"""
Evidence Court — four independent "detectives" that each examine one facet of a
move and return a finding, evidence, confidence and a stance
(supports / opposes / inconclusive) toward the hypothesis:

    "this is a noteworthy, stock-specific event that deserves attention"

Their stances are combined by the verdict tree.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


def _n(row, k, d=0.0):
    try:
        v = float(row[k])
        return d if (v is None or math.isnan(v)) else v
    except (KeyError, TypeError, ValueError):
        return d


@dataclass
class Finding:
    detective: str
    key: str
    finding: str
    evidence: list[str]
    confidence: float
    status: str  # supports | opposes | inconclusive

    def as_dict(self) -> dict:
        return self.__dict__


@dataclass
class CourtContext:
    related_news: list[dict] = field(default_factory=list)
    first_related_news_after_bars: int | None = None
    first_related_news_after_material: bool = False
    news_before_move: bool = False
    dominant_news_sentiment: float = 0.0
    bars_per_day: int = 7
    trailing_news_window_clear: bool = True


def stock_detective(row) -> Finding:
    ret_z = _n(row, "return_zscore")
    ret_cum_z = _n(row, "ret_cum_zscore")
    ret_cum = _n(row, "ret_cum_short")
    dist_ma = _n(row, "dist_from_ma")
    drawdown = _n(row, "drawdown")
    breakout = _n(row, "breakout_strength")
    breakdown = _n(row, "breakdown_strength")
    eff_z = max(abs(ret_z), abs(ret_cum_z) * 0.85)

    ev = [
        f"Single-bar return z-score {ret_z:+.2f}; episode move {ret_cum * 100:+.2f}% "
        f"(episode z {ret_cum_z:+.2f}).",
        f"Price is {dist_ma * 100:+.2f}% from its 20-bar moving average.",
    ]
    if drawdown <= -0.04:
        ev.append(f"Trading {drawdown * 100:.1f}% below its recent 20-bar high.")
    if breakout >= 0.6:
        ev.append(f"Pushed {breakout:.1f} ATR beyond the prior range high (breakout).")
    if breakdown >= 0.6:
        ev.append(f"Broke {breakdown:.1f} ATR below the prior range low (breakdown).")

    if eff_z >= 2.0:
        status, conf = "supports", min(95.0, 55 + 12 * eff_z)
        finding = f"This {ret_cum * 100:+.2f}% move is unusually large for {row['symbol']}."
    elif eff_z >= 1.2:
        status, conf = "inconclusive", 55.0
        finding = f"The move is somewhat above normal but not decisively unusual (z {eff_z:.2f})."
    else:
        status, conf = "opposes", 65.0
        finding = f"A {ret_cum * 100:+.2f}% move is well within {row['symbol']}'s normal range."
    return Finding("Stock Detective", "stock", finding, ev, round(conf, 1), status)


def volume_detective(row) -> Finding:
    vr = _n(row, "volume_ratio", 1.0)
    vz = _n(row, "volume_zscore")
    ev = [
        f"Volume is {vr:.2f}x the 20-bar rolling average.",
        f"Volume z-score {vz:+.2f}.",
    ]
    if vr >= 1.8:
        status = "supports"
        conf = min(95.0, 50 + 18 * (vr - 1))
        finding = f"Market participation is abnormally high ({vr:.2f}x normal)."
    elif vr >= 1.3:
        status = "inconclusive"
        conf = 55.0
        finding = f"Participation is a little elevated ({vr:.2f}x) but not extreme."
    else:
        status = "opposes"
        conf = 62.0
        finding = f"Participation is unremarkable ({vr:.2f}x normal)."
    return Finding("Volume Detective", "volume", finding, ev, round(conf, 1), status)


def sector_detective(row) -> Finding:
    sector_adj_cum = _n(row, "sector_adj_cum")
    sec_cum = _n(row, "sector_ret_cum_short")
    ret_cum = _n(row, "ret_cum_short")
    ev = [
        f"Sector peers moved {sec_cum * 100:+.2f}% over the comparison window.",
        f"This stock moved {ret_cum * 100:+.2f}% over the same window.",
        f"Stock-specific (sector-adjusted) component: {sector_adj_cum * 100:+.2f}%.",
    ]
    if abs(sec_cum) >= 0.02 and abs(sector_adj_cum) < 0.015:
        status = "opposes"
        conf = 78.0
        finding = "The whole sector moved together — this looks sector-driven, not stock-specific."
    elif abs(sector_adj_cum) >= 0.015:
        status = "supports"
        conf = min(92.0, 55 + 700 * abs(sector_adj_cum))
        finding = f"The stock diverged {sector_adj_cum * 100:+.2f}% from its sector — this is stock-specific."
    else:
        status = "inconclusive"
        conf = 50.0
        finding = "Sector context is mixed; neither clearly explains nor rules out a stock-specific event."
    return Finding("Sector Detective", "sector", finding, ev, round(conf, 1), status)


def news_detective(row, ctx: CourtContext) -> Finding:
    ret_z = _n(row, "return_zscore")
    ret_cum = _n(row, "ret_cum_short")
    ret_cum_z = _n(row, "ret_cum_zscore")
    eff_z = max(abs(ret_z), abs(ret_cum_z) * 0.85)
    price_dir = 1 if ret_cum > 0 else (-1 if ret_cum < 0 else (1 if ret_z > 0 else -1))
    n_related = len(ctx.related_news)
    ev: list[str] = []

    if n_related == 0:
        ev.append("No related local headline in the trailing window.")
        if ctx.first_related_news_after_bars is not None and ctx.first_related_news_after_material:
            hrs = ctx.first_related_news_after_bars
            ev.append(f"First related headline is recorded ~{hrs} market hour(s) AFTER this move.")
            finding = ("Unusual activity occurred before the first related headline in this "
                       "dataset — a sequence worth investigating, not proof of anything.")
            return Finding("News Detective", "news", finding, ev, 66.0, "supports")
        if eff_z >= 2:
            finding = "No local news can explain this move — it is currently unexplained."
            return Finding("News Detective", "news", finding, ev, 58.0, "supports")
        finding = "No relevant local news, and no unusual move to explain."
        return Finding("News Detective", "news", finding, ev, 45.0, "inconclusive")

    sent = ctx.dominant_news_sentiment
    for nz in ctx.related_news[:3]:
        ev.append(f"[{nz.get('event_type', 'news')}] {nz.get('headline', '')} "
                  f"({nz.get('sentiment_label', 'neutral')}).")

    if eff_z < 1.2:
        finding = f"{n_related} related headline(s) present, but the price barely reacted — headline noise."
        return Finding("News Detective", "news", finding, ev, 63.0, "opposes")

    if abs(sent) >= 0.2 and price_dir != 0 and (sent > 0) != (price_dir > 0):
        finding = ("Related news points one way while the price moved the other — the "
                   "news does not explain this move.")
        return Finding("News Detective", "news", finding, ev, 70.0, "supports")

    finding = f"{n_related} related headline(s) plausibly explain a move of this direction and size."
    return Finding("News Detective", "news", finding, ev, 72.0, "opposes")


def run_court(row, ctx: CourtContext) -> list[Finding]:
    return [
        stock_detective(row),
        volume_detective(row),
        sector_detective(row),
        news_detective(row, ctx),
    ]


def court_tally(findings: list[Finding]) -> dict:
    supports = [f for f in findings if f.status == "supports"]
    opposes = [f for f in findings if f.status == "opposes"]
    return {
        "supports": len(supports),
        "opposes": len(opposes),
        "inconclusive": len(findings) - len(supports) - len(opposes),
        "split": len(supports) >= 1 and len(opposes) >= 1,
        "net": len(supports) - len(opposes),
    }
