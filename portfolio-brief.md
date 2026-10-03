# Portfolio build brief — Shreyash Sharma

**What this document is:** the source of truth for building a personal portfolio
site around five working projects. Every fact here is verifiable — see §10 for the
commands. If something here disagrees with a repo README, the repo wins; if it
disagrees with the *live* demo, the live demo is the newer of the two (§8 has the
one place where they genuinely diverge).

**Instructions to the agent reading this:** do not invent features, metrics, or
screenshots. If a number is not in this document, do not put it on the page. Every
capability shown must be traceable to code, a repo README, or a live demo. Prefer
omitting a claim over embellishing one.

---

## 1. The person

| | |
|---|---|
| Name | Shreyash Sharma |
| Positioning | Full-Stack Developer — Java, Spring Boot, Angular, Python, React |
| Experience | ~4 years |
| Location | Pune, India |
| GitHub | https://github.com/shreyash-sharma-byte |
| LinkedIn | https://www.linkedin.com/in/shreyash-sharma-908b741a9 |
| Email | shreyashms2501@gmail.com |

**Tone for all copy:** senior and capability-first. Describe what was built and how
it works; never pad with enthusiasm, never use marketing intensifiers ("cutting
edge", "revolutionary", "passionate about"). The work is the argument.

---

## 2. Design rules (non-negotiable)

These are the owner's standing preferences, applied to every page:

- **No AI-slop.** Specifically forbidden: gradients, emoji in the UI, a hero
  section, a 3-card feature grid, glassmorphism, drop-shadow decoration.
- **Information-console style.** Hierarchy comes from type scale, weight and
  spacing. Colour is reserved for meaning — links, primary action, success/failure.
  At most a 1px shadow.
- **Architecture first.** A project page leads with how the thing is built — the
  topology, the real request flow, and the decisions behind it — not a feature list.
  Features come after, as evidence.
- **Mobile responsive**, checked at 390px and 1280px. No horizontal scrolling at
  either width; tap targets ≥ 44px.
- **Label status honestly**: "Implemented" vs "Planned". Never present planned work
  as shipped. If a repo README documents phases, reproduce that labelling.
- **Footer credit on every page**, exact text:
  `Made by Shreyash Sharma` → https://github.com/shreyash-sharma-byte
  plus LinkedIn → https://www.linkedin.com/in/shreyash-sharma-908b741a9
  and email → mailto:shreyashms2501@gmail.com
- **Plain CSS**, self-hosted, no CSS framework, no icon library. No secrets or API
  keys in the browser. Keyboard and screen-reader support is required, not optional.
- Prefer showing **real systems** over screenshots of code.

---

## 3. Suggested site structure

1. **Home** — name, one-line positioning, contact links, then the five projects.
   Each project gets an architecture-first summary (what it is, the topology in one
   line, the stack, one standout decision), a status label, and links to its page +
   live demo + repo.
2. **One page per project** — the meat. Suggested section order:
   the problem it solves → architecture diagram → real request flow → key decisions
   → stack table → verified metrics → screenshots → live demo + credentials → repo.
3. **Explorer** — the Cartographer is a real tool that analysed the other four
   projects. Present it as such (§4.4), with its own map numbers as the evidence.
4. **Engineering notes** — the write-ups in §7. This is the section that
   distinguishes a portfolio from a project list; it shows judgement, measured
   results, and honesty about what went wrong.
5. **Footer** — the credit block from §2, on every page.

---

## 4. The five projects

### 4.1 OpenClaimFlow — AI-assisted insurance claim processing

- **Repo:** https://github.com/shreyash-sharma-byte/ai-assisted-claim-processing-system
- **One-liner:** an end-to-end insurance claim system — claimants file losses
  online, claims auto-route to the least-loaded qualified adjuster, adjusters assess
  through a staged workflow, and supervisors oversee the whole book with authority
  limits, audit and privacy controls.
- **Problem it solves:** claim handling is a workflow with money attached. The hard
  parts are authority (who may approve what), traceability (why was this paid) and
  privacy (what must a claimant never see) — not the forms.

**Stack (verified from the repo README)**

| Layer | Technology |
|---|---|
| Frontend | Angular 22 SPA, `keycloak-js`, Intl formatters |
| Backend | Spring Boot 3, Java 21, Maven, Spring Data JPA + Flyway (V1–V30) |
| Database | PostgreSQL 16 (`claims` dev, `claims_e2e` hermetic E2E) |
| Auth | Keycloak 26, OIDC/PKCE, realm `claims` |
| Email | Mailpit + transactional outbox pattern |
| Tests | Backend 299/299; Playwright E2E, 18 spec files, per-run unique data |
| CI | GitHub Actions — backend tests + frontend build + full E2E stack |

**Architecture**

```
Angular SPA  --OIDC/PKCE-->  Keycloak (:8090)
     |
     +-- /api (Bearer JWT) -->  Spring Boot (Java 21)  --JDBC-->  PostgreSQL 16
     |                                                          (claims, claims_e2e)
     +-- Playwright E2E  ---->  same stack + hermetic claims_e2e DB
                                        email --> Mailpit
```

**Decisions worth showing on the page**

- **Authority gate** — a decision inside the adjuster's limit closes and pays;
  above it, the system saves a proposal and refers upward. Authority is a per-product
  ladder (L1/L2/L3/supervisor), editable by a supervisor.
- **Optimistic locking** — concurrent edits raise a conflict banner (HTTP 409)
  instead of silently overwriting. No lost updates.
- **404, not 403, on cross-owner reads** — refusing to confirm that a record exists
  is the privacy-correct answer.
- **Claimant visibility wall** — the claimant tracker shows workflow steps only;
  reserves, internal notes and assignees never leak. Asserted in tests.
- **Append-only audit** — there is no edit or delete endpoint for the audit log.
- **AI assistant with a fallback** — chat and per-cover advisory via the OpenAI wire
  format to DeepSeek (no SDK). With no API key it degrades to a rules-only path and
  never fails the request.
- **Evidence integrity** — PDF/photo upload with magic-byte validation plus SHA-256
  and size recorded per attachment.
- **Storage seam** — filesystem by default, S3-compatible behind the same interface,
  zero code change to switch.

**Verified metrics:** 71 API endpoints mapped · 373 files · 2,710 symbols ·
9,008 call edges · 87 detected flows · 299/299 backend tests · 18 Playwright specs ·
30 Flyway migrations · 7 denial codes · 3 role classes (claimant, adjuster L1–L3,
supervisor).

**Screenshots available in the repo** (better than anything captured here):
`demo/OpenClaimFlow-Complete-Demo.pdf` — a **59-page** visual demo, 45 live
screenshots + 11 capability deep-dives + a system map. Also `demo/OpenClaimFlow-Demo.pdf`
(46 pages) and `e2e/shots/`.

**Status caution:** the GitHub repo *description* still reads "slices 0-1: walking
skeleton + FNOL with Keycloak auth (AI features planned)" — that description is
**stale**. The README and code document the full system. Read `docs/progress.md`
(status source of truth) before making any status claim.

---

### 4.2 Enterprise Workflow Management System

- **Repo:** https://github.com/shreyash-sharma-byte/workflow-management-system
- **One-liner:** a workflow platform where organisations define reusable templates,
  configure stations with role-based permissions, execute instances across those
  stations, and keep a complete immutable audit trail.
- **Problem it solves:** most "workflow" code is a status column. This is the real
  shape — versioned templates, per-station authority, and an audit trail that
  cannot be edited.

**Stack**

| Layer | Technology |
|---|---|
| Frontend | Angular 17, TypeScript, Keycloak JS adapter |
| Backend | Django 4.2 + Django REST Framework, 40+ REST APIs |
| Auth | Keycloak 25, JWT (RS256), automatic user provisioning |
| Database | PostgreSQL 16, 11 models, append-only audit trail |
| DevOps | Docker + Compose, one-command launch |

**Architecture**

```
Angular  ->  Django  ->  PostgreSQL
    \          |
     \         +--> Keycloak (JWT RS256)
```

**Decisions worth showing**

- **Five-check workflow engine** — every move validates: instance is ACTIVE; the
  user holds the role required at the current station; the transition exists;
  all required tasks are complete; and the optimistic lock still holds. All five
  must pass before a station change is committed.
- **Nine realm roles** with admin/initiator/operator/auditor separation, enforced
  per station rather than globally.
- **Four task types** — APPROVAL, FORM (JSON-schema-driven visual field builder),
  DOCUMENT, CONFIRMATION checklist.
- **Immutable audit** — append-only history with full attribution, exportable.
- **Public instance sharing** — UUID-v4 token URLs let an external stakeholder view
  one instance without an account.
- **Hardening, stated plainly** — whitelist-only CORS, scoped throttling on auth
  endpoints, security headers, input sanitisation middleware, MIME whitelist + 1 MB
  upload cap, Django admin moved off `/admin/`.

**Verified metrics:** 650 symbols · 1,327 call edges · 104 files mapped · 17 detected
flows · 9 realm roles · 11 data models · 40+ REST APIs · 5 validation gates per move.

**Status:** Phase 1 **implemented**, Phase 2 **implemented**, Phase 3 **planned** —
reproduce this labelling exactly; the README lists what belongs to each.

---

### 4.3 Banking Microservices Platform (fronted by "Ledger")

- **Repo:** https://github.com/shreyash-sharma-byte/banking-microservices
- **One-liner:** a retail + business banking platform — accounts, atomic money
  transfers, an event-driven payment pipeline, an immutable unified ledger, and
  role-based access across services behind an API gateway.
- **Problem it solves:** real banks do not move money with one `UPDATE` in one
  database. This is the architecture they actually use: small services, each owning
  its own data, coordinated through an event bus.

**Stack & topology**

| Service | Port | Role |
|---|---|---|
| config-server | 8888 | centralised configuration |
| eureka-server | 8761 | service discovery |
| api-gateway | 8086 | single entry, RBAC + routing |
| auth-service | 8092 | JWT issuance, refresh rotation |
| account-service | 8082 | accounts, ownership |
| payment-service | 8083 | transfers, idempotency, outbox |
| transaction-service | 8084 | immutable unified ledger (append-only) |
| notification-service | 8085 | notifications |

Frontend: **Angular 22** (`banking-ui`), talking to the gateway. Also Kafka for the
event pipeline, PostgreSQL (database-per-service), Zipkin for tracing.

**Decisions worth showing — this is the strongest "real engineering" content here**

- **Database per service** — five databases, no shared tables, ownership enforced at
  the application layer with logical foreign keys.
- **Race-free overdraft protection** — one ACID transaction per transfer using
  `UPDATE ... WHERE balance >= ?`, so two concurrent transfers can never overdraw an
  account.
- **Transactional outbox, 3-state machine** — ledger entries move
  `PENDING → SENDING → PUBLISHED`, batch-synced to the Transaction Service over
  Kafka with confirmation callbacks and ERROR retry. No lost entries, no duplicates.
- **Idempotency at every level** — duplicate payment requests rejected, `batch_id`
  blocks double ledger inserts, `ON CONFLICT DO NOTHING` makes retries safe.
- **Immutable ledger** — append-only, the single source of truth for history and
  reporting, fed by every service that moves money.
- **Auth** — access tokens (1h), rotated refresh tokens (7d, SHA-256 hashed in the
  database), blacklist-based logout, bcrypt password hashing.
- **Roles** — RETAIL / BUSINESS / EMPLOYEE / ADMIN / AUDITOR, enforced at the gateway
  and re-checked per service.
- **Salary → savings lifecycle** — removing an employee from a business converts
  their SALARY accounts to SAVINGS automatically.
- **Correlation IDs** propagated on every request, structured logs, Zipkin tracing.

**Verified metrics:** 492 symbols · 1,568 call edges · 89 files mapped ·
39 endpoints · 17 tables · 39 detected flows · 18 ledger partitions.

**Screenshots in the repo:** `docs/dashboard.png`, `docs/transfer.png`,
`docs/history.png` — the transfer shown was executed end-to-end through
gateway → payment-service → Kafka → ledger.

**Published:** the frontend now has its **own public repository** —
https://github.com/shreyash-sharma-byte/banking-ui — so the client can be
linked and reviewed on its own. Its README documents the architecture, the
screens and the client's decisions, with screenshots of the current UI.

---

### 4.4 Living Codebase Cartographer

- **Repo:** https://github.com/shreyash-sharma-byte/living-codebase-cartographer
- **One-liner:** an offline codebase cartographer — it maps any repository into
  endpoints, call graphs, data lineage, blast-radius impact analysis and request-flow
  traces, with evidence and a confidence level on every fact, and ships a portable
  HTML architecture explorer that opens over `file://`.
- **Problem it solves:** understanding an unfamiliar codebase usually means either a
  cloud service or an LSP. This does it offline, with no dependencies and no
  telemetry.

**Stack:** Python 3.8+, **standard library only** — no third-party packages, no LSP,
no network calls. Language-agnostic by design: Java, TypeScript/JavaScript, Python,
Go, C#, Rust and SQL out of the box, plus a low-confidence fallback pass for
anything else.

**Why it belongs on the portfolio, framed correctly:** it is not a toy — it is the
tool that produced the maps for the other four projects. Use its own output as the
evidence:

| Project it mapped | Files | Symbols | Call edges | Flows traced |
|---|---|---|---|---|
| OpenClaimFlow (claims) | 373 | 2,710 | 9,008 | 87 |
| Workflow Management System | 104 | 650 | 1,327 | 17 |
| Banking Microservices | 89 | 492 | 1,568 | 39 |
| ClaimShield AI | 40 | 184 | 430 | 5 |

Each map also emits human-readable artifacts: `architecture.md`, `api-map.md`,
`call-graph.md`, `data-flow.md`, `database.md`, `dependencies.md`,
`authentication.md`, `configuration.md`, `decisions/`, `business-flows/` and a
`changes/` history.

---

### 4.5 ClaimShield AI

- **Repo:** https://github.com/shreyash-sharma-byte/claimshield-ai
- **One-liner:** a RAG + multi-agent insurance intelligence platform — it reads
  policy documents, extracts structured knowledge, evaluates claim eligibility,
  detects fraud signals, and produces explainable coverage decisions with citations
  and a confidence score.
- **Problem it solves:** "can I trust this model's coverage answer" is the only
  question that matters in insurance. Hence citations, confidence, and an evaluation
  pipeline for hallucination detection.

**Stack:** Python, FastAPI, vector retrieval (FAISS), LLM inference (Groq, OpenAI
wire), streaming responses, Redis cache layer, evaluation pipeline, async
infrastructure.

**Architecture (from the repo README)**

```
request -> API gateway -> cache -> retriever (vector store)
        -> agent orchestrator
             intake | policy validation | fraud detection
             | coverage reasoning | decision
        -> fine-tuned insurance LLM -> evaluation pipeline
        -> explainable response + confidence score
```

**Verified metrics:** 184 symbols · 430 call edges · 40 files mapped · 5 endpoints.

**Live demo — the one that needs explaining.** The public console is free to use
with a deliberately soft quota: **10 model calls per IP**, then a founder-secret
unlock grants another allowance. That is a design choice worth writing up, because
the implementation detail is the interesting part:

- The counter is charged at the **single choke point** every model call passes
  through, so it counts **model calls, not HTTP requests**: one policy search costs
  1, a policy comparison costs 3 (two extractions + a verdict), and the retrieval
  evaluation harness costs **0** — it is local embeddings and classifiers and never
  calls a model.
- The unlock secret is compared **server-side only** and is never sent to the
  browser, so it cannot be read out of the page source. Failed attempts are
  throttled (5 per IP, then a 5-minute cool-off).

---

## 5. Live demos and credentials

> These are **Cloudflare quick tunnels**: free, no account, and the hostname
> **changes on every restart**. Always read the current URL with
> `bin/tunnel-url.sh <label>` — never hardcode the ones below into the site. For a
> portfolio you will want a stable URL; see §5.2.

### 5.1 Current URLs and logins

| App | URL label | Login |
|---|---|---|
| OpenClaimFlow | `bin/tunnel-url.sh claims` | Keycloak — see below |
| Workflow Management System | `bin/tunnel-url.sh workflow` | Keycloak — see below |
| Living Codebase Cartographer | `bin/tunnel-url.sh cartographer` | none (static) |
| Banking (Ledger) | `bin/tunnel-url.sh banking` | own JWT service |
| ClaimShield AI | `bin/tunnel-url.sh claimshield` | none (soft quota, §4.5) |

**Every one of the three login pages now displays its own demo accounts on the page
itself** — a visitor needs no briefing. The values below are already public on those
pages, which is why they can be listed here.

| App | Account | Password | Role |
|---|---|---|---|
| Claims | `ada.lovelace` | `claims-Pass-123` | claimant |
| Claims | `adjuster.one` | `adjuster-Pass-123` | adjuster, authority L1 |
| Claims | `supervisor` | `supervisor-Pass-123` | supervisor |
| Workflow | `priya` | `Workflow@123` | administrator |
| Workflow | `vikram` | `Workflow@123` | developer |
| Workflow | `amit.manager` | `Workflow@123` | QA manager |
| Banking | `yash@bank.test` | `Bank@1234` | retail customer |
| Banking | `staff@bank.test` | `Admin@1234` | staff / admin |

Notes for taking screenshots: logins only work through the **public URL**, never
`localhost` — the identity provider advertises the tunnel origin and rejects a
localhost-started login as cross-origin. The keycloak realms also hold more accounts
than listed (claims has 16 users; workflow has 8) if you want to illustrate a role
matrix.

### 5.2 Getting a stable URL before publishing

Quick tunnels are wrong for a CV link. In order of effort:

1. **Cloudflare named tunnel** — needs a Cloudflare account and a domain:
   `cloudflared tunnel login`, `create`, `route dns`. One stable hostname; the same
   origin-repointing script applies.
2. **Tailscale Funnel** — free and stable, but requires enabling Serve/Funnel and
   TLS certs in the Tailscale admin console.

Either way the app configuration is re-pointed by `bin/set-origin.sh`, not by
editing any project.

---

## 6. Verified metrics at a glance

| | Claims | Workflow | Banking | Cartographer | ClaimShield |
|---|---|---|---|---|---|
| Files mapped | 373 | 104 | 89 | — | 40 |
| Symbols | 2,710 | 650 | 492 | — | 184 |
| Call edges | 9,008 | 1,327 | 1,568 | — | 430 |
| Flows traced | 87 | 17 | 39 | — | 5 |
| Endpoints | 71 | 40+ † | 39 | — | 5 |
| Tests | 299/299 + 18 E2E specs | — | — | — | — |
| Auth | Keycloak OIDC/PKCE | Keycloak JWT RS256 | own JWT | none | none |

Do not present "—" as zero. It means not measured yet, which is a different claim.

† Workflow's "40+" is its own README's figure. Every other endpoint count here is
detected by the mapper; for the Django service it resolves 17 route/endpoint nodes,
because DRF router registrations are not statically resolvable. That is a limit of
static analysis, not evidence of a missing API — which is exactly why the README
figure is quoted instead.

---

## 7. Engineering write-ups worth publishing

This is the section that makes the portfolio credible. Each of these was measured,
and in two cases the honest result contradicted the original expectation — which is
the story.

1. **Why a signed-in app scrolled sideways on a phone.** A shell laid out as
   `sidebar + main` in a flex row broke on mobile because the main column was
   `flex: 1` **without `min-width: 0`**: a flex item cannot shrink below its
   content's intrinsic width, so wide children (nowrap tables, filter bars) sized
   the column itself. Measured: `app-main` computed **784px wide inside a 390px
   viewport**, and every descendant inherited it. Per-component media queries cannot
   fix a column sized by its content — which is why the first attempt at a fix
   compiled cleanly and changed nothing. Fixed structurally, then verified
   numerically: `scrollWidth` 784 → **390** on four routes, with zero elements
   beyond the viewport.
2. **JVM tuning that was measured, not guessed.** Heap committed per Java service
   fell from 256 MB to ~123 MB and RSS dropped ~1.4 GB across the set; Kafka's
   committed heap went from 1 GB to 512 MB. The flags and the reasoning are written
   down, including the flags deliberately *not* set and the traps in reading the
   numbers (`bin/jvm-report.py` reports RSS, heap, metaspace and the unexplained
   residual separately).
3. **The consolidation that did not pay off the way it was expected to.** Merging
   seven per-project Postgres containers into one shared instance saved **~38 MB**,
   not the 100–150 MB originally estimated — because Postgres's per-instance
   overhead is small and connection backends dominate. The reason to keep it is
   operational, not memory: one backup target, one connection point, and the next
   project needs no new database server. Publishing the honest number alongside the
   decision is a better signal than a fabricated win.
4. **One identity provider serving two realms.** Two Keycloak instances looked
   necessary because each realm's issuer must equal the origin the browser used, and
   the apps are reached on different hostnames. A realm carries its own `frontendUrl`
   which outranks the global hostname, so a single instance legitimately advertises
   two origins. Verified with real logins, not just discovery documents. Saved
   **838 MB** — the largest single memory win after the JVM retune.
5. **A dated database partition, and a time bomb that fires on the first of the
   month.** Two tables were range-partitioned by timestamp with exactly one
   hardcoded partition — the month the project was written. Once the calendar moved
   past it, every insert failed and surfaced as a 500 on account creation and on
   *every transfer* (the audit row is written in the same transaction). Fixed with a
   rolling window of monthly partitions plus a `DEFAULT` catch-all per table.
6. **A CORS rule that could never work.** The gateway's allow-list named only
   `localhost:4200/4201`, and a rotating tunnel hostname can never match a fixed
   list. Browsers send `Origin` even on same-origin POSTs, so logins failed with 403
   while `curl` (no `Origin`) succeeded — a genuinely confusing asymmetry. Resolved
   by clearing `Origin` at the edge, correct for a single-origin deployment.
7. **Keeping the source repos pristine while deploying them.** The deployment
   wiring lives in separate clones, as re-appliable patches, with the original repos
   byte-identical to their last commit — so nothing about the hosting can leak into
   the public repos by accident, and a rebuild cannot silently change what is served.

---

## 8. Do NOT claim (accuracy guardrails)

1. **Ledger reads are not ownership-checked.** In the banking platform,
   `GET /api/transactions` and `POST /api/transactions/search` filter the ledger by
   `accountId` without verifying the caller owns that account — any authenticated
   user can read any account's ledger by passing its id. This is **open and
   unfixed**. Do not imply the platform's authorization is complete.
2. **GitHub now matches the live demo** for claims and workflow — this is done, not
   pending. The landing screens, the workflow mobile-layout fix and the emoji
   removals were pushed to the public repos on 2026-10-03 as four grouped commits
   each (`main` for claims, `master` for workflow). Banking is the exception: its
   Angular frontend (`banking-ui`) has **no git repository at all**, so the banking
   redesign, welcome page and login credentials panel are still unpublished.
3. **The claims repo description is stale** — it says "slices 0-1 … AI features
   planned" while the README and code document the whole system. Don't copy the repo
   description; read `docs/progress.md`.
4. **`banking-ui` is published** —
   https://github.com/shreyash-sharma-byte/banking-ui — so the banking
   frontend can be linked. The platform itself remains `banking-microservices`.
5. **The demo credentials are demo data.** Present them as sample logins, never as a
   security feature.
6. **Tunnel URLs are not permanent.** Don't put a raw trycloudflare hostname on a CV
   or a "visit the live site" button without moving to a named tunnel (§5.2).
7. **Don't call ClaimShield's quota a "free tier" or "rate limit"** without the
   nuance in §4.5 — it counts model calls at a single choke point, and the unlock
   secret is server-side only.
8. Two of the READMEs use emoji and marketing language internally. Do not inherit
   them — §2 governs the site's own copy.

---

## 9. Assets

### 9.1 Screenshots captured from the live deployments

In `/home/yash/hosting/docs/portfolio-shots/` (24 files). These show the **deployed**
state, including the demo-credentials panels:

- `landing-<app>-1280.png` / `landing-<app>-390.png` for all five apps —
  the pre-login front doors at desktop and phone width. No overflow at either.
- `demo-claims-1280.png`, `demo-claims-390.png` — the claims Keycloak sign-in page
  with its demo-accounts panel (desktop shows the table; phone stacks it).
- `demo-workflow-1280.png`, `demo-workflow-390.png` — same, workflow realm.
- `demo-banking-1280.png`, `demo-banking-390.png` — banking's own Angular login page.
- `wfacc-1280_dashboard.png`, `wfacc-390_dashboard.png`,
  `wfacc-1280_instances.png`, `wfacc-390_instances.png` — workflow signed-in views.
- `bk-final-390_dashboard.png`, `bk-final-390_transfer.png`,
  `bk-final-390_history.png` — banking signed-in views (phone width).
- `banking-welcome-1280.png`, `banking-login-1280.png`,
  `banking-dashboard-1280.png`, `banking-transfer-1280.png`,
  `banking-history-1280.png` — the banking client at desktop width, captured from
  the live deployment. The welcome and sign-in captures are the true pre-login
  state, with the demo-accounts panel visible on the sign-in screen.
- `wf_landing_390.png` — workflow landing, phone width.

### 9.2 Better sources inside the repos

The repos hold purpose-built demo media — prefer these over anything captured ad hoc:

- **Claims:** `demo/OpenClaimFlow-Complete-Demo.pdf` — 59 pages, 45 screenshots,
  11 capability deep-dives, a system map. Also a 46-page journey PDF and
  `e2e/shots/`.
- **Workflow:** `docs/screenshots/` (10 screenshots) and `DEMO.md`, a demo SOP.
- **Banking:** `docs/dashboard.png`, `docs/transfer.png`, `docs/history.png`.
- **Cartographer:** generates its own HTML explorer — screenshot that, don't
  illustrate it.
- **ClaimShield:** capture the console live; it is the interaction that matters
  (ask a question, see citations, watch the quota counter).

---

## 10. How to verify every claim in this document

```bash
# the current public URL for any app (never trust a hardcoded hostname)
cd /home/yash/hosting && bin/tunnel-url.sh claims

# the project list and their public descriptions
gh repo list shreyash-sharma-byte --limit 30

# the codebase metrics quoted in §4 and §6 (files / symbols / edges / flows)
python3 - <<'PY'
import json
for p in ("claims","workflow","banking","claimshield"):
    d=json.load(open(f"/home/yash/hosting/maps/{p}/graph.json"))
    files=sum(1 for n in d["nodes"] if n.get("kind")=="file")
    print(f"{p:12} files={files:4} symbols={len(d['nodes']):5} "
          f"edges={len(d['edges']):5} flows={len(d['flow_candidates'])}")
PY

# claims test count and feature list
grep -n "backend-299\|299/299" /home/yash/hosting/src/claim-processing-system/README.md

# workflow implemented-vs-planned labelling
grep -nE "^### Phase" /home/yash/hosting/src/workflow-management-system/README.md

# the hosting design record (topology, decisions, measured results)
sed -n '1,120p' /home/yash/hosting/README.md
ls /home/yash/hosting/docs/
```

---

## 11. Source-of-truth files

| What | Where |
|---|---|
| Hosting topology, ports, layout, decisions, measured results | `/home/yash/hosting/README.md` |
| Front-page design standard (skeleton, prohibitions, per-app tokens) | `/home/yash/hosting/docs/front-page-design-spec.md` |
| Identity provider consolidation + login-page notes | `/home/yash/hosting/docs/keycloak-consolidation.md` |
| JVM tuning, flags and measurement traps | `/home/yash/hosting/docs/jvm-tuning.md` |
| Shared-infrastructure plan and its honest results | `/home/yash/hosting/docs/consolidation-plan.md` |
| Claims project (full README, features, architecture, demo) | `/home/yash/hosting/src/claim-processing-system/README.md` |
| Workflow project (features by phase, security table) | `/home/yash/hosting/src/workflow-management-system/README.md` |
| Banking project (patterns, ADRs, screenshots) | GitHub: `banking-microservices` |
| Cartographer output for all four codebases | `/home/yash/hosting/maps/<project>/` |
| Screenshots (live deployment) | `/home/yash/hosting/docs/portfolio-shots/` |

---

## 12. Open items

**Pushed and done:** the landing screens, the workflow mobile-layout fix and the
emoji removals are on the public repositories — `ai-assisted-claim-processing-system`
`main` (`6e235f8` → `6a846ba7`, four commits) and `workflow-management-system`
`master` (`4e2d98b` → `8697604f`, four commits). The deploy/runtime-config wiring
travels in separate `chore(deploy)` commits, because the workflow landing page
cannot render before login without the check-sso change — the two are coupled.
GitHub and the live demos now agree for both apps.

Still open:

1. **`banking-ui` is published** —
   https://github.com/shreyash-sharma-byte/banking-ui (public, `main`, 40
   files), with a README that documents the architecture and the current UI. The
   platform README's screenshots were refreshed to the redesigned client in the
   same pass.
2. **The claims repository's CI has been failing since 2026-09-11.** Three
   consecutive failed runs predate this push, so the GitHub Actions badge on that
   README is red. This is *not* caused by the frontend work. Worth fixing before the
   portfolio goes live, because a red badge is the first thing a reviewer sees.
3. **The claims repository description is stale** — it still reads "slices 0-1 …
   AI features planned". Either update it or don't surface the description on the
   portfolio page.
