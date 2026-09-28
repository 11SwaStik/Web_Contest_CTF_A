# PRD — Scaler Web Security Contest (Set A)

**Status:** draft for approval · **Owner:** Samarth · **Last updated:** 2026-09-25

Authoritative product spec. Companion docs: `CLAUDE.md` (conventions & guardrails),
`PLANNING.md` (design notes), `TASK.md` (live tracker), `instructor/answer-keys.md`
(private solutions). If this PRD and another doc disagree, this PRD wins.

> **Guiding idea:** we are building **three real applications** — complete,
> good-looking, fully functional end to end — and hiding **exactly one security
> flaw** in each. A student poking around should experience a normal, polished
> product; the vulnerability is the only thing that behaves "wrong," and only
> when deliberately attacked. If a feature looks clickable, it works.

---

## 1. Purpose

A hands-on, pass/fail **eligibility gate** for a Scaler web-security module.
Students find and exploit a real vulnerability in each of three believable
applications and submit one flag per app. Realism is a first-class requirement:
the apps must be indistinguishable from production software until attacked.

## 2. Goals / Non-goals

**Goals**
- Test practical exploitation of 3 core skills: SQL injection, auth/session,
  API access control.
- Deliver **three production-quality apps** with complete, working features and
  strong design — the vulnerability is embedded, not the point of the UI.
- Discovery-first: no challenge framing; students recon a real product.
- Cheap to run, easy to operate, fair and repeatable (clean state per run).

**Non-goals (this project)**
- MCQs and the Docker lab (handled separately by the instructor).
- The other 11 module topics.
- Automated flag submission/scoring (instructor validates flags).
- Set B / reattempt (built only after Set A sign-off).
- **Real external integrations** — payment capture, real email/SMS delivery, and
  real third-party APIs are **mocked** with realistic, fully-working *flows*
  (e.g. placing an order returns a real order number; no card is charged). Mocked
  ≠ dead: the flow completes and gives proper feedback.

## 3. Users

- **Student (attacker):** intermediate learner; gets target links, ~25 min each,
  submits one `FLAG{...}` per target.
- **Instructor:** deploys, hands out links, validates flags, tunes difficulty.
  Uses `instructor/answer-keys.md`.

## 4. Contest model

- 3 targets, **independent** (failing one never blocks another).
- One **static** `FLAG{...}` per target, retrievable **only** via the intended
  exploit — never by reasoning, and never visible during normal use.
