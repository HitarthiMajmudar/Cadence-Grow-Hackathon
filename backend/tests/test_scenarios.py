"""
Scenario-manifest verification.

The generator writes a PRIVATE manifest of the situations it injected, with the
verdict each one *should* receive. The inference engine never reads that file —
this test loads it only to assert the engine reached the expected conclusion.
"""
from __future__ import annotations

import pandas as pd
import pytest

from app.data import loader


@pytest.fixture(scope="module")
def cases(engine):
    return engine.generate_cases()


def _members(sector: str) -> set[str]:
    return set(loader.sector_members()[sector])


def _nearby(cases, m):
    ws, we = pd.Timestamp(m["window_start"]), pd.Timestamp(m["window_end"])
    lo, hi = ws - pd.Timedelta(days=2), we + pd.Timedelta(days=3)
    in_win = [c for c in cases if lo <= pd.Timestamp(c["detection_timestamp"]) <= hi]
    if m["symbol"]:
        return [c for c in in_win if c["symbol"] == m["symbol"]]
    if m["sector"]:
        return [c for c in in_win if c["symbol"] in _members(m["sector"])]
    return [c for c in in_win if c["verdict"] == "Market-wide movement"]


@pytest.mark.parametrize(
    "manifest_entry",
    [m for m in loader.load_scenario_manifest() if m["expects_case"]],
    ids=lambda m: m["scenario"],
)
def test_injected_scenario_reaches_expected_verdict(cases, manifest_entry):
    m = manifest_entry
    near = _nearby(cases, m)
    assert near, f"expected a case near {m['scenario']} but found none"
    near.sort(key=lambda c: (c["verdict"] == m["expected_verdict"], c["attention_score"]),
              reverse=True)
    best = near[0]
    assert best["verdict"] == m["expected_verdict"], (
        f"{m['scenario']}: expected {m['expected_verdict']!r}, got {best['verdict']!r}"
    )
    if m.get("expected_min_attention") is not None:
        assert best["attention_score"] >= m["expected_min_attention"] - 6


@pytest.mark.parametrize(
    "manifest_entry",
    [m for m in loader.load_scenario_manifest() if not m["expects_case"]],
    ids=lambda m: m["scenario"],
)
def test_negative_control_does_not_spawn_case(cases, manifest_entry):
    m = manifest_entry
    if not m["symbol"]:
        return
    ws, we = pd.Timestamp(m["window_start"]), pd.Timestamp(m["window_end"])
    lo, hi = ws - pd.Timedelta(days=1), we + pd.Timedelta(days=2)
    hits = [
        c for c in cases
        if c["symbol"] == m["symbol"]
        and lo <= pd.Timestamp(c["detection_timestamp"]) <= hi
    ]
    assert not hits, f"{m['scenario']} should not create a case, got {[c['verdict'] for c in hits]}"


def test_stale_and_missing_reduce_confidence(engine):
    """Cases anywhere near a stale/missing window must carry a confidence penalty."""
    manifest = {m["scenario"]: m for m in loader.load_scenario_manifest()}
    for scn in ("future_stale_data_ongc", "future_missing_data_sbin"):
        m = manifest[scn]
        row = engine.row_at(m["symbol"], pd.Timestamp(m["window_end"]))
        assert row is not None
        assert float(row["confidence"]) < 100.0


def test_conflicting_source_event_is_preserved(engine):
    events = [e for e in engine.quality_events if e["status"] == "conflicting"]
    assert events, "expected a conflicting-source data-quality event"
    ev = events[0]
    assert len(ev["sources"]) == 2
    assert ev["confidence_penalty"] > 0
