# JVM memory tuning, from scratch

Notes from tuning the Java services hosted on this machine, written to be
readable by someone who has never set a JVM flag on purpose. Every number below
is measured on this box, not illustrative.

Companion tool: `bin/jvm-report.py` — per-JVM RSS + heap + metaspace, and a
`--json` mode for before/after comparison.

---

## 1. Where Java's memory actually goes

A Java process is not "the heap". The heap is usually less than half of what the
OS charges it. This is the single most useful thing to internalise:

```
RSS  (what the OS charges to RAM — the number that matters)
├── Java heap            objects; controlled by -Xms / -Xmx
├── Metaspace            class definitions, method bytecode, constant pools
│                        (unbounded by default; -XX:MaxMetaspaceSize caps it)
├── Code cache           JIT-compiled machine code (-XX:ReservedCodeCacheSize)
├── Thread stacks        ~1 MB reserved per thread (-Xss); RSS only for pages
│                        actually touched, so the real cost is small
├── GC structures        per-collector bookkeeping; grows with max heap (G1
│                        keeps per-region metadata and remembered sets)
├── Direct buffers       NIO/Netty off-heap buffers (-XX:MaxDirectMemorySize)
└── Mapped files         e.g. the executable fat JAR itself
```

A worked example from your own machine, `banking/payment-service` after tuning:

| Component | Size |
|---|---|
| RSS (total charged to RAM) | 456 MB |
| Java heap committed | 123 MB |
| Metaspace committed | 102 MB |
| **Everything else** | **231 MB** |

So ~half the footprint is *not* heap. This is why `-Xmx` alone is a blunt
instrument, and why the flag list below has more than two entries.

## 2. Why the original flags were wasteful

Every service ran with `-Xms256m -Xmx1g`. Those numbers came from a container
template, and they were wrong for this workload in two ways:

- **Heap actually used was 94–170 MB.** The 1 GB cap was never approached, so it
  bought nothing — but it did make the collector lazy (little pressure to
  collect), which is how a Java service's RSS quietly climbs over hours.
- **`-Xms256m` committed 256 MB at startup**, whether or not the app needed it.
  Committed memory is memory the JVM has taken from the OS.

Measured before: RSS 377–609 MB per banking service, for apps holding ~150 MB.

## 3. The flags we set

```ini
-Xms128m -Xmx384m -XX:MaxMetaspaceSize=256m -XX:ReservedCodeCacheSize=96m -XX:+UseSerialGC
```

