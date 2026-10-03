# Scaling host layout to many projects — design and migration plan

Written when the host ran 5 projects and the question was "I'll add more; how do
I keep this efficient?" The short version:

> **Consolidate shared infrastructure. Never consolidate the application
> services.** Efficiency at scale comes from a shared platform layer plus
> run-on-demand apps — not from merging code.

All numbers are measured on this machine (2026-10-03).

---

## 1. Why the naive setup does not scale

Per-project duplication is what breaks, not the number of projects:

| Per project, today | Cost | ×10 projects |
|---|---|---|
| Its own Postgres container | ~35 MB | ~350 MB |
| Its own Keycloak (if it needs auth) | 700–1,400 MB | **7–14 GB** |
| Its own Kafka (if it needs events) | ~370 MB | ~3.7 GB |
| Its own nginx edge | ~7.5 MB | ~75 MB |
| Its own cloudflared tunnel | ~40 MB | ~400 MB |

Measured reality: **5 projects = 13 GB used**. Ten projects built the same way
would exceed the 31 GB in the machine. The growth curve is the problem, and
Keycloak is the steepest part of it.

## 2. Target architecture

```
ALWAYS ON — shared, ~1.2 GB total regardless of project count
┌────────────────────────────────────────────────────────────────┐
│ postgres-unified   one server, ONE DATABASE PER PROJECT/SERVICE │
│ keycloak-unified   ONE REALM PER PROJECT                        │
│ kafka              shared broker, topic namespacing             │
│ zipkin             tracing (optional, can be off)               │
│ nginx-edge         ONE container, one server block per project  │
│ cloudflared        ONE named tunnel, ingress rule per project   │
└────────────────────────────────────────────────────────────────┘

ON DEMAND — started only while a project is being shown
┌────────────────────────────────────────────────────────────────┐
│ the project's own services + its frontend bundle                │
│ banking: 8 JVMs ~2.9 GB   claims: ~0.4 GB   workflow: ~0.1 GB   │
└────────────────────────────────────────────────────────────────┘
```

Result: **~4 GB with one project live**, and adding project #6 costs
near-zero infrastructure — no new database server, identity provider, tunnel,
or port negotiation.

## 3. What to consolidate, and what to leave alone

| Consolidate ✅ | Leave separate ❌ |
|---|---|
| Postgres: one server, N **databases** | The services inside a project |
| Keycloak: one instance, N **realms** | A project's own frontend bundle |
| nginx: one edge, N server blocks | Anything a reviewer will inspect |
| cloudflared: one named tunnel | |
| Kafka: shared, namespaced topics | |

### Databases, not schemas

Within one Postgres server, prefer **separate databases** over separate schemas:

- The database *name* is what every app already specifies, so connection
  strings change only in host:port — no `currentSchema`/`search_path` wiring.
- Isolation is enforced by Postgres (separate catalogs, separate roles), not by
  convention. Banking's README claims "database per service, no shared tables" —
  that stays literally true.
- It avoids the schema-based footguns: shared `public` schema, extension
  collisions, and migration tools that assume they own the database.
- Keycloak specifically expects to own its database; giving it a schema inside a
  shared one is unsupported territory.

Memory is identical either way — the *container count* is what costs, not the
number of databases.

### Why NOT one JVM for all the services

Superficially attractive: a JVM is just a runtime, and several Spring Boot apps
can share one (separate `ApplicationContext`s, or webapps in one servlet
container), each with its own port and datasource. The module structure survives
— so "it's still microservices, architecturally" is a fair instinct.

What does not survive is the property the style is actually defined by:
**independent deployability**. One process means:

- no independent deploy or restart (bounce one → bounce all)
- no fault isolation (one OOM or a runaway GC pause takes everything down)
- no independent scaling (one heap for all five services)
- no independent dependency versions (one classpath = one Spring version)
- process-global state fights you: system properties, static initialisers, JMX,
  shutdown hooks, a single GC

That yields a **modular monolith** — respectable, but a different architecture,
and the repo would be mislabelled. Estimated saving: ~2.1 GB, permanently
trading the demo's headline feature. **Rejected.** The same ~2.9 GB is
reclaimable for free by stopping the stack when it is not being demoed (§6).

## 4. Port registry

Single source of truth for "which ports are taken" — the thing that breaks first
as projects accumulate.

| Range | Purpose | In use |
|---|---|---|
| 4200–4299 | frontend dev servers | 4200 |
| 5432–5459 | Postgres | 5432,5433,5434,5435,5436,5453,5454 |
| **5460** | **shared postgres-unified** | reserved |
| 8000–8099 | app backends + shared Keycloak | 8000, 8025, 8080(tomcat), 8081, 8082, 8083, 8084, 8085, 8086, 8090 (shared Keycloak), 8091 (retired), 8092, 8098, 8099 |
| 8761, 8888 | banking discovery/config | both |
| 9092, 9411, 2181 | Kafka, Zipkin, ZooKeeper | all |
| 8801–8899 | **nginx edges (one per project)** | 8801, 8802, 8803, 8804 |
| 3389 | GNOME RDP | yes |

Convention for a new project: take the next free edge port from 8805 upward, give
its backend the next free port from 8100, and create its database on 5460 — no
host-level changes needed.

## 5. The per-project manifest

