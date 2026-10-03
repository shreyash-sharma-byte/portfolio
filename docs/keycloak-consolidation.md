# One Keycloak, many realms

How two applications that used to run their own identity servers now share one —
and why the sharing is not the interesting part, the *issuer* is.

## The shape of the problem

An identity server is not one thing. It is:

```
Keycloak instance            one JVM, one database, one port
  └── realm "claims"         its own users, clients, keys, roles, settings
  └── realm "workflow-realm" its own users, clients, keys, roles, settings
```

Realms are isolated by design: different signing keys, different users, different
login pages, no shared sessions. Nothing in a realm can see anything in another.
So "should these apps share a Keycloak?" is really "do they need separate JVMs?" —
and they don't. Two realms on one instance are as separate as two instances, minus
one JVM's worth of memory.

That is the whole reason this consolidation is possible. The complication is not
realm isolation; it is what Keycloak *tells the browser*.

## Why it is not just two realms on one port

Look at what the `iss` claim in a token is for. When OpenClaimFlow's Spring backend
receives a token, it does not simply verify the signature. It checks:

1. the token is signed by the issuer it trusts (`issuer-uri`), and
2. the token's `iss` claim **equals** that issuer, character for character.

Keycloak builds the issuer from the origin it believes it is served on:

```
https://<host>/realms/<realm>
```

Two instances, two hostnames, no conflict. One instance serving two realms reached
on **different public hostnames** — now there is a real question: which origin does
it advertise for which realm?

The naive answer, `KC_HOSTNAME`, is global: one value for the whole server. Set it
to the claims tunnel and workflow's redirects point at the claims tunnel. Leave it
unset and Keycloak 25 under `start-dev` falls back to advertising `localhost`, which
no remote browser can reach.

## The mechanism: per-realm `frontendUrl`

A realm carries an attribute that outranks the global hostname:

```
realm.attributes.frontendUrl = https://<claims tunnel>
realm.attributes.frontendUrl = https://<workflow tunnel>
```

Keycloak resolves the origin it advertises per realm, highest priority first:

```
realm frontendUrl  ->  global KC_HOSTNAME  ->  the request's own Host header
```

So one server, two realms, two public origins. When it builds the claims realm's
discovery document it says the claims tunnel; when it builds workflow-realm's, it
says the workflow tunnel.

**Verify it, don't trust it.** The decisive test asks with no `Host` header at all,
so nothing request-derived can be involved:

```bash
# no Host header, no X-Forwarded-Host — only realm data can produce these
curl -s localhost:8090/realms/claims/.well-known/openid-configuration | jq -r .issuer
curl -s localhost:8090/realms/workflow-realm/.well-known/openid-configuration | jq -r .issuer
```

If those two print different public origins, `frontendUrl` is doing exactly what you
need. If they print the same thing, you are looking at the global hostname and the
consolidation is not yet configured.

Two realms, one of them strict: claims' backend enforces the issuer, workflow's
Django runs `KEYCLOAK_VERIFY=False` and ignores it entirely. The strict one is what
forces the work; the lax one only needs its redirect URIs right.

## The second half: redirect URIs rotate

The issuer is what the server *says*. The redirect URI is where the server is
allowed to *send the browser back to*. Same trap, different symptom:

```
A quick cloudflared tunnel gets a NEW random hostname every restart.
The old hostname is dead the moment it rotates.
Keycloak will only redirect to a registered URL.
```

So a rotation that updates the issuer but not the client's `redirectUris` fails in
the browser with `Invalid parameter: redirect_uri` (HTTP 400) — while every `curl`
check still passes, because curl never follows the browser's path. This is why
`bin/set-origin.sh` writes both, always, per realm.

## What was actually done

| Step | Why |
|---|---|
| New `keycloak` DB + role on `postgres-unified` | realm data belongs in the shared Postgres, not a dev-file |
| Staged both realm exports into `keycloak/import/` | copies — the originals stay in their project repos |
| Set each realm's `frontendUrl` and added the current tunnel to each client's redirect URIs, **in the staged files** | so a from-scratch build starts correct |
| Started one instance on 8090 (`compose/shared.yml`) | reuses the claims port, so the claims edge needed no change |
| Repointed the workflow edge's `/realms/` from 8091 to 8090 | the retired container's port |
| Repointed Django's `KEYCLOAK_SERVER_URL` at `host.docker.internal:8090` | it reached Keycloak by compose service name before |
| Stopped both old Keycloaks, kept for rollback | — |
| Rewrote `set-origin.sh` against the admin API | rotation is now data, not a container recreate |

## Four traps

**1. The directory importer is filename-sensitive.** A realm named
`workflow-realm` must live in `workflow-realm-realm.json`. Anything else and
Keycloak refuses to boot:

