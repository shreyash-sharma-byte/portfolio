# Front-page design spec — the shared standard

**Applies to:** OpenClaimFlow (claims), Enterprise Workflow Management (workflow),
Ledger (banking). All three pre-login front pages must look like siblings.

The reference implementation is the **banking UI**. Its global stylesheet,
`/home/yash/hosting/src/banking-ui/src/styles.css`, is the authority for every
value below. Read it before writing CSS. Do not invent a second design language.

---

## 1. Design intent

A calm, dense, workmanlike **information console**.

- Hierarchy comes from **type scale, weight and spacing** — not from colour,
  boxes or decoration.
- **Colour is reserved for meaning**: the single accent for links / focus / the
  primary action, and the semantic colours for credit / debit / warn.
- The reader should believe an engineer built this for other engineers.
- Monospace numerals and micro-labels are what give the surface its instrument
  character. Use them.

## 2. Hard prohibitions

Reject any of these on sight:

- gradients, glassmorphism, blurred glows, decorative shadows
- emoji anywhere in the UI (code comments are fine)
- hero images, illustration, background photos
- a "3 feature cards in a row" marketing grid
- border-radius above 4px; shadows beyond a 1px hairline
- marketing superlatives ("powerful", "seamless", "revolutionary", "blazing")
- invented capabilities. **Every claim on the page must be traceable to real
  code, real routes, or the project README.**

## 3. Tokens — each app uses its OWN design system

**Do not import another app's palette or typeface.** The shared standard is the
*structure, density, typography hierarchy and prohibitions* — not the colours.
Every one of these three apps already has a design system, and a landing page
that contradicts the app behind it looks like two products stapled together.

| App | Token source (authoritative) | Typeface |
|---|---|---|
| banking (Ledger) | `banking-ui/src/styles.css` — the warm-paper "Ledger" system, accent `#1f4e8c` | IBM Plex Sans / Mono |
| claims | `frontend/src/styles.css` + `frontend/docs/ui-doctrine.md` — the cool-slate enterprise system, accent `#0056b3` | Inter |
| workflow | `workflow_frontend/src/styles.scss` — accent `#4f46e5`, app bg `#f8f9fb` | Inter |

Read your app's stylesheet and use its real token values. If you need a name
your app does not define, alias it to one it does, e.g. in the workflow landing:

```css
--bg: #f8f9fb;        /* var(--bg-app)      */
--ink: #1a1a2e;       /* var(--text-primary) */
--line: #e4e5e7;      /* var(--border-default) */
--accent: #4f46e5;    /* var(--primary)      */
```

Never edit the app's global stylesheet, and never add a webfont the app does not
already load — that silently changes the whole application, not just your page.
The reference below is banking's block, shown as an example of *shape* (a small
set of semantic tokens: paper, ink, one accent, meaning colours, radius, two
font stacks), not as values to copy.

```css
/* shape to mirror — substitute your app's own values */
:root {
  color-scheme: light;
  --bg / --surface / --surface-2
  --ink / --ink-2 / --muted / --faint
  --line / --line-2
  --accent / --accent-strong / --on-accent
  --credit / --debit / --warn  (+ -bg tints)
  --radius: 4px;  --shadow: 1px hairline
  --sans / --mono
}
```

## 4. Accents

| App | accent | strong | rationale |
|---|---|---|---|
| banking (Ledger) | `#1f4e8c` | `#163c6d` | already shipped |
| claims (OpenClaimFlow) | `#0056b3` | `#004a94` | the app's own `--accent-600/700`, matches its Keycloak theme |
| workflow | `#4f46e5` | `#4338ca` | the app's own `--primary` / `--primary-hover`, matches its Keycloak theme |

Colour is reserved for meaning: the accent for links, focus and the single
primary action, and the semantic colours for state. Nothing decorative.

## 5. Typography

