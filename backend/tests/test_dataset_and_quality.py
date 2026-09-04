"""Offline dataset integrity + data-quality service + test-DB safety guard."""
from __future__ import annotations

import pandas as pd
import pytest

from app.core.config import Settings, assert_test_database
from app.data import loader
from app.data.generator import DatasetGenerator


def test_generator_is_deterministic():
    a = DatasetGenerator(seed=42)
    a.apply_scenarios()
    a.generate_background_news()
    df_a = a.simulate()

    b = DatasetGenerator(seed=42)
    b.apply_scenarios()
    b.generate_background_news()
    df_b = b.simulate()

    pd.testing.assert_frame_equal(
        df_a.sort_values(["symbol", "timestamp"]).reset_index(drop=True),
        df_b.sort_values(["symbol", "timestamp"]).reset_index(drop=True),
    )


def test_dataset_shape_matches_spec():
    meta = loader.load_meta()
    stocks = loader.load_stocks()
    sectors = loader.load_sectors()["sectors"]
    assert 8 <= len(stocks) <= 16
    assert 4 <= len(sectors) <= 6
    for required in ("RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "TATAMOTORS", "ITC", "SBIN"):
        assert any(s["symbol"] == required for s in stocks)
    assert 150 <= meta["trading_days"] <= 260


def test_observations_have_no_lookahead_ordering():
    obs = loader.load_observations()
    for _sym, g in obs.groupby("symbol"):
        ts = g["timestamp"].tolist()
        assert ts == sorted(ts)


def test_present_timestamp_leaves_future_room():
    meta = loader.load_meta()
    present = pd.Timestamp(meta["demo_present_timestamp"])
    last = pd.Timestamp(meta["last_timestamp"])
    assert present < last
    # at least ~15 sessions of future data
    assert (last - present) > pd.Timedelta(days=14)


@pytest.mark.asyncio
async def test_dataset_health_reports_issues(repos, engine):
    from app.repositories.snapshots import DemoClockRepository
    from app.services.data_quality import DataQualityService
    from app.services.seeding import seed_market_data

    await seed_market_data(engine)
    await DemoClockRepository().set("u", pd.Timestamp(engine.meta["last_timestamp"]).to_pydatetime())

    health = await DataQualityService().dataset_health("u")
    assert health["total_observations"] > 0
    assert health["dataset_label"] == "Offline Research Dataset"
    # the injected stale / missing / conflicting scenarios should be visible
    statuses = {e["status"] for e in health["events"]}
    assert {"stale", "missing", "conflicting"} & statuses


def test_test_db_guard_rejects_production_name():
    s = Settings(mongodb_db_name="market_detective", mongodb_test_db_name="market_detective_test")
    with pytest.raises(RuntimeError):
        assert_test_database("market_detective", s)
    with pytest.raises(RuntimeError):
        assert_test_database("random_db", s)
    assert_test_database("market_detective_test", s)  # ok


def test_manifest_not_referenced_by_engine_module():
    """The analysis engine must never import the scenario manifest loader."""
    import inspect

    import app.services.analysis_engine as mod

    src = inspect.getsource(mod)
    assert "load_scenario_manifest" not in src
    assert "scenario_manifest" not in src
