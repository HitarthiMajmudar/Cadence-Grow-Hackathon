# Architecture

## 1. High-level

```
┌────────────────────────┐        HTTPS/JSON        ┌───────────────────────────────┐
│  React + TS (Vite)     │  ────────────────────▶   │  FastAPI (Python)             │
│  Tailwind · Recharts   │      /api/*              │                               │
│  TanStack Query        │  ◀────────────────────   │  ┌─────────────────────────┐  │
│  React Router          │                          │  │ AnalysisEngine (in-mem) │  │
└────────────────────────┘                          │  │  features · scoring ·   │  │
        localStorage:                               │  │  verdict · detectives · │  │
        user_id, active watchlist,                  │  │  explanation · cases    │  │
        remembered tab                              │  └─────────────────────────┘  │
                                                    │  ┌─────────────────────────┐  │
                                                    │  │ Repository layer        │  │
                                                    │  └───────────┬─────────────┘  │
                                                    └──────────────┼───────────────┘
                                                                   │
                                            ┌──────────────────────┴───────────────────────┐
                                            │  DB_BACKEND selects:                          │
                                            │   • MongoDB Atlas (Motor)   ← production      │
                                            │   • file-backed local store ← offline demo    │
                                            └──────────────────────────────────────────────┘

Offline Research Dataset  (data/generated/*.csv/json, committed, seed=42)
  └─ loaded once into the AnalysisEngine at process start
```

The **frontend never connects to MongoDB**. All market intelligence is derived by
the backend from the local dataset; MongoDB stores only *application* state.

## 2. Backend layers

| Layer | Package | Responsibility |
| --- | --- | --- |
| API routes | `app/api/routes/` | HTTP, validation, auth dependency, error mapping |
| Schemas | `app/schemas/` | Pydantic request/response models + enums |
| Services | `app/services/` | orchestration: analysis engine, briefing, demo clock, replay, data quality, seeding, per-user case ranking |
| ML | `app/ml/` | feature engineering, anomaly detection, sentiment, Attention Score, verdict tree, Evidence Court, explanation templates |
| Repositories | `app/repositories/` | one class per collection; the only code that talks to the DB |
| DB | `app/db/` | Mongo (Motor) client + a `MemoryDatabase` implementing the same async API, index specs |
| Data | `app/data/` | deterministic dataset **generator** + **loader** |
| Core | `app/core/` | settings (pydantic-settings), logging, typed errors |

### The AnalysisEngine (`app/services/analysis_engine.py`)

The "brain". Built once per process:

1. Load observations + stocks + sectors + news + quality events.
2. `FeatureEngine.compute()` — trailing-safe features for every (symbol, bar).
3. `add_isolation_forest()` — supporting multivariate anomaly score.
4. `score_row()` per bar → Attention Score, confidence, severity, `_score_obj`.
5. `generate_cases()` — detect score/large-move episodes → one case per episode
   with verdict, Evidence Court, explanation, retrospective news sequence,
   score breakdown, spark + price series; de-duplicate market/sector clusters.

The **running API** uses the engine in-memory for per-timestamp state (fast,
deterministic). The **seed script** uses it to persist features + cases to the DB.

### Persistence abstraction (`app/db/`)

`Database.connect()` picks a backend from `Settings.effective_backend`. Both
backends expose `db[collection]` with `find / find_one / insert_one / insert_many
/ update_one(upsert) / delete_* / count_documents / create_index`. The
`MemoryDatabase`:

- round-trips `datetime` through JSON (tagged `{"__dt__": ...}`) so range queries
  keep working after a reload;
- enforces declared unique indexes (raises `DuplicateKeyError`);
- persists to `backend/.local_store/<db>.json` atomically; `set_autoflush(False)`
  batches bulk seed inserts.

## 3. Request flow example — "Advance Market Time"

```
POST /api/demo-clock/advance
  → get_current_user (X-User-Id header)
  → DemoClockService.advance(user_id, bars=18)
      → DemoClockRepository.ensure / set        (MongoDB or local store)
      → AnalysisEngine.advance_timestamp        (in-memory, dataset timeline)
  → CaseRepository.list_between(from_ts, to_ts, symbols=watchlist∪)
  → 200 { clock, advanced_bars, from/to, new_case_ids }
```

Then the frontend invalidates the `clock`, `watchlist`, `briefing`, `cases`,
`stock` and `dataset-health` query keys, and everything re-renders at the new
simulated time.

