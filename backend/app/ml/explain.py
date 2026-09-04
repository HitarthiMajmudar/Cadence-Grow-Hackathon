"""
Deterministic explanation templates — no LLM.

Every verdict maps to a short headline sentence and a longer paragraph, filled
from the feature row. Wording is deliberately cautious: the tool describes
sequences and statistics, it never alleges misconduct or gives advice.
"""
from __future__ import annotations

import math

from app.ml.detectives import CourtContext, Finding
from app.schemas.common import Verdict


def _n(row, k, d=0.0):
    try:
        v = float(row[k])
        return d if (v is None or math.isnan(v)) else v
    except (KeyError, TypeError, ValueError):
        return d


def _pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def _sigma(z: float) -> str:
    """Readable sigma phrasing — capped so extremes don't read as absurd."""
    a = abs(z)
    if a >= 6:
        return "more than 6 standard deviations"
    return f"{a:.1f} standard deviations"


def build_explanation(
    row,
    verdict: Verdict,
    findings: list[Finding],
    ctx: CourtContext,
    score: float,
    confidence: float,
) -> tuple[str, str]:
    name = row.get("company_name", row["symbol"])
    ret_z = _n(row, "return_zscore")
    ret_cum = _n(row, "ret_cum_short")
    vol_ratio = _n(row, "volume_ratio", 1.0)
    sec_cum = _n(row, "sector_ret_cum_short")
    mkt_cum = _n(row, "market_ret_cum_short")
    sector_adj = _n(row, "sector_adjusted_return")
    vol_regime = _n(row, "volatility_ratio", 1.0)

    stat = (f"{name} moved {_sigma(ret_z)} from its normal range "
            f"on volume {vol_ratio:.1f}x its rolling average")

    v = Verdict(verdict) if not isinstance(verdict, Verdict) else verdict

    if v == Verdict.UNUSUAL_PRICE_VOLUME:
        head = (f"{name} moved {_sigma(ret_z)} beyond its normal range while volume reached "
                f"{vol_ratio:.1f}x its rolling average. Its sector moved only {_pct(sec_cum)}, "
                f"suggesting the movement was stock-specific.")
        body = (f"{stat}. Over the same window the rest of the sector moved {_pct(sec_cum)} and "
                f"the market index {_pct(mkt_cum)}, so roughly {_pct(sector_adj)} of the move is "
                f"specific to {name}. Volume and price agree, which is why this is flagged as "
                f"unusual stock-specific activity rather than a broad move.")
    elif v == Verdict.SECTOR_DRIVEN:
        head = (f"{name} fell in line with its sector: sector peers moved {_pct(sec_cum)} over the "
                f"window while {name} moved {_pct(ret_cum)}. The stock-specific component is only "
                f"{_pct(sector_adj)}.")
        body = (f"The move tracks the sector closely (sector-adjusted return {_pct(sector_adj)}). "
                f"This looks like a sector-wide repricing rather than something specific to {name}. "
                f"Attention is moderate because the direction is shared across peers.")
    elif v == Verdict.MARKET_WIDE:
        head = (f"The whole market moved: the index changed {_pct(mkt_cum)} over the window and "
                f"{name} moved {_pct(ret_cum)} with it (market-adjusted {_pct(_n(row, 'market_adjusted_return'))}).")
        body = (f"Nearly every tracked stock moved the same way over this window. {name}'s move is "
                f"largely explained by the market factor, so the stock-specific surprise is small.")
    elif v == Verdict.NEWS_SUPPORTED:
        head = (f"{name} moved {_pct(ret_cum)} and a related local headline dated at or before the "
                f"move points the same way — the move looks news-explained.")
        body = (f"{stat}. A related headline is on record before the move with matching sentiment, "
                f"so the price reaction is consistent with known information.")
    elif v == Verdict.PRE_NEWS:
        after = ctx.first_related_news_after_bars
        head = (f"{name} showed unusual price and volume activity before the first related headline "
                f"in this dataset (recorded ~{after} market hour(s) later).")
        body = (f"{stat}, with no related local headline in the trailing window. The first related "
                f"headline appears about {after} market hour(s) afterwards. This is a sequence worth "
                f"investigating; it is NOT evidence of misconduct and this tool makes no such claim.")
    elif v == Verdict.HEADLINE_NOISE:
        head = (f"Related headlines appeared but {name}'s price barely reacted "
                f"(z {ret_z:+.1f}), even though volume was {vol_ratio:.1f}x normal.")
        body = ("There is local news in the window, but the price response is muted. The elevated "
                "turnover without a matching price move is why this is flagged as headline noise.")
    elif v == Verdict.VOLATILITY_REGIME:
        head = (f"{name}'s short-horizon volatility jumped to {vol_regime:.1f}x its longer-horizon "
                f"level while the net move stayed small ({_pct(ret_cum)}).")
        body = ("Bar-to-bar swings expanded sharply without a clear directional outcome. This is a "
                "volatility-regime change: the stock has become harder to price, which matters for "
                "risk even though the close is near where it started.")
    elif v == Verdict.POSSIBLE_BREAKOUT:
        head = (f"{name} pushed {_n(row, 'breakout_strength'):.1f} ATR beyond its recent range high "
                f"on {vol_ratio:.1f}x volume.")
        body = (f"{stat}. The close cleared the prior 20-bar range to the upside. Range breaks can "
                f"revert, so this is described as a possible breakout, not a prediction.")
    elif v == Verdict.POSSIBLE_BREAKDOWN:
        head = (f"{name} broke {_n(row, 'breakdown_strength'):.1f} ATR below its recent range low "
                f"on {vol_ratio:.1f}x volume.")
        body = (f"{stat}. The close fell through the prior 20-bar range to the downside. Range breaks "
                f"can revert, so this is described as a possible breakdown, not a prediction.")
    elif v == Verdict.CONFLICTING:
        supports = [f.detective for f in findings if f.status == "supports"]
        opposes = [f.detective for f in findings if f.status == "opposes"]
        head = (f"The evidence is split on {name}: {', '.join(supports) or 'some signals'} support an "
                f"unusual event while {', '.join(opposes) or 'others'} argue against it.")
        body = (f"{stat}. Different detectives disagree — for example the news and price signals point "
                f"in opposite directions. The case is kept open with reduced confidence so a human can "
                f"weigh the conflicting evidence.")
    elif v == Verdict.INSUFFICIENT_DATA:
        head = (f"There is not enough reliable data for {name} in this window to reach a verdict.")
        body = ("Some bars are missing, stale or in conflict, or there is too little history for a "
                "stable baseline. Confidence is held low and no strong conclusion is drawn.")
    else:  # NORMAL
        head = (f"{name} moved {_pct(ret_cum)} over the window — within its normal range "
                f"(z {ret_z:+.1f}) on {vol_ratio:.1f}x volume. Nothing here needs attention.")
        body = ("No component of the Attention Score crossed its onset threshold and the detectives "
                "do not see anything unusual. This is ordinary movement.")

    return head, body


def classification_headline(classification: str, symbol: str, verdict: str | None) -> str:
    if classification == "important":
        return f"{symbol}: {verdict or 'unusual movement'} — flagged for your attention."
    if classification == "investigating":
        return f"{symbol}: {verdict or 'developing situation'} — still gathering evidence."
    if classification == "explained":
        if verdict:
            return f"{symbol}: {verdict} — a likely explanation is on record."
        return f"{symbol}: moved with its sector or the market — no stock-specific case."
    if classification == "insufficient_data":
        return f"{symbol}: not enough reliable data to judge."
    return f"{symbol}: ordinary movement, nothing to do."
