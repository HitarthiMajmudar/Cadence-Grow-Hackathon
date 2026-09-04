# Three-minute judging demo

> Have the backend + frontend running and open on the **Login** page.
> Sign in as **Demo Detective** (or the seeded-account button). The dataset
> "present" is **04 Jul 2025 15:15**; each **Advance Market Time** click jumps
> **18 simulated market hours** (≈ 2½ trading sessions).

---

## 0:00 – 0:30 · The pitch

> "A normal watchlist tells you a stock *moved*. **Market Detective** tells you
> whether the movement was *unusual*, what *evidence* explains it, and whether it
> actually *deserves your attention* — and it remembers what you saw last time so
> it can brief you on what you missed."

Point at the top bar: **Offline Research Dataset**, **Replay / Demo Mode**, and the
**simulated market clock**. "No live APIs, no LLM — everything is a local model
over a reproducible synthetic dataset."

## 0:30 – 1:00 · Since You Left

Click **Advance Market Time** twice.

> "The user was away for **36 simulated market hours**. Eight things changed —
> but the engine says only **four** deserve attention. Everything else is a
> sector move, a market move, or headline noise, and it's labelled as such."

Read the classifications: **TATAMOTORS – Important**, **TCS / INFY – Investigating**
(a sector-wide IT sell-off), the rest **Explained / Normal**.

## 1:00 – 1:45 · The top case

Click **Open the case** on **TATAMOTORS – Unusual price and volume activity**.

Walk through, top to bottom:

- **Attention Score 72**, 95 % confidence, **High** severity.
- **Price chart** with the red anomaly dot at the detection bar.
- **Metrics**: return z-score, volume 9.2×, sector-adjusted move, iso-forest score.
- **Evidence Court** — Stock / Volume / Sector / News detectives, each with a
  finding, evidence and a stance. All four *support* an unusual stock-specific
  event → combined verdict.
- **Score breakdown** — every component, with a tooltip explaining the stat.
- **Supporting evidence** *and* **Counter-evidence** side by side.

## 1:45 – 2:30 · Market Time Machine

Click **Replay** (or **Time Machine**). It auto-plays.

> "This is the same engine, replayed. The price line draws itself, volume updates,
> the Attention Score climbs, and the anomaly marker appears **at the exact bar it
> was detected**. 'Who moved first?' says **stock** — not the sector, not the market."

Then go to **Investigation Room → RELIANCE** (advance once more if needed to reveal
it) → open the **Price activity before recorded news** case → **Replay**.

> "Watch the sequence: the price and volume spike **here** … and the first related
> local headline lands **here**, a full session later. The system says
> *'unexplained activity occurred before the first related headline stored in this
> research dataset'* — it does **not** claim misconduct. It identifies a sequence
> worth investigating."

## 2:30 – 2:50 · Honesty about data

Nav to any stale/conflicting stock (e.g. **ONGC** or **MARUTI**) or the
data-quality context on a case.

> "Two stored sources disagree on the MARUTI close by ~1.8 %. The higher-priority
> research source was used, and **confidence was reduced** — the score wasn't
> inflated, the *confidence* was cut, and the conflict is shown to the user."

## 2:50 – 3:00 · Change Story Card + close

On any case click **Story Card → Download PNG**.

> "A shareable card — company, event date, Attention Score, verdict, the main
> evidence, a sparkline, and the disclaimer. Rendered entirely in the browser.
>
> **Your stocks moved. We investigated why.**"

---

## Backup talking points

| If a judge asks… | Say |
| --- | --- |
| "Is this real data?" | No — synthetic, seed 42, generated locally. The badge says so everywhere. Structure is realistic; identity is not. |
| "How is 'meaningful' defined?" | Not a % threshold — unusual vs. the stock's *own* robust (median/MAD) history, or several independent signals agreeing. |
| "Where's the ML?" | Robust statistical scoring (primary) + Isolation Forest (supporting) + TF-IDF/LogReg news sentiment + a deterministic verdict tree. All local, all explainable. |
| "Does it give advice?" | Never. It's an educational analysis tool; the disclaimer is on every screen and every card. |
| "MongoDB?" | Atlas for *application* state only (users, watchlists, snapshots, case status). The frontend never touches it. Runs fully offline via a file-backed store if Atlas is unavailable. |
| "Future-data leakage?" | Every rolling feature is trailing-only; there's a test (`test_no_future_data_leak_in_features`) that truncates the series and asserts the features match. |
