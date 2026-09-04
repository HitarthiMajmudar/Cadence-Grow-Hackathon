"""
Deterministic verdict decision tree.

Given a feature row, the statistical flags, the Evidence Court tally and a small
amount of retrospective sequence context, pick exactly one verdict. The order of
the checks IS the priority order.
"""
from __future__ import annotations

import math

from app.ml.detectives import CourtContext, Finding, court_tally
from app.ml.scoring_config import signal_thresholds
from app.schemas.common import Verdict


def _n(row, k, d=0.0):
    try:
        v = float(row[k])
        return d if (v is None or math.isnan(v)) else v
    except (KeyError, TypeError, ValueError):
        return d


def decide_verdict(
    row,
    flags: dict,
    findings: list[Finding],
    ctx: CourtContext,
    score: float,
) -> tuple[Verdict, dict]:
    th = signal_thresholds()
    tally = court_tally(findings)

    ret_z = _n(row, "return_zscore")
    ret_cum_z = _n(row, "ret_cum_zscore")
    ret_cum = _n(row, "ret_cum_short")
    ret_cum_20 = _n(row, "ret_cum_20")
    sec_cum = _n(row, "sector_ret_cum_short")
    mkt_cum = _n(row, "market_ret_cum_short")
    vol_regime = _n(row, "volatility_ratio", 1.0)
    vol_regime_strength = _n(row, "vol_regime_strength")
    price_dir = 1 if ret_cum > 0 else (-1 if ret_cum < 0 else (1 if ret_z > 0 else -1))
    news_sent = ctx.dominant_news_sentiment
    meta = {"tally": tally}

    fresh = str(row.get("freshness_status", "fresh"))

    # 1. insufficient data ------------------------------------------------ #
    if bool(row.get("is_missing", False)) or bool(row.get("short_history", False)) or fresh == "missing":
        meta["reason"] = "missing_or_thin_history"
        return Verdict.INSUFFICIENT_DATA, meta
    if fresh == "stale" and abs(ret_z) < 1.2:
        meta["reason"] = "stale_feed"
        return Verdict.INSUFFICIENT_DATA, meta

    cz = th["return_cum_z_threshold"]
    strong_move = abs(ret_z) >= th["return_z_threshold"] or abs(ret_cum_z) >= cz
    mild_move = abs(ret_z) >= 1.6 or abs(ret_cum_z) >= cz - 1.0

    # 2. news contradiction -> conflicting ----------------------------- #
    if (strong_move and ctx.related_news and abs(news_sent) >= th["news_shift_threshold"]
            and price_dir != 0 and (news_sent > 0) != (price_dir > 0)):
        meta["reason"] = "news_price_contradiction"
        return Verdict.CONFLICTING, meta

    market_adj_cum = _n(row, "market_adj_cum")
    sector_adj_cum = _n(row, "sector_adj_cum")

    # 3. market-wide --------------------------------------------------- #
    if (abs(mkt_cum) >= 0.028 and abs(market_adj_cum) <= 0.022
            and abs(market_adj_cum) <= abs(sector_adj_cum) + 0.006
            and (price_dir == 0 or (mkt_cum > 0) == (price_dir > 0))):
        meta["reason"] = "moved_with_market"
        return Verdict.MARKET_WIDE, meta

    # 4. sector-driven ------------------------------------------------- #
    if (abs(sec_cum) >= 0.022 and abs(sector_adj_cum) <= 0.022
            and abs(sec_cum) >= abs(mkt_cum) * 1.05
            and (price_dir == 0 or (sec_cum > 0) == (price_dir > 0))):
        meta["reason"] = "moved_with_sector"
        return Verdict.SECTOR_DRIVEN, meta

    # 5. news-supported --------------------------------------------- #
    if (strong_move and ctx.related_news and ctx.news_before_move
            and abs(news_sent) >= th["news_shift_threshold"]
            and price_dir != 0 and (news_sent > 0) == (price_dir > 0)):
        meta["reason"] = "news_supported"
        return Verdict.NEWS_SUPPORTED, meta

    # 6. pre-news activity ----------------------------------------- #
    if ((strong_move or (mild_move and flags["volume_unusual"]))
            and flags["sector_divergent"]
            and not ctx.news_before_move
            and ctx.first_related_news_after_bars is not None
            and ctx.first_related_news_after_material
            and 0 < ctx.first_related_news_after_bars <= 2 * ctx.bars_per_day):
        meta["reason"] = "activity_precedes_news"
        return Verdict.PRE_NEWS, meta

    # 7. volatility-regime change (many big bars, no net move) ----- #
    choppy = vol_regime_strength >= 5 or (vol_regime >= th["volatility_ratio_threshold"]
                                          and vol_regime_strength >= 3)
    if choppy and abs(ret_cum_20) < 0.04 and abs(ret_cum) < 0.035:
        meta["reason"] = "range_expansion_low_net_move"
        return Verdict.VOLATILITY_REGIME, meta

    # 8. unusual price + volume (stock-specific) ------------------- #
    if (strong_move and flags["volume_unusual"] and flags["sector_divergent"]
            and not flags["moved_with_market"] and not flags["moved_with_sector"]):
        meta["reason"] = "stock_specific_price_volume"
        return Verdict.UNUSUAL_PRICE_VOLUME, meta

    # 9. breakout / breakdown ------------------------------------ #
    if flags["breakout"] and price_dir > 0 and flags["sector_divergent"] and strong_move:
        meta["reason"] = "range_breakout"
        return Verdict.POSSIBLE_BREAKOUT, meta
    if flags["breakdown"] and price_dir < 0 and flags["sector_divergent"] and strong_move:
        meta["reason"] = "range_breakdown"
        return Verdict.POSSIBLE_BREAKDOWN, meta

    # 10. headline noise ----------------------------------------- #
    if (ctx.related_news and not strong_move
            and (flags["volume_unusual"] or len(ctx.related_news) >= 2)):
        meta["reason"] = "news_without_price_response"
        return Verdict.HEADLINE_NOISE, meta

    # 11. conflicting (court split) ---------------------------- #
    if tally["split"] and mild_move and abs(tally["net"]) <= 1:
        meta["reason"] = "evidence_court_split"
        return Verdict.CONFLICTING, meta

    # 12. lone unusual price move (no volume / sector context) - #
    if strong_move and flags["sector_divergent"]:
        meta["reason"] = "isolated_price_move"
        return Verdict.UNUSUAL_PRICE_VOLUME, meta

    meta["reason"] = "nothing_crossed_threshold"
    return Verdict.NORMAL, meta
