# 🔍 CADENCE

> **"cause every market move has a rhythm"**

CADENCE is **not a stock watchlist**. It remembers what you saw on your
last visit and investigates what has *meaningfully* changed since then — turning
important movements into evidence-backed **Investigation Cases**, ranking them by
how urgently they deserve your attention, and replaying the story in an animated
**Market Time Machine**.

It ships with two clearly separated modes:

- **Detective Mode** — the educational, research-oriented analysis engine above.
  It never gives buy / sell / hold recommendations, and it uses **no external
  market, news or LLM APIs** — every price, headline and model runs locally from
  a reproducible synthetic dataset.
- **Live Markets** — a separate feature that fetches **real** quotes and daily
  charts for any symbol (India or worldwide) via the [Twelve Data](https://twelvedata.com)
  API. It has no Attention Score, anomaly detection, or Evidence Court — it's a
  plain live-quote lookup, kept intentionally apart from Detective Mode's engine.

---

## Table of contents

1. [Problem statement](#problem-statement)
2. [The solution](#the-solution)
3. [Why CADENCE is different](#why-cadence-is-different)
4. [Main features](#main-features)
5. [The Market Time Machine](#the-market-time-machine)
6. [Architecture](#architecture)
7. [MongoDB Atlas setup](#mongodb-atlas-setup)
8. [Environment variables](#environment-variables)
9. [Offline dataset strategy](#offline-dataset-strategy)
10. [Definition of "meaningful change"](#definition-of-meaningful-change)
11. [Attention Score formula](#attention-score-formula)
12. [ML methodology](#ml-methodology)
13. [Data limitations](#data-limitations)
14. [Installation](#installation)
15. [Seeding the database](#seeding-the-database)
16. [Running the app](#running-the-app)
17. [Tests & builds](#tests--builds)
18. [Three-minute demo flow](#three-minute-demo-flow)
19. [Scalability strategy](#scalability-strategy)
20. [Deployment (Render + Vercel)](#deployment-render--vercel)
21. [Educational disclaimer](#educational-disclaimer)

---

## Problem statement

A normal watchlist tells a user that a stock *moved*. It does not tell them
whether that movement was **unusual**, what **evidence** explains it, or whether
it actually **deserves their attention**. Users drown in green-and-red numbers
and miss the two or three changes that genuinely matter — especially the ones
that happened while they were away.

## The solution

CADENCE takes a snapshot of what you saw, and on your next visit (or
after the simulated market clock advances) it:

1. Recomputes a rich set of statistics for every stock, using **only
   information available at or before each timestamp** (no future-data leakage).
2. Decides which changes are **meaningful** — unusual relative to a stock's *own*
   history, or corroborated by several independent signals.
3. Converts meaningful events into **Investigation Cases**: verdict, confidence,
   severity, an **Evidence Court** of four "detectives", supporting *and*
   counter-evidence, a deterministic plain-language explanation, related local
   headlines, and data-quality caveats.
4. Ranks cases by an explainable **Attention Score (0–100)** and your personal
   **attention threshold** + **daily attention budget**.
5. Lets you **replay** any event in the **Market Time Machine** and export a
   shareable **Change Story Card**.

## Why CADENCE is different

| A normal watchlist | CADENCE |
| --- | --- |
| "TCS is +4% today" | "TCS moved 4.1σ beyond its own normal range on 5.2× volume while its sector moved +0.7% — this is stock-specific" |
| Every fluctuation shown equally | Only meaningful changes; ranked by an explainable Attention Score |
| No memory between visits | Remembers your acknowledged snapshot and briefs you on what you missed |
| Price only | Price, volume, volatility regime, market-relative, sector-relative, local-news activity, **and data reliability** |
| Black-box or no model | Evidence Court + score breakdown + counter-evidence, all deterministic |
| — | Animated **Market Time Machine** replay of the event |
| Silent on bad data | Stale / missing / conflicting data **visibly reduces confidence** |

## Main features

- **Since You Left briefing** — *"You were away for 36 simulated market hours. We
  found 6 changes, but only 3 deserve your attention."* Each watchlist item is
  classified **Important / Investigating / Explained / Normal / Insufficient data**.
- **Investigation Cases** — 12 possible verdicts (unusual price+volume,
  sector-driven, market-wide, news-supported, **price activity before recorded
  news**, headline noise, volatility-regime change, possible breakout/breakdown,
  conflicting evidence, insufficient data, normal movement).
- **Evidence Court** — Stock / Volume / Sector / News detectives, each returning a
  finding, evidence list, confidence and a stance (*supports / explains it /
  inconclusive*), combined into one verdict.
- **Explainable Attention Score** — component breakdown, confidence %, severity,
  top-3 reasons, supporting + counter-evidence, data-quality warnings.
- **Market Time Machine** — animated, interactive replay (see below).
- **Change Story Card** — shareable PNG / printable card, rendered entirely in the
  browser.
- **Data-quality honesty** — Fresh / Delayed / Stale / Missing / Conflicting, with
  a dataset-health dashboard.
- **Real accounts** — email + password signup/login (bcrypt-hashed, JWT bearer
  tokens); state persists in MongoDB Atlas across sessions and devices.
- **Per-user demo clock** — Advance / Reset the simulated market time.
- **Live Markets** — search any real stock (India or worldwide) and see a live
  quote + daily chart via Twelve Data, entirely separate from Detective Mode.

## The Market Time Machine

A dedicated route (`/time-machine/:symbol`) that replays what happened to a stock
between two points in the dataset:

- The **price line draws itself** over time; **volume bars** and the
  **stock-vs-sector-vs-market** chart update frame by frame.
- **Anomaly markers** appear at the exact bar they were detected — amber for
  moderate, a subtle **red pulse** for serious (respecting `prefers-reduced-motion`).
- **Local-news markers** flash in at their correct timestamp with a distinct icon.
- The **Attention Score gauge**, **verdict**, and **"who moved first?"** update live.
- **Play / Pause / Restart / Step / Speed (0.5×–4×) / drag-scrub** transport.
- Cases detected during the replay are one click away.

It is a **functional feature driven by the same engine as the rest of the app**,
not a canned animation.

## Architecture

```
cadence/
├── backend/            FastAPI · Pandas/NumPy/scikit-learn · Motor (MongoDB)
│   ├── app/
│   │   ├── api/         REST routes (auth, stocks, watchlists, briefings,
│   │   │                cases, replay, demo-clock, data-quality, live-market, meta)
│   │   ├── core/        config, security (hashing/JWT), logging, error handling
│   │   ├── db/          Mongo client + a file-backed local store (same API)
│   │   ├── repositories/  data-access layer, one class per collection
│   │   ├── schemas/     Pydantic models
│   │   ├── ml/          features · anomaly · sentiment · scoring · verdict ·
│   │   │                detectives · explanation   (+ scoring_weights.json)
│   │   ├── services/    analysis engine, briefing, demo clock, replay,
│   │   │                data quality, seeding, live-market (Twelve Data client)
│   │   └── data/        deterministic dataset generator + loader
│   ├── scripts/         seed.py, diagnose.py
│   └── tests/
├── frontend/           React · TypeScript · Vite · Tailwind v4 · Recharts ·
│   └── src/             shadcn/ui (base-lyra) + Vercel AI Elements · TanStack
│                        Query · React Router
├── data/generated/     the committed Offline Research Dataset (CSV + JSON)
├── render.yaml         Render (backend) deploy config
└── docs/               ARCHITECTURE · DEMO_SCRIPT · MODEL_CARD ·
                        DATA_DICTIONARY · SCENARIO_MANIFEST
```

The **frontend talks only to the FastAPI backend** and never connects to MongoDB.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full picture.

### Persistence: MongoDB Atlas, with an offline fallback

`DB_BACKEND` selects the store:

| value | behaviour |
| --- | --- |
| `mongo` | MongoDB Atlas / any MongoDB via `MONGODB_URI` (**production path**) |
| `memory` | file-backed local store at `backend/.local_store/` — **zero external services**, still survives restarts on one machine |
| `auto` *(default)* | `mongo` if `MONGODB_URI` is set and reachable, else `memory` |

The local store implements the same async Mongo-style API the repositories use,
so the code path is identical. This guarantees the demo runs even with **no
internet at all** while keeping MongoDB Atlas first-class.

## MongoDB Atlas setup

1. Create a free **M0** cluster at <https://cloud.mongodb.com>.
2. **Database Access** → add a user (username + password).
3. **Network Access** → allow your IP (or `0.0.0.0/0` for a hackathon).
4. **Connect → Drivers** → copy the `mongodb+srv://…` string.
5. Put it in `backend/.env` (see below) and set `DB_BACKEND=mongo`.
6. Seed: `python -m scripts.seed`. Indexes are created programmatically and
   idempotently (see [MongoDB indexes](#mongodb-collections--indexes)).

**Never** commit `.env`, hard-code credentials, log the full connection string,
or point tests at the production database — the code enforces the last one.

## Environment variables

Copy [`.env.example`](.env.example) to `backend/.env`:

```env
DB_BACKEND=auto                     # auto | mongo | memory
MONGODB_URI=mongodb+srv://USER:PASS@CLUSTER/?retryWrites=true&w=majority
MONGODB_DB_NAME=cadence
MONGODB_TEST_URI=mongodb+srv://USER:PASS@CLUSTER/?retryWrites=true&w=majority
MONGODB_TEST_DB_NAME=cadence_test
BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DEMO_CLOCK_ADVANCE_BARS=18

# Auth — required in production (APP_ENV=prod fails startup without it)
JWT_SECRET_KEY=                     # e.g. `openssl rand -hex 32`
JWT_ALGORITHM=HS256

# Live Markets — optional; without it, /api/live/* returns 503
# market_data_not_configured and Detective Mode is unaffected
TWELVE_DATA_API_KEY=
```

Frontend (`frontend/.env`, optional — the default works):

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

Startup validation prints clear warnings for a missing dataset or an
`mongo`-without-URI misconfiguration.

## Offline dataset strategy

`backend/app/data/generator.py` deterministically synthesises (fixed seed `42`):

- **15 stocks · 5 sectors · 1 market index (NIFTYMD)**
- **160 trading days × 7 hourly bars** (09:15–15:15 IST) — daily OHLCV per bar
- **~250 timestamped local headlines** (baseline chatter + scenario-specific)
- **data-quality incidents** (stale / missing / conflicting)
- **16 deliberately injected scenarios** — a stock-specific spike, a whole sector
  falling, a market-wide crash, volume-without-price, a volatility-regime change,
  positive-news-negative-price, **price activity before the recorded headline**,
  missing data, stale data, conflicting sources, and normal movement that must
  **not** be flagged.

A **private** `data/generated/scenario_manifest.json` records each scenario's
expected verdict. **The inference engine never reads it** — only the automated
tests do (verified by `test_manifest_not_referenced_by_engine_module`).

`data/generated/` is committed so the app runs with no build step and no network.
Regenerate with `python -m app.data.generator` (from `backend/`).

## Definition of "meaningful change"

Not a universal percentage threshold. A change is meaningful when it is **unusual
relative to that stock's own history**, or when **several independent signals
agree**. The engine computes, trailing-only, at every bar:

percentage return · **robust** return z-score (median/MAD, so a big move doesn't
hide itself) · episode (7-bar) return z-score · volume ratio & z-score · rolling
volatility (fast/slow) & regime ratio · market-adjusted return (rolling beta) ·
sector-adjusted return (leave-one-out) · distance from moving average · drawdown ·
breakout / breakdown strength (ATR units) · local-news count change · local-news
sentiment shift · data freshness · **signal agreement** (how many axes fire).

## Attention Score formula

Additive, fully explainable, weights in **one file**:
[`backend/app/ml/scoring_weights.json`](backend/app/ml/scoring_weights.json).

| Component | Max points | Driven by |
| --- | --- | --- |
| Price surprise | 20 | max(single-bar z, episode z), convex ramp |
| Volume anomaly | 15 | volume ÷ rolling median |
| Sector divergence | 15 | cumulative stock-specific move vs sector peers |
| Market divergence | 10 | cumulative move vs index (beta-adjusted) |
| Volatility-regime change | 15 | fast/slow volatility ratio **or** sustained choppiness |
| News relevance & sentiment shift | 15 | change in local-news activity + direction |
| Signal agreement | 10 | number of independent axes that fire |

`score = clamp(Σ components, 0, 100)`.

**Data-quality problems reduce *confidence*, never the score:** stale −25,
missing −40, conflicting −15, delayed −10, short history −20, thin news −5,
isolation-forest-untrained −8; confidence is clamped to `[20, 100]`.

Every score returns: final score, component breakdown, confidence %, severity,
top-3 reasons, supporting evidence, counter-evidence, data-quality warnings.

## ML methodology

Everything runs locally, is explainable, and is deterministic (fixed
`random_state`). Full details in [docs/MODEL_CARD.md](docs/MODEL_CARD.md).

- **Statistical anomaly detection** — robust rolling z-scores, ratios,
  volatility-regime comparison, sector/market-relative returns. *Primary signal.*
- **Isolation Forest** (scikit-learn) over 6 standardised features — a
  **supporting** signal only; skipped with a confidence penalty if data is thin.
- **Local-news sentiment** — a TF-IDF + Logistic Regression pipeline trained at
  process start from the bundled `news_training.csv` (~600 rows, < 1 s). No model
  download. Falls back to transparent keyword rules if the data is missing.
- **Event-type classification** — documented keyword rules (earnings, acquisition,
  regulation, leadership, product launch, legal, analyst action, financing,
  operational).
- **Verdict** — a deterministic decision tree; the order of checks *is* the
  priority. **No LLM.** Explanations come from templates.
- **Responsible wording** — pre-news activity is described as *"unexplained
  activity occurred before the first related headline in this dataset"*, never as
  proof of misconduct.

## Data limitations

- Detective Mode's dataset is synthetic — **not real market data**. It is
  realistic in structure, not in identity; company names label sectors, nothing
  more. (Live Markets, in contrast, is real — see above.)
- The `local_wire` news feed is modelled as unverified background chatter; only
  the curated `research_primary` feed is treated as "material" for the
  price-before-news test. This is a modelling choice, documented in the model card.
- No holiday calendar; trading days are simply weekdays.
- Isolation Forest is trained on the whole (synthetic) history at once — fine for
  a prototype, not how you would do it in production.
- Sentiment labels for training are template-derived, so the classifier mostly
  learns the templates. Documented and acceptable for the prototype.

## Installation

Prerequisites: **Python 3.11–3.13**, **Node 18+**. No Docker.

```bash
# 1. Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env               # edit if you want MongoDB Atlas
python -m app.data.generator          # (optional) regenerate the dataset

# 2. Frontend
cd ../frontend
npm install
cp .env.example .env                  # optional
```

## Seeding the database

```bash
cd backend && source .venv/bin/activate
python -m scripts.seed                # idempotent — safe to run repeatedly
python -m scripts.seed --fresh        # regenerate the dataset first
python -m scripts.seed --test         # seed the TEST database only
```

Seeding inserts market observations, precomputed features, local news,
data-quality events, and ~58 Investigation Cases for Detective Mode. It **does
not duplicate** anything on re-run. User accounts are created by real signup
(`POST /auth/signup`), not by seeding.

> The backend also **auto-seeds on first startup** if the cases collection is
> empty, so `uvicorn app.main:app` works with no separate step. `scripts/seed.py`
> remains the explicit path (and the only one that supports `--fresh` / `--test`).

## Running the app

```bash
# Terminal 1 — backend  (http://localhost:8000, docs at /docs)
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend  (http://localhost:5173)
cd frontend
npm run dev
```

Open <http://localhost:5173> and create an account (name, email, password) — or
log back in if you've already signed up.

## Tests & builds

```bash
# Backend
cd backend && source .venv/bin/activate
pytest                               # unit + service + API + scenario tests
pytest tests/test_scenarios.py -q    # just the injected-scenario verification
python -m scripts.diagnose           # human-readable classification report

# Frontend
cd frontend
npm run typecheck                    # tsc --noEmit
npm run lint                         # eslint, zero warnings
npm run test                         # vitest
npm run build                        # tsc -b && vite build
```

MongoDB integration tests run only when `MONGODB_TEST_URI` is set and refuse to
touch a database whose name is not the configured test DB.

## Three-minute demo flow

The full script is in [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md). In short:

1. **0:00** — "A normal watchlist says a stock moved. CADENCE says
   whether it was unusual, what explains it, and whether it deserves attention."
2. **0:30** — Dashboard → **Advance Market Time** twice → *"You were away for 36
   simulated market hours. We found 6 changes, but only 3 deserve your attention."*
3. **1:00** — Open the top case (**TATAMOTORS — Unusual price and volume
   activity**): Attention Score 71, Evidence Court, sector comparison, volume
   anomaly, related news, supporting + counter-evidence.
4. **1:45** — **Market Time Machine** → replay it. Then open the **RELIANCE**
   pre-news case and replay: *"unexplained activity occurred before the first
   related headline stored in this research dataset — a sequence worth
   investigating, not a claim of misconduct."*
5. **2:30** — Show stale/conflicting data lowering confidence on the data-quality
   panel.
6. **2:50** — Generate a **Change Story Card**, then switch to **Live Markets**
   and pull up a real quote for any symbol. Close with *"cause every market move
   has a rhythm."*

## Scalability strategy

The prototype stays simple, but the architecture is built to grow — see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#scalability):

- Analyse every (stock, timestamp) **once**; store/cache features and
  precomputed replay scores at seed time.
- **Global** Investigation Cases shared across users; **user-specific** case
  status, feedback and snapshots only. Personalisation is just ranking +
  thresholds + snapshots.
- MongoDB **compound indexes**; pagination on observations and cases; batch
  inserts.
- Never recompute full stock history on a request.
- Future: background workers for ingestion, scheduled recompute, Redis cache,
  MongoDB time-series collections, multiple backend instances, and extending
  Live Markets' Twelve Data client with a shared cache (e.g. Redis) if traffic
  outgrows the current per-process TTL cache.

## Deployment (Render + Vercel)

**Backend → Render.** `render.yaml` at the repo root defines a Python web
service (`rootDir: backend`, `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
health check at `/api/health`). Set these env vars on the Render service
(`sync: false` ones are secrets you paste in, not committed):

| Variable | Value |
| --- | --- |
| `DB_BACKEND` | `mongo` |
| `MONGODB_URI` | your Atlas connection string |
| `MONGODB_DB_NAME` | `cadence` |
| `BACKEND_CORS_ORIGINS` | `https://<your-app>.vercel.app` |
| `TWELVE_DATA_API_KEY` | your Twelve Data key |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` |
| `JWT_ALGORITHM` | `HS256` |
| `APP_ENV` | `prod` |

**Frontend → Vercel.** Framework preset **Vite**, root directory `frontend`,
build command `npm run build`, output directory `dist`. `frontend/vercel.json`
rewrites all paths to `index.html` so React Router's client-side routes don't
404 on a hard refresh. Set one build-time env var:

| Variable | Value |
| --- | --- |
| `VITE_API_BASE_URL` | `https://<your-render-service>.onrender.com/api` |

**After the first deploy:** copy the live Vercel URL into `BACKEND_CORS_ORIGINS`
on Render and **restart** the Render service (config is cached per-process, so
an env var edit alone doesn't take effect). Confirm MongoDB Atlas → Network
Access allows Render's egress.

## Educational disclaimer

**CADENCE is an educational market-analysis prototype. Detective Mode uses
synthetic, historical-style data — not live market data — and produces **no**
investment advice. Live Markets shows real quotes via Twelve Data, but nothing
in either mode is a recommendation to buy, sell or hold any security.**
