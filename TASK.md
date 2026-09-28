# TASK.md — status & to-dos

_Last updated: 2026-09-24_

## Done ✅

- [x] Project scaffold: Flask app, Dockerfile, docker-compose, requirements, .gitignore
- [x] SQLite seed layer (`app/db.py`), idempotent, clean reset on startup
- [x] Config module, logging, 404/500 error pages, `/healthz`
- [x] **Q1 — ShopSmart (SQL Injection), Set A** — built as a full storefront:
      home/hero, featured, category browse, product detail pages, about page;
      rich seed catalogue (16 products, categories, price/stock/rating).
      Only the search is vulnerable (7-column UNION read); everything else is
      parameterized. Verified end-to-end.
- [x] Instructor answer key for Q1 (updated to 7-column payloads)
- [x] Test suite (`tests/`, pytest) — 11 tests passing
- [x] Project docs: README, CLAUDE.md, PLANNING.md, TASK.md

## Realism direction (decided)

- Scaler = wrapper only. Targets are fictional brands: **Voltix** (store),
  **Meridian** (portal), **DataBridge** (API). Scaler appears on the `/`
  engagement briefing.
- No contest hub / no vulnerability-type labels. `/` is a Scaler "Rules of
  Engagement" briefing listing targets by brand only. Standalone sites.
- Minimal hints: subtle vulns, decoys (e.g. DataBridge `/v1/usage`), realistic
  content. Discovery-first.
- Design language modelled on real best-in-class sites (Stripe-style API docs,
  modern storefront, SaaS portal) with our own brands/assets — no cloned logos.

## Realism status per challenge

- [x] `/` Scaler engagement briefing (wrapper) — done.
- [x] **Q3 DataBridge** — elevated: marketing landing + API reference +
      decoy `/v1/usage`. Done to the "real site" bar.
- [x] **Q1 Voltix (M4, P0)** — full store: home + promo + newsletter, browse
      with sort + in-stock filter + pagination, product pages with specs &
      reviews & add-to-cart, working cart → checkout → order confirmation,
      contact page, shipping/returns pages. Decoys (newsletter/contact) work and
      are non-injectable; search is the only injection point (visible errors, as
      decided). 7 new tests; 29 total passing.
- [ ] **Q1 Voltix (P1)** — optional: customer review submission form.
- [x] **Q2 Meridian (M5, P0)** — full SaaS portal: public marketing landing
      (hero + features + pricing), sign-in, app shell (sidebar + topbar),
      dashboard (stats + usage meter + activity), billing + invoices + invoice
      detail (scoped, safe), team list, settings (profile update + password
      change, both persist), support/FAQ, gated admin. JWT `alg:none` flaw intact
      → admin flag. 6 new tests; 35 total passing. No 500s in edge QA.
- [x] **Q2 Meridian — Slack re-skin** — aubergine workspace sidebar, Slack-green
      buttons, blue active nav, workspace header; existing features/flow unchanged;
      vuln unchanged. 35 tests still pass.
- [x] **Q3 DataBridge (M6)** — finished to §7.3: expanded API reference
      (quickstart, auth, errors, full endpoint list), a **developer dashboard**
      (`/api/dashboard`: account, API key, usage meter, recent events), extra
      endpoints (`/v1/events` decoy, `/v1/health` public), consistent JSON error
      envelope. BOLA flaw + flag unchanged. Self-reviewed via screenshots.
      3 new tests; **44 total passing.**

## Set A — status: COMPLETE (P0 across all three, to the "real app" bar)
- Voltix (store) · Meridian (Slack-style SaaS portal) · DataBridge (API platform)
- Scaler engagement briefing wrapper · no dead controls · self-reviewed visually.
- Next: M7 — deploy to Render for instructor difficulty sign-off.

- [x] **Dead-control sweep (all apps)** — every clickable control now acts:
      Meridian Change plan (persists), Update card (mock+flash), Download receipt
      (real file download), Invite member (adds member), Save notifications, and
      landing pricing "Choose plan" CTAs. Voltix & DataBridge already clean.
      6 new tests; 41 total. Also: stale-DB self-heal + `.dockerignore` fix.

Note: mobile responsiveness dropped (desktop lab env only).

## In progress 🚧

- [ ] Instructor to run Q1 locally / on Render and sign off on difficulty
      (early read: slightly hard for absolute beginners — calibrate later via
      the levers below)

## Done ✅ (continued)

- [x] **Q2 — MemberPortal (Auth & Session), Set A** — full login portal with its
      own identity; JWT session token; verifier insecurely accepts `alg:none`
      → privilege escalation to admin panel where the flag lives. HS256 path is
      safe (strong secret). Answer key + 6 tests added. Verified end-to-end.

- [x] **Q3 — DataBridge API (API Attacks), Set A** — real REST API with dev docs,
      bearer-token auth; `GET /v1/accounts/{id}` has BOLA/IDOR (no ownership
      check) → read the system account (1000) for the flag. Answer key + 5 tests.
      Verified end-to-end.
- [x] **Set A complete** — all 3 challenges built, 21 tests passing.
- [x] Landing page links all three challenges.

## To do — Set B (reattempt, equivalent difficulty)

- [ ] Q1 variant (b1) — different injectable field + new flag
- [ ] Q2 variant (b2)
- [ ] Q3 variant (b3)
- [ ] Decide how Set A vs Set B are served (separate routes? env flag? separate deploy?)

## To do — deploy & handoff

- [ ] Push to GitHub
- [ ] Create Render web service (Docker), get public URL
- [ ] Exclude `instructor/` from student-facing build
- [ ] Warm-up / cold-start note for contest day
- [ ] Final smoke test of every flag path on the live URL

## Q1 difficulty levers (for calibration after instructor feedback)

- Show vs hide DB errors (hidden = blind injection = harder).
- Number of columns in the search query (fewer = easier).
- Keep vs remove the recon step (naming the hidden table for them = easier).
- Hint text on the search page for beginners.

## Decisions to confirm

- [ ] Q1: keep DB errors visible, or go blind (harder)?
- [ ] Set A vs Set B delivery mechanism