| Flag | What it does | Why this value | Trade-off |
|---|---|---|---|
| `-Xms128m` | Initial heap, committed at startup | Observed live set is ~100–170 MB; 128 MB starts small and grows into the cap | Slightly more GC in the first minutes while the heap warms |
| `-Xmx384m` | Heap ceiling | ~2x the observed live set — headroom without looseness | A runaway allocation now hits OOM sooner (that's the point) |
| `-XX:MaxMetaspaceSize=256m` | Caps class metadata | These apps settle at 42–102 MB; 256 MB is generous headroom | If exceeded → OOM + restart instead of silently eating native RAM. Does **not** reduce current metaspace |
| `-XX:ReservedCodeCacheSize=96m` | Caps JIT code cache | Default is 240 MB; these apps compile far less | Too small disables further JIT ("CodeCache is full"). 96 MB is ample here |
| `-XX:+UseSerialGC` | Single-threaded stop-the-world GC | Tiny heaps + demo traffic: no parallel GC threads, no per-region metadata = lowest footprint and fewest threads | Pauses scale with heap; a full GC on 384 MB is ~tens of ms. For real throughput, use G1 (the default) |

Kafka got the same treatment through its own environment variable, because the
project's compose sets none and the image default is `-Xms1G -Xmx1G` — 1 GB
committed for a broker holding a handful of demo messages:

```yaml
# compose/banking-override.yml
kafka:
  environment:
    KAFKA_HEAP_OPTS: "-Xms256m -Xmx512m"
```

## 4. Flags we deliberately did NOT set

Knowing what to leave alone matters as much as knowing what to change:

- **`-Xss512k`** (thread stack size). Sounds tempting — Spring Boot runs 50–80
  threads. But stacks are *reserved* per thread and only touched pages become
  resident, so the real RSS saving is a few MB, while a deep JSON or Hibernate
  call stack risks `StackOverflowError`. Not worth it.
- **`-XX:MaxDirectMemorySize=64m`**. The API gateway is Reactor Netty and does
  its I/O through direct buffers. Capping this low produces
  `OutOfMemoryError: Direct buffer memory` under load. Left at its default.
- **`-XX:TieredStopAtLevel=1`** (C1-only JIT). Great for CLI tools and batch
  jobs — much faster startup, smaller code cache — but 2–5x slower peak
  throughput. Wrong for services you demo interactively.
- **`-XX:+UseZGC` / `+UseG1GC`**. Both are excellent and both cost more memory
  than SerialGC at this heap size. Revisit if throughput ever matters.

## 5. How to measure

```bash
# the purpose-built report (RSS + heap + metaspace + unexplained residual)
python3 ~/hosting/bin/jvm-report.py
python3 ~/hosting/bin/jvm-report.py --json > snapshot.json   # for comparisons

# raw equivalents
ps -eo pid,rss,args | grep '[j]ava'        # RSS per process (1024 = MB)
jcmd <pid> GC.heap_info                    # heap regions + metaspace
jcmd <pid> VM.native_memory summary        # needs -XX:NativeMemoryTracking=summary
jstat -gc <pid> 5s                         # live GC behaviour
docker stats --no-stream                   # per-container

# see GC pauses (add to the flags when investigating, remove when done)
-Xlog:gc:file=/home/yash/hosting/logs/gc.log:time,uptime
```

## 6. Three traps when reading the numbers

1. **Committed is not resident.** ZooKeeper runs with a 512 MB committed heap but
   its RSS is ~117 MB — the JVM has *mapped* the heap; untouched pages are not in
   RAM. The reverse also happens: RSS is *larger* than heap + metaspace because
   of code cache, stacks, GC structures and mapped JARs.
2. **Warm is not cold.** Right after a restart the JIT has barely compiled
   anything and the heap is nearly empty, so RSS reads low and then climbs for
   several minutes. Comparing a freshly restarted JVM against one that has been
   up an hour will flatter whichever you restarted. Always compare like for
   like — `bin/jvm-report.py --json` snapshots exist for exactly this.
3. **Snapshot totals move on their own.** A container healthcheck that shells
   out to `kafka-broker-api-versions` starts a *fresh JVM every run*, which shows
   up as an extra short-lived process and periodic CPU/RSS spikes. Don't chase it.

## 7. Verifying a change didn't break anything

Tuning is a change to a live system; prove it with a behaviour test, not a vibe:

```bash
export PATH=/home/yash/hosting/bin:$PATH
systemctl is-active banking-config-server banking-eureka-server banking-api-gateway \
  banking-auth-service banking-account-service banking-payment-service \
  banking-transaction-service banking-notification-service claims-backend
for p in 8888 8761 8086 8092 8082 8083 8084 8085; do
  printf ":%s %s\n" "$p" "$(curl -s localhost:$p/actuator/health)"
done
grep -lE "OutOfMemoryError|StackOverflowError" ~/hosting/logs/banking-*.log
# then the real proof: a transfer must still reach the ledger
python3 ~/hosting/bin/seed-banking-demo.py
```

Note: the claims backend's `/actuator/health` answers **401**, not 200 — it is an
OIDC resource server and the endpoint is secured. A 401 there means healthy; an
empty response means the port is not answering.

## 8. Results

Nine Spring services + Kafka retuned. RSS in MB:

| Service | Before | After (cold) | Change |
|---|---|---|---|
| banking/notification-service | 609 | 407 | −202 |
| banking/payment-service | 587 | 456 | −131 |
| banking/account-service | 577 | 378 | −199 |
| banking/auth-service | 557 | 378 | −179 |
| claims-backend | 556 | 398 | −158 |
| banking/transaction-service | 528 | 386 | −142 |
| banking/api-gateway | 483 | 380 | −103 |
| banking/eureka-server | 474 | 317 | −157 |
| banking/config-server | 377 | 249 | −128 |
| kafka | 433 | 370 | −63 |
| **total (these 10)** | **5181** | **3719** | **≈ −1.4 GB** |

Whole-machine JVM footprint went from **7344 MB → ~5890 MB** across 15–16 JVMs.

**The honest caveat:** the "before" column was measured on services that had been
warmed up for 20–40 minutes; the "after" column was measured ~10 minutes after a
restart. Some of the delta is therefore warm-vs-cold, not flags. The
flag-attributable part is solid and mechanistic: heap committed dropped from
256 MB to ~123 MB per service (that is `-Xms` alone), plus SerialGC's saved GC
threads and structures. Re-run `bin/jvm-report.py --json` against
`docs/jvm-after-cold.json` once the system has been up an hour for a
warm-to-warm number.

Functional verification after the change: all eight services healthy, a live
transfer completed (`200 COMPLETED`), balances moved, and the new entry appeared
in the ledger — so the Kafka pipeline survived its own restart.

## 9. What is still on the table

- **Keycloak ×2 = ~1.47 GB.** The largest remaining target, and the least like
  the services above: it is Quarkus, where much of the memory profile is decided
  at *build* time, so flag tuning gives less than you would expect from a Spring
  app. The bigger win is running **one** instance with two realms (see the
  consolidation discussion) rather than two servers.
- **Zipkin ~285 MB** for tracing that is nice for a screenshot but not needed
  live.
- **CDS / AppCDS.** Nine near-identical Spring apps each commit ~42–102 MB of
  metaspace. A shared class archive lets them map the *same* class metadata from
  one file, so the pages are shared rather than duplicated. This is the next
  genuine multi-JVM win (`-XX:ArchiveClassesAtExit`, then
  `-XX:SharedArchiveFile`) — a build step, not a flag you can bolt on.
- **The Kafka healthcheck JVM churn** noted in §6.3 — switch it to a TCP check.
- **Fewer JVMs.** The blunt truth: the biggest lever is not a flag. Eight banking
  services × ~380 MB is ~3 GB by design, because showing a microservices
  architecture is the point of that project.

## 10. Reverting

The flags live in the unit files, not in any project repository:

```
~/hosting/systemd/banking-*.service      (installed to /etc/systemd/system/)
~/hosting/systemd/claims-backend.service
```

To revert a service, restore its `ExecStart` flags to the originals
(`-Xms256m -Xmx1g`), then:

```bash
export PATH=/home/yash/hosting/bin:$PATH
sdo install -m 644 ~/hosting/systemd/<unit>.service /etc/systemd/system/
sdo systemctl daemon-reload && sdo systemctl restart <unit>
```

Kafka reverts by removing `KAFKA_HEAP_OPTS` from `compose/banking-override.yml`
and re-running the compose `up -d`.

## 11. Going deeper

- `jcmd <pid> help` — the whole diagnostic toolbox; `VM.native_memory summary`
  attributes every byte once you enable NativeMemoryTracking.
- `-XX:+PrintFlagsFinal -version` — print the *effective* value of every flag,
  which is how you confirm a flag actually applied.
- Oracle's "Java HotSpot VM GC Tuning Guide" and Aleksey Shipilëv's JVM Anatomy
  Quirks series — the latter explains *why* things behave as they do.
- For containers: `-XX:MaxRAMPercentage` / `-XX:InitialRAMPercentage` are usually
  better than hard-coded `-Xmx`, because they derive from the cgroup limit. These
  services run as host processes under systemd, so explicit values were clearer —
  if they ever move into containers, switch.