- body: `var(--sans)`, `0.9375rem`, `line-height: 1.5`
- `h1` page title: `1.375rem`, weight 600, `letter-spacing: -0.01em`
- page sub / lede: `0.875rem`, `var(--muted)`
- `.eyebrow` — mono, `0.6875rem`, uppercase, `letter-spacing: 0.08em`,
  `var(--muted)`. This is the app's small caps label above the title.
- `.section-title` — `0.8125rem`, weight 600, uppercase, `letter-spacing: 0.06em`
- `.field-label` — `0.75rem`, weight 500, `var(--ink-2)`
- `.hint` — `0.75rem`, `var(--muted)`
- All numerals, references, amounts and dates: `var(--mono)` where the app has
  a mono stack; if it has none, use `ui-monospace, SFMono-Regular, Menlo,
  Consolas, monospace`.
- Fonts: use the typeface the app already loads (banking IBM Plex, claims and
  workflow Inter). Do **not** add or replace a webfont link — changing
  `index.html` alters the entire application, not just the front page.

## 6. Component vocabulary (reuse these class names)

`.page` (max-width 1040px, centred, `padding: 24px 16px 56px`) ·
`.page-narrow` (560px) · `.page-head` · `.page-title` · `.page-sub` ·
`.eyebrow` · `.section-title` · `.card` (1px `--line`, 4px radius, 16px pad,
hairline shadow) · `.field` · `.field-label` · `.control` · `.hint` ·
`.btn` · `.btn-primary` · `.btn-ghost` · `.btn-sm` · `.btn-block` ·
`.alert` `-error` `-success` `-warn` · `.badge` · `.num` · `.text-muted` ·
`.empty` · `.footer`

Buttons: `padding: 8px 14px`, `0.875rem`, weight 500, 4px radius, transparent
1px border; `.btn-primary` fills `--accent`, hover `--accent-strong`;
`.btn-ghost` is transparent with a `--line-2` border, hover `--surface-2`.

Focus is never removed: `outline: 2px solid var(--accent); outline-offset: 1px`
on `:focus-visible`.

## 7. Layout rules

- Single column first; widen out from there.
- Breakpoints: **640px** (stacked → side by side), **960px** (full width).
- Everything must work at 390px wide without horizontal scroll.
- Spacing rhythm: 4 / 8 / 12 / 16 / 24 / 32.
- Lists of capabilities are separated by **hairline rules** (`1px solid
  var(--line)`), not by cards or boxes.

## 8. Front-page anatomy

Every one of the three front pages uses exactly this skeleton, top to bottom:

1. **Top bar** — the app wordmark on the left (`.brand`), and on the right a
   **filled primary** `Sign in` button (`.btn.btn-primary.btn-sm`) for a visitor.
   Not a ghost/outline button: entry has to read as the primary action. The bar is
   `position: sticky; top: 0`, so the way in stays reachable while the visitor
   scrolls a long architecture page. When authenticated, the real navigation and a
   Sign out button replace it (that logic already exists — do not break it).
2. **Entry block, directly after the lede** — before the architecture, so nobody
   has to scroll to find the door. Three elements, stacked and left-aligned, in
   this order:
   - a value line: that this is a **running application with real data, not a
     mock-up**
   - the action: `.btn.btn-primary` "Sign in"
   - the fine print: demo credentials available on request

   Hairline `border-top` and `border-bottom`, 16px vertical padding. Same block at
   every width — do not flip it to a row on desktop; the three sibling apps must
   agree. Repeat the CTA at the very bottom for a reader who worked through the
   page.
3. **Eyebrow** — mono, uppercase: the domain, e.g. `LOSS MANAGEMENT`.
4. **Title** — the product name. Not a slogan.
5. **Lede** — one paragraph, two sentences at most, plain English, saying what
   the system does and for whom.
6. **Capability groups** — two or three groups, each with a `.section-title`,
   then a hairline-separated list of entries. Each entry is a bold
   short label plus a one-line description. This is the substance of the page;
   make it generous and specific.