## 4. Frontend structure

```
src/
  api/            client (fetch + X-User-Id), typed endpoint map
  hooks/          useAuth, TanStack Query hooks, useActiveWatchlist,
                  useReplayPlayer (requestAnimationFrame state machine)
  components/     AttentionScore gauge, Sparkline, EvidenceCourt, CaseCard,
                  ScoreBreakdown, NewsTimeline, SinceYouLeft, StoryCard(+Modal),
                  charts (Recharts), badges, DatasetClock, WatchlistSelector, ui
  layouts/        AppLayout (sticky command bar, nav, offline/demo badges)
  pages/          Login, Dashboard, StockDetail, CaseDetail, TimeMachine,
                  Watchlists, Stocks, StoryCard
  types/          mirrors the backend schemas
  utils/          formatters + colour/label maps
```

State: **TanStack Query** owns all server state; `localStorage` only holds the
demo `user_id`, the active watchlist id, and small UI conveniences.

## 5. Data model (MongoDB collections)

| Collection | Key fields | Notes |
| --- | --- | --- |
| `users` | `email_normalized` (unique), `preferences` | demo auth |
| `watchlists` | `user_id`, `name`, `symbols[]`, `attention_threshold`, `daily_attention_budget` | |
| `market_observations` | `symbol`, `timestamp`, OHLCV, `source`, `freshness_status` | from the offline dataset |
| `stock_features` | `symbol`, `timestamp`, all engineered features + score | precomputed at seed |
| `news_events` | `timestamp`, `symbols[]`, `headline`, `event_type`, `sentiment_*` | local, offline |
| `visit_snapshots` | `user_id`, `watchlist_id`, `acknowledged_at`, `dataset_timestamp`, `stock_states[]`, `seen_case_ids[]` | the "since you left" anchor |
| `investigation_cases` | `case_id` (unique), `symbol`, `detection_timestamp`, `attention_score`, `verdict`, `evidence`, `score_components`, … | **global**, shared across users |
| `user_case_states` | `(user_id, case_id)` unique, `status`, `viewed_at` | **per-user** |
| `case_feedback` | `user_id`, `case_id`, `feedback` | |
| `data_quality_events` | `symbol`, `timestamp`, `status`, `sources`, `confidence_penalty` | |
| `demo_clock` | `user_id` (unique), `current_dataset_timestamp` | per-user simulated time |

### Indexes (created idempotently in `app/db/client.py`)

- `users.email_normalized` — unique
- `watchlists (user_id, name)` · `(user_id, updated_at desc)`
- `market_observations (symbol, timestamp)` · `(timestamp)`
- `stock_features (symbol, timestamp)` — unique
- `visit_snapshots (user_id, watchlist_id, dataset_timestamp desc)` · `(…, acknowledged_at desc)`
- `investigation_cases (symbol, detection_timestamp)` · `(attention_score desc)` · `case_id` unique · `(detection_timestamp)`
- `user_case_states (user_id, case_id)` — unique
- `case_feedback (user_id, case_id)`
- `data_quality_events (symbol, timestamp)`
- `demo_clock.user_id` — unique

## 6. Scalability

Implemented now:

- **Compute once**: features + Attention Scores + cases are computed a single
  time and reused; the API does light per-request work (ranking, diffing).
- **Global cases, personal ranking**: `investigation_cases` is shared; only
  `user_case_states`, `case_feedback` and `visit_snapshots` are per-user.
- **Pagination** on observation/case queries; **batch inserts** (chunked) at seed.
- **Compound indexes** on every hot query path.
- **Precomputed replay**: replay frames are sliced from the already-scored
  feature frame + cases + news — no recomputation.

The next version would add (behind the unchanged repository interface):

| Concern | Approach |
| --- | --- |
| Ingestion | a background worker (Celery / RQ / arq) writing `market_observations` |
| Recompute | scheduled job recomputing features + cases on new data; incremental, not full history |
| Caching | Redis for hot per-user briefings and case lists |
| Time-series | MongoDB **time-series collections** for `market_observations` |
| Horizontal scale | multiple stateless FastAPI instances; the AnalysisEngine becomes a shared precompute service / cache |
| Real data | a `MarketDataProvider` implementation for an **authorised** paid feed — same interface, no other code changes |

None of this infrastructure is built for the 72-hour prototype, by design.
