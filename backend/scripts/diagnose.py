"""Ad-hoc diagnostics for tuning the detection engine against the scenario manifest."""
from __future__ import annotations

import warnings
from collections import Counter

import pandas as pd

warnings.filterwarnings("ignore")

from app.data import loader  # noqa: E402
from app.services.analysis_engine import get_engine  # noqa: E402


def scenario_symbol(m: dict) -> str | None:
    if m["symbol"]:
        return m["symbol"]
    if m["sector"]:
        return loader.sector_members()[m["sector"]][0]
    return None  # market-wide


def main() -> None:
    e = get_engine()
    cases = e.generate_cases()
    present = pd.Timestamp(e.meta["demo_present_timestamp"])

    print(f"total cases: {len(cases)}")
    print("by verdict:", dict(Counter(c["verdict"] for c in cases)))
    print("by severity:", dict(Counter(c["severity"] for c in cases)))
    sc = pd.Series([c["attention_score"] for c in cases])
    print("scores:", sc.describe().round(1).to_dict())
    past = sum(1 for c in cases if pd.Timestamp(c["detection_timestamp"]) <= present)
    print(f"past/future split: {past}/{len(cases) - past}")
    print()

    man = loader.load_scenario_manifest()
    members = loader.sector_members()
    ok = tot = 0
    for m in man:
        if not m["expects_case"]:
            continue
        tot += 1
        ws, we = pd.Timestamp(m["window_start"]), pd.Timestamp(m["window_end"])
        lo, hi = ws - pd.Timedelta(days=2), we + pd.Timedelta(days=3)
        in_win = [c for c in cases if lo <= pd.Timestamp(c["detection_timestamp"]) <= hi]
        if m["symbol"]:
            near = [c for c in in_win if c["symbol"] == m["symbol"]]
        elif m["sector"]:
            syms = set(members[m["sector"]])
            near = [c for c in in_win if c["symbol"] in syms]
        else:  # market-wide
            near = [c for c in in_win if c["verdict"] == "Market-wide movement"]
        # prefer a verdict match, else highest score
        near.sort(key=lambda c: (c["verdict"] == m["expected_verdict"], c["attention_score"]), reverse=True)
        got = near[0]["verdict"] if near else "NO CASE"
        s = f"{near[0]['attention_score']:.0f}/{near[0]['confidence']:.0f} n={len(near)}" if near else "-"
        match = bool(near) and got == m["expected_verdict"]
        ok += match
        flag = "OK " if match else "XX "
        print(f"{flag}{m['scenario']:34s} exp={m['expected_verdict']:35s} got={got:35s} {s}")

    print(f"\n=== verdicts matched: {ok}/{tot} ===\n")

    for m in man:
        if m["expects_case"]:
            continue
        sym = scenario_symbol(m)
        ws, we = pd.Timestamp(m["window_start"]), pd.Timestamp(m["window_end"])
        near = [c for c in cases if sym and c["symbol"] == sym
                and ws - pd.Timedelta(days=1) <= pd.Timestamp(c["detection_timestamp"]) <= we + pd.Timedelta(days=2)]
        flag = "XX " if near else "OK "
        extra = f" (score {near[0]['attention_score']:.0f}, {near[0]['verdict']})" if near else ""
        print(f"{flag}{m['scenario']:34s} expects NO case → got {len(near)}{extra}")

    print("\n--- top 15 cases by score ---")
    for c in sorted(cases, key=lambda x: -x["attention_score"])[:15]:
        print(f"{c['symbol']:11s} {str(c['detection_timestamp'])[:16]} "
              f"{c['attention_score']:5.1f}/{c['confidence']:3.0f} {c['severity']:9s} {c['verdict']}")


if __name__ == "__main__":
    main()