- ~25-min solve per target for an intermediate student.
- Pass/fail gate (threshold owned by the instructor's platform).
- **Set A** now; **Set B** (equivalent variants) after Set A sign-off.

## 5. Product principles (apply to every target)

1. **Real app first.** Each target is a coherent product with a clear value
   proposition, complete primary user flows, and believable seed data.
2. **Functional completeness — no dead ends.** Every visible control does
   something real: links navigate, forms validate + submit + give feedback,
   buttons act. Nothing is a placeholder that silently does nothing. Where a
   feature is out of scope to fully build, it is a *mock with a working flow and
   honest copy* (e.g. "This is a demo store — no payment is taken").
3. **All states handled.** Empty, loading (where relevant), success, error,
   not-found, unauthorized — each state has a designed screen. No raw tracebacks
   except where a vulnerability intentionally leaks them.
4. **No challenge tells.** No vulnerability-type labels anywhere student-facing.
   Only the reward screen after a solve acknowledges the flag.
5. **Scaler = wrapper only.** Targets are fictional brands (Voltix, Meridian,
   DataBridge). Scaler appears only on the `/` engagement briefing.
6. **Standalone products.** Each target is self-contained with its own identity
   and navigation. No cross-links between targets.
7. **Discovery-first / minimal hints.** Subtle vulnerability; ≥1 **decoy**
   (non-vulnerable input or benign endpoint) per target.
8. **Design language** modelled on best-in-class real sites (modern storefront,
   SaaS dashboard, Stripe-style API docs) with our own brand/assets — no cloned
   logos or impersonation of a real company.
9. **Sound engineering.** Only the intended flaw is vulnerable; all sibling
   functionality is safe (parameterized queries, hashed passwords, proper authz).

## 6. Shared design system (quality bar)

- **Layout:** consistent header/nav + footer per app; max content width; generous
  spacing; card-based components; clear visual hierarchy.
- **Type:** system font stack; defined scale (page title / section / body / meta).
- **Color:** each app has its own palette (Voltix indigo, Meridian teal,
  DataBridge dark/cyan). Sufficient contrast (WCAG AA for text).
- **Components:** buttons (primary/secondary/ghost/disabled), inputs with focus
  and error styles, badges/tags, tables, cards, alerts/toasts, breadcrumbs,
  pagination, empty states, modals/confirm where needed.
- **Responsive:** works down to ~360px; nav collapses; grids reflow; no
  horizontal scroll except intentional (code blocks/tables).
- **Feedback:** every form shows validation + success/error; destructive actions
  confirm; flash/toast messages for actions.
- **Accessibility:** labels on inputs, alt text, keyboard-focusable controls,
  semantic headings.

---

## 7. Per-target specifications

Priorities: **P0** = must be built and fully working for Set A; **P1** =
build if time allows, otherwise present as an honest mock (still no dead ends).

### 7.1 Target 1 — Voltix (Consumer electronics store · SQL Injection)

**Value prop:** a modern direct-to-consumer electronics store (desk gear,
peripherals, audio, displays, storage).

**Primary user flows**
1. Browse → filter/sort a category → open a product → add to cart → checkout →
   order confirmation. *(P0, fully working)*
2. Search for a product → view results → open a product. *(P0 — search is the
   vulnerable surface)*
3. Read/write a product review. *(P1)*
4. Subscribe to newsletter / send a contact message. *(P0 decoys — must work)*

**Page / route inventory**
- `/shop` — home: hero, promo banner, top-rated, category highlights, newsletter.
- `/shop?category=<slug>` — category browse with **sort** (price/rating/newest)
  and **in-stock filter**, pagination.
- `/shop?q=<term>` — search results (sortable, paginated, no-results state).
  **← SQL injection lives here.**
- `/shop/product/<id>` — detail: gallery, price, stock, rating, description,
  **specs table**, **reviews**, add-to-cart, related products, breadcrumbs.
- `/shop/cart` — cart: line items, qty update, remove, subtotal, empty state.
- `/shop/checkout` — shipping form (validated), order summary.
- `/shop/order/<number>` — order confirmation (mock payment, real order number).
- `/shop/about`, `/shop/shipping`, `/shop/returns`, `/shop/contact` — static +
  working contact form.

**Functional requirements**
- Cart persists in the session; badge count updates; totals compute correctly. *(P0)*
- Category sort + filter + pagination actually re-query and reflect the choice. *(P0)*
- Checkout validates fields, creates an order row, shows confirmation with a
  generated order number; clearly a demo (no real charge). *(P0)*
- Newsletter + contact forms validate, persist, and show success. *(P0, decoys)*
- Reviews render from data; optional submit form persists a review. *(P1)*

**Data model:** `products`, `categories`, `reviews`, `orders`, `order_items`,
`newsletter_subscribers`, `contact_messages`, `internal_flags`.

**Embedded vulnerability:** SQL injection in the **search** query (string
concatenation); 7-column result rendered as product cards. All other queries
(catalogue, product, cart, orders, reviews) are parameterized.

**Flag:** `FLAG{un10n_b4s3d_sql1_r3c0n_a1}` — in `internal_flags`, reachable only
via a cross-table (UNION) read.

**Decoys:** newsletter form, contact form, review form, category filter inputs —
all safe/parameterized. Search is the only injectable input.

**Difficulty:** medium. Lever: search errors **visible** (easier) vs **blind**
(harder). *(decision needed — see §11)*

---

### 7.2 Target 2 — Meridian (SaaS customer portal · Auth & Session)

**Value prop:** a business "customer portal" where a company's users manage their
account: dashboard, billing, team, settings.

**Primary user flows**
1. Sign in → land on dashboard → view usage/activity. *(P0)*
2. View billing: current plan + invoice history → download an invoice (mock). *(P0)*
3. Manage team: list members, invite a member (form), change a member's role. *(P1)*
4. Edit profile / change password in settings. *(P0)*
5. Attempt the admin area → blocked as a member. *(P0 — the gated target)*

**Page / route inventory**
- `/portal` — public marketing landing + "Sign in" (or redirect to login).
- `/portal/login`, `/portal/logout` — auth (JWT session cookie).
- `/portal/dashboard` — overview widgets: plan, usage meter, recent activity.
- `/portal/billing` — plan, invoice table, payment method (mock), invoice detail.
- `/portal/team` — members list, roles, invite form. *(P1)*
- `/portal/settings` — profile edit (works), change password (works), prefs.
- `/portal/admin` — **admin-only**; members get a designed 403. Flag lives here.
- `/portal/support` — help/FAQ page.

**Functional requirements**
- Real login with hashed passwords; session via JWT cookie; logout clears it. *(P0)*
- Dashboard widgets reflect the signed-in user's real data. *(P0)*
- Billing shows the user's invoices from data; invoice "download" returns a
  generated invoice view/file (mock, but real content). *(P0)*
- Settings: profile update persists; password change re-hashes and works. *(P0)*
- Team invite/role change persists within the account. *(P1)*
- Admin link is visibly gated for members (not hidden) → tempting but 403. *(P0)*

**Data model:** `users` (profile, plan, role, company), `invoices`,
`team_members`, `activity_log`.

**Embedded vulnerability:** JWT session verifier insecurely accepts `alg:none`
→ a member forges an admin token and reaches `/portal/admin`. Correctly-signed
HS256 path is safe (strong secret).

**Flag:** `FLAG{jwt_n0ne_alg_pr1v_esc_a2}` — shown on the admin panel.

**Decoys:** billing, team, settings are fully real but not exploitable; the
member's own correctly-signed token cannot reach admin.

**Given to students:** member creds `alice / member2026` (also `bob / hunter2meh`).

**Difficulty:** medium. Lever: switch flaw to weak-secret HS256 (harder) if needed.

---

### 7.3 Target 3 — DataBridge (Developer API platform · API Attacks)

**Value prop:** a Stripe-style data API product: marketing site, developer
reference, a web dashboard for keys/usage, and a real JSON API.

**Primary user flows**
1. Land on marketing → read docs/reference → grab the sandbox key. *(P0, done)*
2. Call the API: current account, usage, list/among resources. *(P0)*
3. Use the web **dashboard**: view API key, usage, account details. *(P1)*

**Page / route inventory**
- `/api` — marketing landing. *(done)*
- `/api/docs` — API reference: quickstart, auth, endpoints, errors, changelog. *(done, expand)*
- `/api/dashboard` — web dashboard: sandbox key, usage chart, account info. *(P1)*
- JSON API under `/api/v1`:
  - `GET /v1/accounts/me` — current account. *(done)*
  - `GET /v1/accounts/{id}` — **BOLA lives here.** *(done)*
  - `GET /v1/usage` — benign, caller-scoped (decoy). *(done)*
  - `GET /v1/events` — recent events for the caller (benign, paginated). *(P1 decoy)*
  - `GET /v1/health` — status. *(P1)*

**Functional requirements**
- Consistent JSON envelope + error format with proper status codes. *(P0)*
- Bearer-token auth enforced on all `/v1` data endpoints. *(P0)*
- Reference documents every endpoint accurately with working curl examples. *(P0)*
- Dashboard reflects the sandbox account's real key/usage. *(P1)*

**Data model:** `api_accounts`, `api_usage` (derived), `api_events` *(P1)*.

**Embedded vulnerability:** BOLA/IDOR on `GET /v1/accounts/{id}` — authenticated
but no ownership check; the internal system account (1000) holds the flag.

**Flag:** `FLAG{b0la_id_3num_ap1_a3}` — `private_note` of account 1000.

**Decoys:** `/v1/usage`, `/v1/events` (benign, correctly scoped).

**Given to students:** sandbox key on the reference; own account id 1007.

**Difficulty:** medium. Lever: id range / discoverability.

---

## 8. Technical requirements

- **Stack:** Python + Flask + SQLite (stdlib), one app, one blueprint per target,
  shared components/templates where sensible.
- **State:** DB seeded on startup; ephemeral hosting → clean identical state per
  run. Session data (cart, flashes) in Flask session.
- **Hosting:** Render free tier (Docker web service), public HTTPS URL.
- **Portability:** relative paths only; runs unchanged on another machine via
  `docker compose up` or a plain venv.
- **Security:** `instructor/` and `tests/` excluded from the deployed image;
  answer keys never shipped.
- **Quality gate:** pytest suite (functional + security invariants).

## 9. Acceptance criteria

**Per target**
- [ ] Real product: complete primary flows work end to end; ≥ the P0 pages exist
      and function; believable data; own identity; no vuln labels.
- [ ] **No dead ends:** every visible control navigates/acts; mocks have honest
      copy and a completing flow; all states designed (empty/success/error/404/403).
- [ ] Exactly one flag; retrievable only via the intended vulnerability class.
- [ ] Test proves the exploit recovers the flag.
- [ ] Test proves the flag is NOT exposed during normal use.
- [ ] ≥1 decoy present and confirmed non-exploitable.
- [ ] Only the intended flaw is vulnerable; sibling features are safe.
- [ ] Solvable in ~25 min by an intermediate student (instructor-confirmed).

**Global**
- [ ] `/` is the Scaler briefing; no vulnerability-type labels leak (test-checked).
- [ ] Full pytest suite green.
- [ ] Runs via `docker compose up` and via plain venv.
- [ ] Desktop layout is clean (lab env only; mobile not required).
- [ ] Deployed to Render; app warmed before the contest window.
- [ ] `instructor/` excluded from the deployed image.

## 10. Milestones

- **M1–M3 (done):** scaffold; all 3 vulns built; realism overhaul (Scaler
  wrapper, rebrand, DataBridge elevated).
- **M4 — Voltix full build** to §7.1 + acceptance criteria (cart, checkout,
  product detail, reviews, decoy forms, states).
- **M5 — Meridian full build** to §7.2 (dashboard, billing, settings, team,
  gated admin, states).
- **M6 — DataBridge finish** to §7.3 (docs expansion, dashboard, extra
  endpoints, error envelope).
- **M7 — Deploy Set A to Render; instructor difficulty sign-off.**
- **M8 — Build Set B** (equivalent variants) to the calibrated difficulty.
- **M9 — Final deploy + handoff.**

## 11. Decisions & open questions

**Decided (2026-09-25)**
- **Voltix error feedback:** visible DB errors (realistic discovery signal;
  code structured so it can flip to blind later if the instructor wants harder).
- **Build scope:** P0 first across all three apps, then a P1 pass.
- **Meridian visual direction:** Slack-inspired look (aubergine sidebar, Slack
  green primary, blue active nav) applied to the existing portal features. The
  vulnerability (JWT `alg:none` → admin) is unchanged.
- **No mobile responsiveness:** the contest runs only in the desktop lab
  environment. Design for desktop; do not invest in mobile layouts.

**Open**
- **Set A vs Set B delivery:** separate deploy? env flag? separate paths?
  (Deferred to M7.)