```
ERROR: File name / realm name mismatch. workflow-realm.json, contains realm
       workflow-realm. File name should be workflow-realm-realm.json
```

`claims-realm.json` passed only because the realm is *called* `claims` and the
convention happens to be satisfied. The rule is `<realm-name>-realm.json`.

**2. A realm export is not a deployment manifest.** The workflow export contained
localhost and the tailnet name but not the tunnel — a naive import would have
broken every tunnel login. Exports capture what was configured when they were
written; the deploy origin has to be applied at deploy time.

**3. `docker compose up` resurrects things you retired.** Two ways to get bitten
here. `depends_on` will pull a retired dependency back up (Keycloak's base file
gated startup on the local `db`, so the Postgres we removed came back with it), and
a start script with no service arguments will start *everything* it can see. Fix
for both: put the retired services behind a non-default profile.

```yaml
  db:
    profiles: ["legacy"]      # invisible to `up -d`, explicit to `--profile legacy up -d`
```

**4. A single-file bind-mount serves a stale inode.** Editing
`nginx/workflow.conf` on the host and running `nginx -s reload` inside the container
changed nothing at all: the container's mount still pointed at the *old* file, so it
went on proxying to the retired 8091. Symptom was a 502 on the workflow edge while
the claims edge — pointed at the same port through a different conf — was fine.
`nginx -t` inside the container happily validated the old file, which is the tell
that you are testing the wrong thing. Mount the *directory* where you can; otherwise
recreate the container after a conf change.

## Verifying a real login (not just the discovery document)

Discovery documents prove advertising. They do not prove login. The end-to-end
check is an authorization-code flow, which is what the browser does:

```python
# abbreviated; the full version is how Phase 2 was verified
verifier  = base64.urlsafe_b64encode(os.urandom(48)).decode().rstrip("=")      # PKCE
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")

# 1. the authorization endpoint returns the login form
# 2. POST the credentials to the form's action
# 3. read ?code= out of the 302 Location header
# 4. exchange the code at the token endpoint (with code_verifier)
# 5. decode the access token and look at `iss` — it must be the public origin
# 6. call the API with that token
```

Step 6 is the one that matters for claims: a 401 there means the issuer did not
match; a 200 means the resource server validated a token minted by the shared
instance. (A 403 means authentication *succeeded* and only a role check failed —
also a pass.) For workflow, `grant_type=password` works too, because that realm has
direct access grants enabled:

```bash
curl -s -X POST https://<workflow tunnel>/realms/workflow-realm/protocol/openid-connect/token \
  -d grant_type=password -d client_id=workflow-platform \
  -d username=priya -d 'password=Workflow@123' -d scope=openid
```

## Adding realm #3

1. Export it: `kc.sh export --dir /tmp --realm <name>` from inside a container that
   has it (or start from a hand-written export).
2. Save it as `keycloak/import/<name>-realm.json` — the filename **must** be
   `<realm>-realm.json`.
3. Set `attributes.frontendUrl` to the origin it will be reached on, and add that
   origin to the client's `redirectUris`.
4. Import with `--import-realm` (first start only), or add the realm in the admin
   console if the instance is already running.
5. Add its edge's `/realms/` location pointing at `127.0.0.1:8090` — and remember
   trap 4: recreate the edge, don't just reload.
6. Add it to `set-origin.sh`'s target list so tunnel rotations keep it correct.

## Rollback

Both retired Keycloaks are stopped but intact, behind the `legacy` profile:

```bash
dk compose --project-directory "<claims dir>" -f docker-compose.yml \
           -f hosting/compose/claims.override.yml --profile legacy up -d keycloak
```

The claims edge and Django's `KEYCLOAK_SERVER_URL` would both need pointing back at
their old ports/names. Nothing is deleted, so this is reversible.

## Numbers

| | Before | After |
|---|---|---|
| Keycloak JVMs | 2 (784 MB + 685 MB) | 1 (631 MB) |
| Containers running | 13 | 12 |
| Ports | 8090 + 8091 | 8090 |
| Realms | 2, in 2 places | 2, in 1 place |

**838 MB saved.** The database consolidation saved ~38 MB and was justified on
operational grounds; this one is justified on memory alone.

## Login page: alignment and field borders (measured, not eyeballed)

Two defects in both branded sign-in pages, found by rendering them in a headless
browser and then **measuring** the geometry rather than trusting the look:

1. **The brand block was centred while the card's content was left-aligned.** The
   realm name sits in `#kc-header-wrapper` inside `.pf-v5-c-login__header`, which
   PatternFly gives a 16px inset and centres the text of; the card's own content
   starts at `1px border + 32px body padding = 33px`. The measured result was a
   brand block on a different vertical axis from everything below it.
   Fix: `.pf-v5-c-login__header { padding-inline: 33px }` plus
   `#kc-header-wrapper { text-align: left }`. After the fix the measurement reads
   brand x=33, card title x=33, first label x=33, first input x=34 — one edge.

