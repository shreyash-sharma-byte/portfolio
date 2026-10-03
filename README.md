# Portfolio — working folder

This folder is the starting point for building a personal portfolio site around
five working projects. It holds documentation and screenshots only — **no project
source code** (the projects live in their own repositories; see §"The projects").
It sits beside the original project folders and does not modify any of them.

## If you are an agent about to build the portfolio

**Read `portfolio-brief.md` first — it is the brief, and it is self-contained.**
It carries the positioning, the design rules, the five project write-ups with
verified metrics, the live demo credentials, the accuracy guardrails (what must
*not* be claimed), and the commands to verify every number in it.

Two rules from it, repeated here because they matter most:

1. **Do not invent features or metrics.** If a number is not in the brief, it does
   not go on the page.
2. **Architecture first.** Every project page leads with how the system is built —
   topology, real request flow, decisions — before any feature list.

## What is in here

| Path | What it is |
|---|---|
| `portfolio-brief.md` | The build brief. Start here. |
| `docs/front-page-design-spec.md` | The written standard for the pre-login landing screens: page skeleton, prohibitions, per-app design tokens. |
| `docs/keycloak-consolidation.md` | Identity-provider consolidation, per-realm origins, and the login-page work (including why the credentials panels need a template override). |
| `docs/jvm-tuning.md` | JVM memory model, every flag set and why, how to measure, and the traps in reading the numbers. |
| `docs/consolidation-plan.md` | Shared-infrastructure plan, with the honest measured results (including one that contradicted the estimate). |
| `screenshots/` | 24 images captured from the **live deployments**, at desktop (1280px) and phone (390px) width. |

## Screenshots: what the names mean

| Pattern | What it shows |
|---|---|
| `landing-<app>-1280.png` / `-390.png` | The pre-login front door of each of the five apps, desktop and phone. |
| `demo-claims-*.png`, `demo-workflow-*.png` | The Keycloak sign-in pages with their demo-accounts panels. |
| `demo-banking-*.png` | The banking app's own Angular sign-in page. |
| `wfacc-1280_*.png`, `wfacc-390_*.png` | The workflow app signed in (dashboard, instances). |
| `bk-final-390_*.png` | The banking app signed in (dashboard, transfer, history). |
| `wf_landing_390.png` | The workflow landing page, phone width. |

Better demo media exists **inside the project repositories** — most notably the
claims project's 59-page visual demo PDF (45 screenshots) at
`demo/OpenClaimFlow-Complete-Demo.pdf`. Prefer those for anything prominent; the
brief's §9.2 lists what each repo offers.

## The projects

All public repos are under https://github.com/shreyash-sharma-byte

| Project | Repo | Live |
|---|---|---|
| OpenClaimFlow (insurance claims) | `ai-assisted-claim-processing-system` | Keycloak login |
| Enterprise Workflow Management System | `workflow-management-system` | Keycloak login |
| Banking Microservices Platform | `banking-microservices` + [`banking-ui`](https://github.com/shreyash-sharma-byte/banking-ui) (client) | own JWT login |
| Living Codebase Cartographer | `living-codebase-cartographer` | no login (static) |
| ClaimShield AI | `claimshield-ai` | no login (soft quota) |

The banking frontend has its own repository as well:
[`banking-ui`](https://github.com/shreyash-sharma-byte/banking-ui) — link it
for the client, and `banking-microservices` for the platform.

## Two things to settle before publishing

1. **Live URLs are temporary.** The demos are exposed through Cloudflare *quick*
   tunnels, whose hostname changes on every restart. Do not hardcode one into the
   site or a CV — either read the current URL with
   `cd /home/yash/hosting && bin/tunnel-url.sh <claims|workflow|cartographer|banking|claimshield>`
   or move to a named tunnel / Tailscale Funnel for a stable address (brief §5.2).
2. ~~The live demos are ahead of the public repos.~~ **Done** — the landing
   screens, the workflow mobile-layout fix and the emoji removals were pushed to
   the public repos on 2026-10-03 (four grouped commits each). GitHub and the live
   demo agree for claims and workflow. Banking is covered too:
   [`banking-ui`](https://github.com/shreyash-sharma-byte/banking-ui) was
   published with the redesigned client, the welcome page and the login credentials
   panel, and the platform README's screenshots were refreshed to match.

## Where the fuller hosting record lives

`/home/yash/hosting/` — `README.md` is the runbook (topology, ports, layout,
decisions, measured results); `docs/` holds the design records copied into this
folder, plus `portfolio-brief.md` and `portfolio-shots/` as the originals.

The five live apps are served locally on `:8801` (claims), `:8802` (workflow),
`:8803` (cartographer), `:8804` (banking) and `:8098` (ClaimShield).