7. **Technology line** — one muted line: the real stack.
8. **Primary action** — a `.btn.btn-primary` "Sign in", plus a muted line
   telling the visitor what they will get (e.g. demo credentials available
   on request). Never print credentials on the page.
9. **Footer** — the credit line, always the last thing on the page:
   `Made by Shreyash Sharma · LinkedIn · shreyashms2501@gmail.com`
   - name → `https://github.com/shreyash-sharma-byte`
   - `LinkedIn` → `https://www.linkedin.com/in/shreyash-sharma-908b741a9`
   - the address itself → `mailto:shreyashms2501@gmail.com`
   Separator is a middle dot with hairline spacing. All three links carry the
   footer's muted colour and a persistent underline so they read as links without
   shouting. Outbound links open in a new tab with `rel="noopener"`.
   In an **Angular template** the `@` in the email text must be written `&#64;`
   — a bare `@` starts a control-flow block and fails the build (NG5002).
## 9. Copy rules

- Sentence case for descriptions; short. No exclamation marks.
- Say what the thing *does*, concretely. "Atomic transfers with race-free
  overdraft protection" — not "powerful money movement".
- Prefer a number to an adjective where a real number exists.
- Label + consequence reads better than a noun list.

## 10. Engineering constraints

- **Preserve the existing auth wiring exactly.** The front page is presentation
  only. In particular: claims must keep deferring Keycloak init until "Sign in"
  and must keep detecting the returning authorization code in the **URL
  fragment** — not the query string; workflow must keep `check-sso` with its
  silent-check redirect URI. Breaking either breaks login.
- No new npm dependencies. No icon libraries. No CSS frameworks.
- Do not change any API call, route path, guard, or service.
- Stay inside your assigned source tree. Never touch
  `/home/yash/Documents/AI Projects/` (the owner's originals), never run
  `bin/build-*.sh`, never write to `hosting/artifacts/`, never commit or push.

## 11. Class names collide with the app's global stylesheet

**Angular's emulated encapsulation does not protect a component from global
selectors.** A component's own styles get attribute-scoped; a rule in the app's
global stylesheet matches any element in the document, including inside your
component. So reusing a class name the app already defines silently applies that
rule to your page.

This broke the claims landing in the worst possible way: the walkthrough list
used `class="steps"`, the app's global stylesheet already had
`.steps li { display: flex; gap: ... }` for its own stepper, and every text run
and `<span>` in each list item became a separate flex item — the prose rendered
as shattered columns. It compiled cleanly and every string check passed.

**Rule: namespace your classes.** Prefix everything the page introduces
(`lp-` for landing page, or the component name). Before finishing, list every
class your page uses and check each against the app's global stylesheet:

```bash
# every class the page uses, against the global stylesheet
grep -o 'class="[^"]*"' frontend/src/app/landing/landing.html \
  | sed 's/class="//;s/"//' | tr ' ' '\n' | sort -u
```

Treat a hit as a defect to resolve unless the overlap is deliberate (reusing the
app's own `.btn` for the CTA is fine and desirable). A hit that sets `display`,
`grid`, `flex`, `columns` or `position` will break layout.

## 12. Where the architecture goes

App demos and tool demos are not the same page.

- **App demos** (claims, workflow, banking): architecture first. The reader is
  evaluating whether you can build a system, so the topology and the request
  walkthrough come immediately after the lede, before any capability list.
- **Tool demos** (Cartographer, ClaimShield): **the tool stays at the top.** A
  visitor came to use it. The explorer links / the console go directly under a
  short intro, and the pipeline, walkthrough and design notes follow below.

Getting this backwards buries the reason the page exists under four walls of
explanation.

## 13. Version and port numbers must match what the visitor sees

A page is not the place to describe a repo's `docker-compose.yml` if the deployed
demo differs. The workflow page said "Keycloak 25 :8080" — true of the repo's
pinned compose, but the hosted realm is served by a shared Keycloak **26.3**
whose version is printed on the very login page the visitor clicks through to.
Either state the deployed reality or omit the number; never ship a version the
visitor can catch out.
