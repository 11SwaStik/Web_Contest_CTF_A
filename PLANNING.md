# PLANNING.md — contest design

## Purpose

A hands-on, pass/fail **eligibility gate** for a web/API security module. Not a
ranking contest — it checks whether a student can actually perform the core
skills before they're eligible for the next stage. Three practical challenges,
one flag each.

## Why these three topics

The module covers 14 topics; three questions can't test all of them, so we pick
the three most representative "you don't pass without this" skills, spanning
injection, access control, and APIs:

- **Q1 — SQL Injection** — the canonical server-side injection skill.
- **Q2 — Auth & Session Attacks** — access-control / identity skill.
- **Q3 — API Attacks** — modern API-layer skill; shows breadth beyond classic web.

Topics intentionally dropped for this contest: XSS, CSRF/clickjacking, SSRF,
NoSQL/command injection, business logic, HTTP request smuggling, secure coding,
web recon, API recon, GraphQL, SOAP/XML. (Smuggling is a poor fit for lightweight
hosting; secure coding is defensive and suits a written question, not a flag.)

## Format rules

- One `FLAG{...}` per challenge, submitted by the student and checked against a
  stored value (same manual validation the instructor already uses for labs).
- **No partial credit within a challenge** — one flag = solved or not.
- Challenges are **fully independent** (separate routes, separate data).
- Target time: ~25 min per challenge for an intermediate student.

## Set A / Set B (reattempt)

The contest is valid for one day; a student who misses it reattempts with **Set
B**. Set B must be **equivalent** to Set A — same topic, same difficulty,
different instance and flag — so the makeup is fair. Model: 3 slots × 2 variants.

| Slot | Topic | Set A | Set B |
|------|-------|-------|-------|
| Q1 | SQL Injection | ShopSmart — UNION read via search | different field + flag (TBD) |
| Q2 | Auth & Session | MemberPortal (TBD) | equivalent variant (TBD) |
| Q3 | API Attacks | DataBridge API (TBD) | equivalent variant (TBD) |

## Per-challenge design

### Q1 — ShopSmart (SQL Injection) — BUILT (Set A)

- Route `/shop?q=`. Product search builds SQL by string concatenation.
- Flag lives in an `internal_flags` table the UI never queries; only reachable by
  injecting across tables (UNION-based read).
- Error messages left visible (error-based feedback) — a fair hint for a gate.
  Can be hardened to blind injection if we want it harder.

### Q2 — MemberPortal (Auth & Session) — TO BUILD

- Idea space: session/identity flaw where the flag sits behind an account or area
  the student shouldn't normally reach. Exact mechanism TBD on build.

### Q3 — DataBridge API (API Attacks) — TO BUILD

- Idea space: small REST/JSON API with an access-control or auth flaw; flag
  returned by an endpoint reached improperly. Exact mechanism TBD on build.

## Infrastructure

- **Stack:** Flask + SQLite, single container.
- **Host:** Render free tier (Docker web service). Cold-start on free tier — warm
  the app right before the contest window.
- **Cost:** $0 on SQLite (no separate DB service). Upgrade path to MySQL is a
  config change if ever needed.
- **Hosting the DB:** none needed — SQLite file lives in the app container and is
  reseeded on startup.

## Open questions

- Difficulty calibration per challenge (confirm after instructor runs Set A).
- Whether Q1 errors stay visible or go blind.
- Exact Q2 / Q3 mechanisms.