The piece that turns "add a project" from an afternoon into a checklist. One
file describing everything about a project; scripts derive from it.

```yaml
# ~/hosting/apps.yaml
projects:
  banking:
    edge_port: 8804
    edge_conf: nginx/banking.conf
    bundle: artifacts/banking-browser
    database: banking_auth, banking_account, banking_payment,
              banking_transaction, banking_notification   # on postgres-unified
    db_user: bank
    auth: own-jwt                 # not keycloak
    units: [banking-config-server, banking-eureka-server, banking-api-gateway,
            banking-auth-service, banking-account-service, banking-payment-service,
            banking-transaction-service, banking-notification-service]
    tunnel: banking
  claims:
    edge_port: 8801
    database: claims
    db_user: claims
    auth: keycloak
    realm: claims
    units: [claims-backend, cloudflared-claims]
    tunnel: claims
```

Derived tooling (small scripts, each reading the manifest):

- `bin/solo.sh <project>` — start that project, stop the others
- `bin/status.sh` — health of every project, one screen
- `bin/backup.sh` — `pg_dump` every database from the one server
- `bin/newproject.sh <name>` — scaffolds edge block, DB, realm, unit files

## 6. Migration plan

Incremental, verified at each step, with rollback always available.

### Phase 0 — prep (no live impact, do first)

1. `pg_dump` all 7 databases into `~/hosting/backups/`.
2. Start `postgres-unified` on **5460** (idle; old containers keep running).
3. Create the same roles and one database per project/service inside it.
4. Restore the dumps and **verify row/table counts match** — before any
   application is repointed.

Old containers stay running throughout, so behaviour is unchanged and rollback
is "change nothing back".

### Phase 1 — cut applications over, one project at a time

Repoint connection strings to `localhost:5460`, in hosting-level config only:

- **banking**: systemd units (`--spring.datasource.url=...`) — no repo edits,
  same mechanism already used for account/payment
- **claims**: its `claims-backend.env`
- **workflow**: `workflow_platform/.env`
- **keycloak (workflow)**: compose override `KC_DB_URL`

Verify each project end-to-end (login, read data, one write) before moving to the
next. Rollback per project = point the config back.

### Phase 2 — shared Keycloak

Biggest single win (~700 MB), fiddliest step. One instance, two realms.

The genuine work is **per-realm hostname/origin advertising** — the reason two
instances exist today (`bin/set-origin.sh` exists because each app must
advertise the browser's hostname). Keycloak 25 supports per-realm hostname
config. Claims' realm currently lives in `start-dev`'s ephemeral file database
and is re-imported per container creation; moving it to Postgres makes it
persistent (an upgrade, but it changes the documented realm-editing workflow).

### Phase 3 — edge and tunnel

- Five nginx edges → one container, five `server {}` blocks (~30 MB, and one
  place for snippets/headers/rate limits).
- Five quick tunnels → **one named tunnel** with an ingress rule per project.
  Bonus beyond memory: **stable hostnames**, which is what you actually want on a
  CV — quick-tunnel URLs change on every restart.

### Phase 4 — run-on-demand

`bin/solo.sh` plus the manifest. Stopping the demos you are not showing frees
more than every consolidation above combined (~2.9 GB for banking alone) and is
instant and reversible.

## 7. Risks and rollback

| Risk | Mitigation |
|---|---|
| Data loss during migration | `pg_dump` first; old containers untouched until verified |
| One Postgres = single point of failure for all projects | Accepted knowingly; it is the trade for maintainability. Backups become *easier* (one target) |
| Keycloak origin regression breaks logins | Do Phase 2 last, keep the old instance running until both logins verify |
| A project's config leaks between environments | All changes in hosting config/env, never in project repos |
| Losing the microservices story | Phases 0–4 never merge services |

## 8. Checklist for a new project

1. Pick the next free edge port (8805+) and backend port (8100+).
2. Create its database(s) on 5460 with its own role.
3. If it needs auth: add a realm to the shared Keycloak.
4. Add an `nginx/<name>.conf` server block; serve its bundle.
5. Add a systemd unit (tuned JVM flags — see `docs/jvm-tuning.md`).
6. Add an ingress rule on the shared tunnel.
7. Add it to `apps.yaml`.
8. Verify: `bin/solo.sh <name>` → local health → public URL → login.

---

## Phase 2 — status: COMPLETE

One shared Keycloak (`hosting-keycloak`, `compose/shared.yml`, port 8090) serves
`claims` and `workflow-realm`; realm data is in a `keycloak` database on
`postgres-unified`. Each realm carries its own `frontendUrl`, which outranks the
global hostname, so one instance correctly advertises two different public origins.

- Retired: both per-project Keycloak containers (stopped, `legacy` profile).
- Retired at the same time, for the same resurrection reason: the two per-project
  Postgres services (Phase 1 leftovers) and workflow's Angular dev-server container,
  all now behind `profiles: ["legacy"]`.
- Rotation is handled by `bin/set-origin.sh` via the admin API: per-realm
  `frontendUrl` plus the client's redirect URIs. No container restart.
- Measured saving: **838 MB** (631 MB vs 784 + 685 MB).

Full write-up and the reasoning: `keycloak-consolidation.md`. Operational summary:
`../README.md`.