2. **The fields had no border at all.** Computed `border-width` was `0px` on both
   the `.pf-v5-c-form-control` wrapper and the inner `<input>`, with no
   box-shadow, so an unfocused empty field was invisible against the white card.
   The only visible line was the helper-text separator *below* the password —
   which is why the password looked like an underline field while the
   (autofocused) username looked boxed. Fix: a real `1px solid` hairline on
   `.pf-v5-c-form-control`, the inner input's own border zeroed, and the password
   pair joined into one control — `.pf-v5-c-input-group__item.pf-m-fill >
   .pf-v5-c-form-control { border-top-right-radius: 0; border-bottom-right-radius:
   0 }` with `#password-show-password { border-left: 0; border-radius: 0 7px 7px 0 }`.
   The focus ring then belongs to the group, not the inner wrapper, so it is
   never drawn twice.

Themes are bind-mounted (`keycloak/themes:/opt/keycloak/themes:ro`), so editing a
`brand.css` takes effect on the next request — no container recreate, no realm
round-trip through the admin API. Verify with a **fresh browser profile**: the
sign-in form cannot be reached in a browser that already holds a Keycloak SSO
cookie, and it does not appear at all until the request carries PKCE parameters
(`code_challenge` + `code_challenge_method=S256`) for a client that enforces them
— without them Keycloak returns `302 ... error=invalid_request`.

## Demo credentials on the sign-in pages

Every application that has a login now states its demo accounts on the login page
itself, so a visitor can sign in without being told out-of-band.

| application | login surface | where the panel lives |
|---|---|---|
| OpenClaimFlow (claims) | Keycloak realm `claims` | `themes/claims/login/login.ftl` + `.../resources/css/brand.css` |
| Workflow Management | Keycloak realm `workflow-realm` | `themes/workflow/login/login.ftl` + `.../brand.css` |
| Ledger (banking) | its own Angular route `/login` | component template + component `styles` in `banking-ui/src/app/features/login/login.ts` |

Cartographer and ClaimShield have no login, so there is nothing to show there.

Accounts displayed (one per role — the realms hold more):

- **claims** — `ada.lovelace` (claimant), `adjuster.one` (adjuster L1), `supervisor`
- **workflow** — `priya` (admin), `vikram` (dev), `amit.manager` (QA manager)
- **banking** — `yash@bank.test` (customer), `staff@bank.test` (staff/admin)

### Why the Keycloak panel needed a template override

The themes previously carried only a `brand.css` and no template — which is why
the header descriptor above is injected with a CSS `::after`. The credentials
panel cannot use that trick: the values must be **selectable and copyable**, and
CSS-generated content is neither reliably selectable nor exposed to assistive
technology. So each theme now ships one extra file:

    themes/<realm>/login/login.ftl      # a copy of keycloak.v2's login.ftl

with a `<div class="demo-access">` block inserted at the end of the `form`
section. **Only `login.ftl` is overridden** — `template.ftl`, `field.ftl`,
`buttons.ftl` and the rest still resolve from the parent `keycloak.v2` theme, so
PatternFly v5 wiring is unchanged and the block inherits the card body's own
32px inset. Measured result: panel left edge == field left edge, at 417px
(desktop) and 33px (phone); below 430px the rows stack, because three monospace
columns do not fit a 330px card without truncation.

**This file is version-coupled.** It was copied from Keycloak 26.3.5:

    dk cp hosting-keycloak:/opt/keycloak/lib/lib/main/org.keycloak.keycloak-themes-26.3.5.jar /tmp/kcthemes.jar
    python3 -c "import zipfile;zipfile.ZipFile('/tmp/kcthemes.jar').extract('theme/keycloak.v2/login/login.ftl','/tmp')"

After a Keycloak upgrade, re-copy the template and re-insert the block.

### Restarting: CSS is live, a new template is not

A `brand.css` edit applies on the next request (the themes directory is
bind-mounted). A newly *added template* does not — Keycloak caches compiled
templates, so `login.ftl` only takes effect after:

    dk restart hosting-keycloak

Restart, do **not** recreate: a recreate re-runs the hostname/origin setup.

### Pitfall found while wiring this up

`open(path, "w").write(<expression that raises>)` truncates the file the instant
`open()` is called, because the argument is evaluated only *after* the file is
already empty. A `KeyError` raised by a `.format()` call inside that expression
silently emptied an 8,828-byte stylesheet. Build the complete string first, then
open and write — or write a temp file and `os.replace()`. (Recovered here from
the copy read earlier in the session; the restoring write reported exactly
8,828 bytes.)
