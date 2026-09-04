"""
Offline Research Dataset generator for CADENCE's Detective Mode.

This module deterministically synthesises a plausible Indian-equities dataset
(prices, volumes, a market index, timestamped local headlines and data-quality
incidents) plus a PRIVATE scenario manifest used only by the automated tests.

Nothing here calls a network service. Everything is driven by a single fixed
random seed so the dataset is fully reproducible.

Run standalone:
    python -m app.data.generator            # writes data/generated/*
    python -m app.data.generator --force    # overwrite existing files
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

GENERATOR_VERSION = "1.0.0"
SEED = 42

START_DATE = date(2025, 1, 6)          # a Monday
TRADING_DAYS = 160
BAR_TIMES = ["09:15", "10:15", "11:15", "12:15", "13:15", "14:15", "15:15"]
BARS_PER_DAY = len(BAR_TIMES)
MARKET_HOURS_PER_BAR = 1.0             # each bar == one simulated market hour

# The simulated "present" the demo starts at. Bars after this are the future the
# user advances into with the "Advance Market Time" button.
DEMO_PRESENT_DAY = 130                 # 1-indexed trading day

MARKET_INDEX = {"symbol": "NIFTYMD", "name": "Nifty Market-Detective 50"}
CURRENCY = "INR"

# symbol, name, sector, index weight (pre-normalisation), base price
STOCKS: list[tuple[str, str, str, float, float]] = [
    ("RELIANCE",   "Reliance Industries Ltd",        "ENERGY",  0.13,  2850.0),
    ("ONGC",       "Oil & Natural Gas Corp Ltd",     "ENERGY",  0.03,   265.0),
    ("NTPC",       "NTPC Ltd",                       "ENERGY",  0.03,   360.0),
    ("TCS",        "Tata Consultancy Services Ltd",  "IT",      0.10,  3900.0),
    ("INFY",       "Infosys Ltd",                    "IT",      0.08,  1650.0),
    ("WIPRO",      "Wipro Ltd",                      "IT",      0.03,   545.0),
    ("HDFCBANK",   "HDFC Bank Ltd",                  "BANKING", 0.12,  1550.0),
    ("ICICIBANK",  "ICICI Bank Ltd",                 "BANKING", 0.09,  1150.0),
    ("SBIN",       "State Bank of India",            "BANKING", 0.06,   820.0),
    ("TATAMOTORS", "Tata Motors Ltd",                "AUTO",    0.05,   970.0),
    ("MARUTI",     "Maruti Suzuki India Ltd",        "AUTO",    0.05, 12800.0),
    ("M&M",        "Mahindra & Mahindra Ltd",        "AUTO",    0.04,  2900.0),
    ("ITC",        "ITC Ltd",                        "FMCG",    0.07,   470.0),
    ("HINDUNILVR", "Hindustan Unilever Ltd",         "FMCG",    0.05,  2450.0),
    ("NESTLEIND",  "Nestle India Ltd",               "FMCG",    0.03,  2500.0),
]

SECTOR_NAMES = {
    "ENERGY": "Energy",
    "IT": "Information Technology",
    "BANKING": "Banking & Financials",
    "AUTO": "Automobile",
    "FMCG": "Fast-Moving Consumer Goods",
}

# U-shaped intraday volume profile (open & close heavier).
INTRADAY_VOLUME_SHAPE = np.array([1.65, 1.05, 0.80, 0.70, 0.80, 1.10, 1.55])

# Company blurbs for the UI.
COMPANY_SUMMARY = {
    "RELIANCE": "Diversified conglomerate spanning oil-to-chemicals, telecom (Jio) and retail.",
    "TCS": "India's largest IT-services exporter, part of the Tata group.",
    "INFY": "Global technology-services and consulting major headquartered in Bengaluru.",
    "HDFCBANK": "India's largest private-sector bank by assets and market value.",
    "ICICIBANK": "Large private-sector bank with a broad retail and corporate franchise.",
    "SBIN": "India's largest public-sector bank, majority owned by the Government of India.",
    "TATAMOTORS": "Automobile manufacturer; owns Jaguar Land Rover and a growing EV portfolio.",
    "MARUTI": "India's largest passenger-vehicle maker, majority owned by Suzuki.",
    "M&M": "Automobile and farm-equipment maker; the 'Mahindra' SUV and tractor brand.",
    "ITC": "Diversified FMCG, hotels, paperboards and agri-business group.",
    "HINDUNILVR": "India's largest listed FMCG company, a Unilever subsidiary.",
    "NESTLEIND": "Packaged-foods and beverages maker; the Maggi and Nescafé brand owner.",
    "ONGC": "State-owned crude-oil and natural-gas explorer and producer.",
    "NTPC": "India's largest power-generation utility, majority government owned.",
    "WIPRO": "IT-services and consulting company headquartered in Bengaluru.",
}


# --------------------------------------------------------------------------- #
# Scenario definitions
# --------------------------------------------------------------------------- #

@dataclass
class Scenario:
    """One deliberately injected market situation.

    ``expected_verdict`` and the ``expected_*`` bounds live in the PRIVATE
    manifest only. The inference engine never receives this object.
    """

    name: str
    kind: str
    day: int                       # 1-indexed trading day the event centres on
    window_bars: int
    expected_verdict: str
    reason: str
    symbol: str | None = None
    sector: str | None = None
    params: dict = field(default_factory=dict)
    expected_min_attention: float | None = None
    expected_max_attention: float | None = None
    expects_case: bool = True


SCENARIOS: list[Scenario] = [
    # ---- history (visible the moment the demo opens) ----------------------- #
    Scenario(
        name="past_market_crash", kind="market_crash", day=40, window_bars=4,
        expected_verdict="Market-wide movement",
        reason="Broad de-risking event: every constituent and the index fall together.",
        params={"total_pct": -0.058},
        expected_min_attention=40,
    ),
    Scenario(
        name="past_stock_spike_tcs", kind="stock_price_volume_spike", day=58, window_bars=5,
        symbol="TCS", expected_verdict="Unusual price and volume activity",
        reason="Large order-win rumour: TCS jumps on 3x volume while IT peers are flat.",
        params={"direction": 1, "magnitude_pct": 0.075, "volume_mult": 2.9},
        expected_min_attention=60,
    ),
    Scenario(
        name="past_sector_decline_banking", kind="sector_decline", day=88, window_bars=9,
        sector="BANKING", expected_verdict="Sector-driven movement",
        reason="Regulator tightens provisioning norms: the whole banking pack sells off together.",
        params={"total_pct": -0.072},
        expected_min_attention=45,
    ),
    Scenario(
        name="past_conflicting_tatamotors", kind="positive_news_negative_price", day=100,
        window_bars=5, symbol="TATAMOTORS",
        expected_verdict="Conflicting evidence",
        reason="Delivery beat headline, but the stock falls on soft guidance — signals disagree.",
        params={"price_pct": -0.052},
        expected_min_attention=32,
    ),
    Scenario(
        name="past_pre_news_icicibank", kind="pre_news_activity", day=112, window_bars=3,
        symbol="ICICIBANK", expected_verdict="Price activity before recorded news",
        reason="Unusual buying a full session before the block-deal headline is recorded.",
        params={"price_pct": 0.052, "volume_mult": 2.8, "news_delay_bars": 8},
        expected_min_attention=55,
    ),

    # ---- future (revealed by "Advance Market Time" / "Replay What I Missed") - #
    # Spaced ~2 trading days apart from the demo present (day 130) so each
    # "Advance Market Time" click (18 bars ≈ 2.5 sessions) reveals a fresh story.
    Scenario(
        name="future_stock_spike_tatamotors", kind="stock_price_volume_spike", day=132,
        window_bars=5, symbol="TATAMOTORS",
        expected_verdict="Unusual price and volume activity",
        reason="Stock-specific breakout on 3.3x volume; AUTO peers and the index barely move.",
        params={"direction": 1, "magnitude_pct": 0.092, "volume_mult": 3.3},
        expected_min_attention=70,
    ),
    Scenario(
        name="future_sector_decline_it", kind="sector_decline", day=135, window_bars=8,
        sector="IT", expected_verdict="Sector-driven movement",
        reason="A large client's IT-budget cut drags TCS, INFY and WIPRO down in lockstep.",
        params={"total_pct": -0.07},
        expected_min_attention=45,
    ),
    Scenario(
        name="future_pre_news_reliance", kind="pre_news_activity", day=137, window_bars=4,
        symbol="RELIANCE", expected_verdict="Price activity before recorded news",
        reason="Sharp, high-volume mark-up a full session before the demerger headline lands.",
        params={"price_pct": 0.075, "volume_mult": 3.2, "news_delay_bars": 9},
        expected_min_attention=52,
    ),
    Scenario(
        name="future_market_crash", kind="market_crash", day=140, window_bars=4,
        expected_verdict="Market-wide movement",
        reason="Global risk-off session: the index and every stock gap down together.",
        params={"total_pct": -0.064},
        expected_min_attention=40,
    ),
    Scenario(
        name="future_conflicting_infy", kind="positive_news_negative_price", day=143,
        window_bars=5, symbol="INFY",
        expected_verdict="Conflicting evidence",
        reason="Infosys beats on EPS yet sells off on a weak margin outlook.",
        params={"price_pct": -0.052},
        expected_min_attention=45,
    ),
    Scenario(
        name="future_volume_no_price_itc", kind="volume_spike_flat_price", day=145,
        window_bars=5, symbol="ITC",
        expected_verdict="Headline noise",
        reason="Demerger chatter drives 3x turnover but the price hardly moves.",
        params={"volume_mult": 3.2},
        expected_min_attention=12,
    ),
    Scenario(
        name="future_volatility_regime_hdfcbank", kind="volatility_regime_change", day=147,
        window_bars=16, symbol="HDFCBANK",
        expected_verdict="Volatility-regime change",
        reason="Choppy two-and-a-half-day range expansion with almost no net move.",
        params={"vol_mult": 5.2},
        expected_min_attention=38,
    ),
    Scenario(
        name="future_missing_data_sbin", kind="missing_data", day=150, window_bars=4,
        symbol="SBIN", expected_verdict="Insufficient data",
        reason="Vendor outage: four consecutive SBIN bars are absent.",
        params={},
        expected_max_attention=55,
        expects_case=False,
    ),
    Scenario(
        name="future_stale_data_ongc", kind="stale_data", day=152, window_bars=6,
        symbol="ONGC", expected_verdict="Insufficient data",
        reason="Delayed feed: ONGC prints repeat the last good print for six bars.",
        params={},
        expects_case=False,
    ),
    Scenario(
        name="future_conflicting_source_maruti", kind="conflicting_data", day=154, window_bars=1,
        symbol="MARUTI", expected_verdict="Normal movement",
        reason="Two stored vendors disagree on the MARUTI close by ~1.8%.",
        params={"disagreement_pct": 0.018},
        expects_case=False,
    ),
    Scenario(
        name="future_normal_nestle_like", kind="normal_movement", day=156, window_bars=6,
        symbol="HINDUNILVR", expected_verdict="Normal movement",
        reason="Ordinary low-volatility drift that must NOT be flagged.",
        params={},
        expected_max_attention=38,
        expects_case=False,
    ),
]


# --------------------------------------------------------------------------- #
# News templates
# --------------------------------------------------------------------------- #

POSITIVE_TEMPLATES = [
    ("{name} beats quarterly estimates on strong demand", "earnings"),
    ("{name} raises FY guidance after robust order inflows", "earnings"),
    ("Brokerage upgrades {name} to 'buy', lifts target price", "analyst_action"),
    ("{name} wins large multi-year deal, shares in focus", "operational"),
    ("{name} announces buyback, board clears proposal", "financing"),
    ("{name} launches new flagship product to positive reviews", "product_launch"),
]
NEGATIVE_TEMPLATES = [
    ("{name} misses profit view as margins compress", "earnings"),
    ("{name} cuts outlook citing weak demand environment", "earnings"),
    ("Brokerage downgrades {name}, flags valuation risk", "analyst_action"),
    ("Regulator opens probe into {name} accounting practices", "regulation"),
    ("{name} recalls units after quality complaints", "operational"),
    ("{name} CFO resigns abruptly, succession unclear", "leadership"),
    ("Court rules against {name} in long-running dispute", "legal_issue"),
]
NEUTRAL_TEMPLATES = [
    ("{name} to hold board meeting to consider results", "earnings"),
    ("{name} completes scheduled maintenance shutdown", "operational"),
    ("{name} appoints new independent director", "leadership"),
    ("{name} clarifies media report on expansion plans", "operational"),
    ("{name} announces record date for dividend", "financing"),
    ("{name} in talks to acquire smaller regional player", "acquisition"),
]

SENTIMENT_LABELS = {1: "positive", 0: "neutral", -1: "negative"}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def build_timestamp_index() -> list[datetime]:
    """Return the ordered list of trading-bar datetimes (naive IST)."""
    days: list[date] = []
    d = START_DATE
    while len(days) < TRADING_DAYS:
        if d.weekday() < 5:  # Mon-Fri
            days.append(d)
        d += timedelta(days=1)
    stamps: list[datetime] = []
    for day in days:
        for t in BAR_TIMES:
            hh, mm = map(int, t.split(":"))
            stamps.append(datetime(day.year, day.month, day.day, hh, mm))
    return stamps


def day_bar_slice(day: int) -> slice:
    """Bar-index slice for a 1-indexed trading day."""
    start = (day - 1) * BARS_PER_DAY
    return slice(start, start + BARS_PER_DAY)


def repo_root() -> Path:
    # backend/app/data/generator.py -> repo root
    return Path(__file__).resolve().parents[3]


def output_dir() -> Path:
    d = repo_root() / "data" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------- #
# Core generation
# --------------------------------------------------------------------------- #

class DatasetGenerator:
    def __init__(self, seed: int = SEED) -> None:
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.stamps = build_timestamp_index()
        self.n_bars = len(self.stamps)
        self.symbols = [s[0] for s in STOCKS]
        self.sector_of = {s[0]: s[2] for s in STOCKS}
        self.name_of = {s[0]: s[1] for s in STOCKS}
        self.base_price = {s[0]: s[4] for s in STOCKS}
        raw_w = np.array([s[3] for s in STOCKS], dtype=float)
        self.weight = dict(zip(self.symbols, raw_w / raw_w.sum(), strict=False))
        self.sectors = sorted({s[2] for s in STOCKS})

        # per-stock factor loadings
        self.beta_mkt = {s: float(self.rng.uniform(0.75, 1.25)) for s in self.symbols}
        self.beta_sec = {s: float(self.rng.uniform(0.55, 0.95)) for s in self.symbols}
        self.idio_vol = {s: float(self.rng.uniform(0.0035, 0.0075)) for s in self.symbols}
        self.base_volume = {
            s: float(self.rng.uniform(4e5, 5e6)) * (1.0 + 4 * self.weight[s])
            for s in self.symbols
        }

        # additive per-bar contributions filled in by scenario injection
        self.mkt_extra = np.zeros(self.n_bars)
        self.sector_extra = {sec: np.zeros(self.n_bars) for sec in self.sectors}
        self.stock_extra = {s: np.zeros(self.n_bars) for s in self.symbols}
        self.vol_mult = {s: np.ones(self.n_bars) for s in self.symbols}
        self.idio_vol_mult = {s: np.ones(self.n_bars) for s in self.symbols}
        self.freshness = {s: np.array(["fresh"] * self.n_bars, dtype=object) for s in self.symbols}
        self.source = {s: np.array(["research_primary"] * self.n_bars, dtype=object) for s in self.symbols}
        self.force_missing = {s: np.zeros(self.n_bars, dtype=bool) for s in self.symbols}
        self.force_flat = {s: np.zeros(self.n_bars, dtype=bool) for s in self.symbols}
        self.suppress_factor = {s: np.zeros(self.n_bars, dtype=bool) for s in self.symbols}

        # windows where variance is amplified but net drift is removed
        self.vol_regime_windows: list[tuple[str, np.ndarray]] = []

        self.news: list[dict] = []
        self.quality_events: list[dict] = []
        self._news_id = 0

    # -- scenario injection ------------------------------------------------- #

    def apply_scenarios(self) -> None:
        for sc in SCENARIOS:
            handler = getattr(self, f"_inject_{sc.kind}")
            handler(sc)

    def _bars(self, day: int, window: int) -> np.ndarray:
        start = (day - 1) * BARS_PER_DAY
        return np.arange(start, min(start + window, self.n_bars))

    def _inject_market_crash(self, sc: Scenario) -> None:
        bars = self._bars(sc.day, sc.window_bars)
        # front-load the drop so a clear "first bar" exists, then keep bleeding.
        # Apply the SAME realised shock to every stock (bypassing beta) so the
        # move is genuinely uniform — that is what "market-wide" means here.
        profile = np.linspace(1.4, 0.7, len(bars))
        profile = sc.params["total_pct"] * profile / profile.sum()
        self.mkt_extra[bars] += profile * 0.35
        for sym in self.symbols:
            self.stock_extra[sym][bars] += profile
            for k, b in enumerate(bars):
                self.vol_mult[sym][b] *= 1.0 + 0.7 * (profile[k] / profile.min())
        self._add_news(bars[len(bars) // 2], [], "market",
                       "Global markets slide as risk sentiment sours", "market_wire", -1,
                       symbols_optional=True)

    def _inject_sector_decline(self, sc: Scenario) -> None:
        bars = self._bars(sc.day, sc.window_bars)
        profile = np.linspace(1.3, 0.7, len(bars))
        profile = sc.params["total_pct"] * profile / profile.sum()
        members = [s for s in self.symbols if self.sector_of[s] == sc.sector]
        self.sector_extra[sc.sector][bars] += profile * 0.3
        for sym in members:
            self.stock_extra[sym][bars] += profile
            for k, b in enumerate(bars):
                self.vol_mult[sym][b] *= 1.0 + 0.6 * (profile[k] / profile.min())
        self._add_news(bars[1], members, "regulation",
                       f"{SECTOR_NAMES[sc.sector]} stocks fall on policy tightening worries",
                       "sector_wire", -1)

    def _concentrated_profile(self, n: int) -> np.ndarray:
        """Weight vector that front-loads a move into its first 1-2 bars."""
        if n <= 1:
            return np.array([1.0])
        w = np.zeros(n)
        w[0] = 0.6
        w[1] = 0.28
        if n > 2:
            w[2:] = 0.12 / (n - 2)
        return w

    def _inject_stock_price_volume_spike(self, sc: Scenario) -> None:
        bars = self._bars(sc.day, sc.window_bars)
        direction = sc.params.get("direction", 1)
        profile = self._concentrated_profile(len(bars))
        self.stock_extra[sc.symbol][bars] += direction * sc.params["magnitude_pct"] * profile
        vmult = sc.params["volume_mult"]
        for k, b in enumerate(bars):
            self.vol_mult[sc.symbol][b] *= 1.0 + (vmult - 1.0) * (profile[k] / profile.max())

    def _inject_volume_spike_flat_price(self, sc: Scenario) -> None:
        bars = self._bars(sc.day, sc.window_bars)
        for b in bars:
            self.vol_mult[sc.symbol][b] *= sc.params["volume_mult"]
        self._add_news(bars[1], [sc.symbol], "acquisition",
                       f"{self.name_of[sc.symbol]} demerger buzz lifts turnover", "chatter", 0)

    def _inject_volatility_regime_change(self, sc: Scenario) -> None:
        bars = self._bars(sc.day, sc.window_bars)
        for b in bars:
            self.idio_vol_mult[sc.symbol][b] *= sc.params["vol_mult"]
            self.vol_mult[sc.symbol][b] *= 1.5  # range expansion lifts turnover a little
            self.suppress_factor[sc.symbol][b] = True  # kill beta drift → ~zero net move
        # register the window so simulate() removes the net drift but keeps the variance
        self.vol_regime_windows.append((sc.symbol, bars))
        self._add_news(bars[len(bars) // 2], [sc.symbol], "operational",
                       f"{self.name_of[sc.symbol]} swings in a wide range amid uncertainty",
                       "local_wire", 0)

    def _inject_positive_news_negative_price(self, sc: Scenario) -> None:
        bars = self._bars(sc.day, sc.window_bars)
        profile = self._concentrated_profile(len(bars))
        self.stock_extra[sc.symbol][bars] += sc.params["price_pct"] * profile
        for b in bars:
            self.vol_mult[sc.symbol][b] *= 1.9
        self._add_news(bars[0], [sc.symbol], "earnings",
                       f"{self.name_of[sc.symbol]} beats profit estimates for the quarter",
                       "research_primary", 1)

    def _inject_pre_news_activity(self, sc: Scenario) -> None:
        bars = self._bars(sc.day, sc.window_bars)
        profile = self._concentrated_profile(len(bars))
        self.stock_extra[sc.symbol][bars] += sc.params["price_pct"] * profile
        vmult = sc.params["volume_mult"]
        for k, b in enumerate(bars):
            self.vol_mult[sc.symbol][b] *= 1.0 + (vmult - 1.0) * (profile[k] / profile.max())
        news_bar = int(bars[-1]) + int(sc.params["news_delay_bars"])
        news_bar = min(news_bar, self.n_bars - 1)
        self._add_news(news_bar, [sc.symbol], "acquisition",
                       f"{self.name_of[sc.symbol]} confirms strategic restructuring plan",
                       "research_primary", 1)

    def _inject_missing_data(self, sc: Scenario) -> None:
        bars = self._bars(sc.day, sc.window_bars)
        for b in bars:
            self.force_missing[sc.symbol][b] = True
            self.freshness[sc.symbol][b] = "missing"
            self.source[sc.symbol][b] = "unavailable"
        self.quality_events.append({
            "symbol": sc.symbol,
            "timestamp": self.stamps[int(bars[0])].isoformat(),
            "status": "missing",
            "sources": ["research_primary"],
            "details": f"{len(bars)} consecutive bars unavailable from the primary feed.",
            "confidence_penalty": 40,
        })

    def _inject_stale_data(self, sc: Scenario) -> None:
        bars = self._bars(sc.day, sc.window_bars)
        for b in bars:
            self.force_flat[sc.symbol][b] = True
            self.freshness[sc.symbol][b] = "stale"
            self.source[sc.symbol][b] = "delayed_vendor"
        # calm the ~8 bars after the outage so a coincidental organic move does
        # not get misread as a "catch-up" event
        tail = np.arange(int(bars[-1]) + 1, min(int(bars[-1]) + 9, self.n_bars))
        for b in tail:
            self.idio_vol_mult[sc.symbol][b] *= 0.35
        self.quality_events.append({
            "symbol": sc.symbol,
            "timestamp": self.stamps[int(bars[0])].isoformat(),
            "status": "stale",
            "sources": ["delayed_vendor"],
            "details": f"Feed delayed; {len(bars)} bars repeat the last good print.",
            "confidence_penalty": 25,
        })

    def _inject_conflicting_data(self, sc: Scenario) -> None:
        bars = self._bars(sc.day, sc.window_bars)
        b = int(bars[0])
        self.freshness[sc.symbol][b] = "conflicting"
        disagreement = sc.params["disagreement_pct"]
        # store the event; the actual chosen value is resolved after price sim
        self.quality_events.append({
            "symbol": sc.symbol,
            "timestamp": self.stamps[b].isoformat(),
            "status": "conflicting",
            "sources": [
                {"name": "research_primary", "priority": 1, "relative_delta": 0.0},
                {"name": "exchange_snapshot", "priority": 2, "relative_delta": disagreement},
            ],
            "details": (
                f"research_primary and exchange_snapshot disagree on the close by "
                f"{disagreement * 100:.1f}%. The higher-priority research source was used "
                f"and confidence was reduced."
            ),
            "confidence_penalty": 15,
        })

    def _inject_normal_movement(self, sc: Scenario) -> None:
        # deliberately do nothing — this is a negative control
        return

    # -- news ------------------------------------------------------------- #

    def _add_news(self, bar: int, symbols: list[str], event_type: str, headline: str,
                  source: str, sentiment: int, symbols_optional: bool = False) -> None:
        bar = int(np.clip(bar, 0, self.n_bars - 1))
        self._news_id += 1
        self.news.append({
            "id": f"NEWS{self._news_id:04d}",
            "timestamp": self.stamps[bar].isoformat(),
            "symbols": list(symbols),
            "headline": headline,
            "body": headline + ".",
            "source": source,
            "event_type": event_type,
            "sentiment_score": float(sentiment),
            "sentiment_label": SENTIMENT_LABELS[sentiment],
            "scope": "market" if (not symbols and symbols_optional) else
                     ("sector" if not symbols else "company"),
        })

    def generate_background_news(self) -> None:
        """One or two neutral/regular headlines per trading day."""
        for day in range(1, TRADING_DAYS + 1):
            k = int(self.rng.integers(1, 3))
            base_bar = (day - 1) * BARS_PER_DAY
            for _ in range(k):
                sym = str(self.rng.choice(self.symbols))
                bar = base_bar + int(self.rng.integers(0, BARS_PER_DAY))
                roll = self.rng.random()
                if roll < 0.2:
                    tmpl, et = POSITIVE_TEMPLATES[self.rng.integers(len(POSITIVE_TEMPLATES))]
                    sent = 1
                elif roll < 0.35:
                    tmpl, et = NEGATIVE_TEMPLATES[self.rng.integers(len(NEGATIVE_TEMPLATES))]
                    sent = -1
                else:
                    tmpl, et = NEUTRAL_TEMPLATES[self.rng.integers(len(NEUTRAL_TEMPLATES))]
                    sent = 0
                self._add_news(bar, [sym], et, tmpl.format(name=self.name_of[sym]),
                               "local_wire", sent)
        self.news.sort(key=lambda n: n["timestamp"])

    # -- price / volume simulation -------------------------------------- #

    def simulate(self) -> pd.DataFrame:
        n = self.n_bars
        # market factor path
        mkt_ret = self.rng.normal(0.00018, 0.0034, n) + self.mkt_extra
        sector_ret: dict[str, np.ndarray] = {}
        for sec in self.sectors:
            sector_ret[sec] = (
                0.6 * mkt_ret
                + self.rng.normal(0.0, 0.0028, n)
                + self.sector_extra[sec]
            )

        rows: list[dict] = []
        stock_returns: dict[str, np.ndarray] = {}
        stock_close: dict[str, np.ndarray] = {}

        for sym in self.symbols:
            sec = self.sector_of[sym]
            idio = self.rng.normal(0.0, 1.0, n) * self.idio_vol[sym] * self.idio_vol_mult[sym]
            # volatility-regime windows: keep the amplified variance, only remove
            # the window mean so there is (almost) no net directional move.
            for rsym, rbars in self.vol_regime_windows:
                if rsym == sym and len(rbars):
                    seg = idio[rbars].copy()
                    idio[rbars] = seg - seg.mean()
            factor_scale = np.where(self.suppress_factor[sym], 0.15, 1.0)
            ret = (
                0.00005
                + factor_scale * self.beta_mkt[sym] * mkt_ret
                + factor_scale * self.beta_sec[sym] * sector_ret[sec]
                + idio
                + self.stock_extra[sym]
            )
            close = np.empty(n)
            prev = self.base_price[sym]
            last_good = prev
            for i in range(n):
                if self.force_missing[sym][i]:
                    close[i] = np.nan
                    continue
                if self.force_flat[sym][i]:
                    close[i] = last_good
                    ret[i] = 0.0
                    continue
                px = prev * (1.0 + ret[i])
                px = max(px, 1.0)
                close[i] = px
                prev = px
                last_good = px
            # carry price across missing gaps for continuity of later bars
            filled = pd.Series(close).ffill().bfill().to_numpy()
            for i in range(n):
                if not (self.force_missing[sym][i] or self.force_flat[sym][i]):
                    prev_val = filled[i - 1] if i > 0 else self.base_price[sym]
                    ret[i] = filled[i] / prev_val - 1.0
            stock_returns[sym] = ret
            stock_close[sym] = filled

            # OHLCV
            bar_of_day = np.tile(np.arange(BARS_PER_DAY), TRADING_DAYS)[:n]
            for i in range(n):
                c = filled[i]
                o = (filled[i - 1] if i > 0 else self.base_price[sym])
                o = o * (1.0 + self.rng.normal(0.0, 0.0009))
                hi = max(o, c) * (1.0 + abs(self.rng.normal(0.0, 0.0016)))
                lo = min(o, c) * (1.0 - abs(self.rng.normal(0.0, 0.0016)))
                if self.force_missing[sym][i]:
                    o = hi = lo = c = np.nan
                    vol = 0
                else:
                    shape = INTRADAY_VOLUME_SHAPE[bar_of_day[i]]
                    noise = float(np.exp(self.rng.normal(0.0, 0.32)))
                    vol = self.base_volume[sym] * shape * noise * self.vol_mult[sym][i]
                    if self.force_flat[sym][i]:
                        vol *= 0.15
                    vol = int(max(vol, 0))
                rows.append({
                    "symbol": sym,
                    "timestamp": self.stamps[i].isoformat(),
                    "open": _round(o), "high": _round(hi), "low": _round(lo),
                    "close": _round(c), "volume": vol,
                    "source": self.source[sym][i],
                    "freshness_status": self.freshness[sym][i],
                })

        # market index = weighted average of constituent closes, rebased to 1000
        idx_close = np.zeros(n)
        for sym in self.symbols:
            idx_close += self.weight[sym] * (stock_close[sym] / self.base_price[sym])
        idx_close = 1000.0 * idx_close
        for i in range(n):
            c = idx_close[i]
            o = idx_close[i - 1] if i > 0 else idx_close[0]
            hi = max(o, c) * (1.0 + abs(self.rng.normal(0.0, 0.0007)))
            lo = min(o, c) * (1.0 - abs(self.rng.normal(0.0, 0.0007)))
            rows.append({
                "symbol": MARKET_INDEX["symbol"],
                "timestamp": self.stamps[i].isoformat(),
                "open": _round(o), "high": _round(hi), "low": _round(lo),
                "close": _round(c), "volume": 0,
                "source": "research_primary", "freshness_status": "fresh",
            })

        df = pd.DataFrame(rows).sort_values(["symbol", "timestamp"]).reset_index(drop=True)
        return df

    # -- manifest --------------------------------------------------------- #

    def manifest(self) -> list[dict]:
        out = []
        for sc in SCENARIOS:
            bars = self._bars(sc.day, sc.window_bars)
            out.append({
                "scenario": sc.name,
                "kind": sc.kind,
                "symbol": sc.symbol,
                "sector": sc.sector,
                "day": sc.day,
                "timestamp": self.stamps[int(bars[0])].isoformat(),
                "window_start": self.stamps[int(bars[0])].isoformat(),
                "window_end": self.stamps[int(bars[-1])].isoformat(),
                "window_bars": int(sc.window_bars),
                "expected_verdict": sc.expected_verdict,
                "expected_min_attention": sc.expected_min_attention,
                "expected_max_attention": sc.expected_max_attention,
                "expects_case": sc.expects_case,
                "reason": sc.reason,
            })
        return out

    # -- assemble & write --------------------------------------------- #

    def run(self, force: bool = False) -> dict:
        out = output_dir()
        self.apply_scenarios()
        self.generate_background_news()
        obs = self.simulate()

        present_ts = self.stamps[DEMO_PRESENT_DAY * BARS_PER_DAY - 1].isoformat()

        stocks_json = [
            {
                "symbol": s, "name": self.name_of[s], "sector": self.sector_of[s],
                "sector_name": SECTOR_NAMES[self.sector_of[s]],
                "index": MARKET_INDEX["symbol"], "weight": round(self.weight[s], 5),
                "base_price": self.base_price[s], "currency": CURRENCY,
                "summary": COMPANY_SUMMARY[s],
            }
            for s in self.symbols
        ]
        sectors_json = {
            "market_index": MARKET_INDEX,
            "sectors": [
                {
                    "id": sec, "name": SECTOR_NAMES[sec],
                    "symbols": [s for s in self.symbols if self.sector_of[s] == sec],
                }
                for sec in self.sectors
            ],
        }
        meta = {
            "seed": self.seed,
            "generator_version": GENERATOR_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "start_date": START_DATE.isoformat(),
            "trading_days": TRADING_DAYS,
            "bars_per_day": BARS_PER_DAY,
            "bar_times": BAR_TIMES,
            "timezone": "Asia/Kolkata (IST, stored naive)",
            "market_hours_per_bar": MARKET_HOURS_PER_BAR,
            "n_bars": self.n_bars,
            "first_timestamp": self.stamps[0].isoformat(),
            "last_timestamp": self.stamps[-1].isoformat(),
            "demo_present_day": DEMO_PRESENT_DAY,
            "demo_present_timestamp": present_ts,
            "symbols": self.symbols,
            "sectors": self.sectors,
            "market_index": MARKET_INDEX["symbol"],
            "currency": CURRENCY,
            "label": "Offline Research Dataset",
            "disclaimer": (
                "Synthetic, deterministically generated data for an educational "
                "market-analysis prototype. NOT live market data and NOT investment advice."
            ),
        }

        # training data for the local sentiment model
        training_rows = self._sentiment_training_rows()

        _write_json(out / "stocks.json", stocks_json, force)
        _write_json(out / "sectors.json", sectors_json, force)
        _write_json(out / "dataset_meta.json", meta, force)
        _write_json(out / "news_headlines.json", self.news, force)
        _write_json(out / "data_quality_events.json", self.quality_events, force)
        _write_json(out / "scenario_manifest.json", self.manifest(), force)
        obs.to_csv(out / "market_observations.csv", index=False)
        pd.DataFrame(training_rows).to_csv(out / "news_training.csv", index=False)

        return {
            "observations": len(obs),
            "news": len(self.news),
            "quality_events": len(self.quality_events),
            "scenarios": len(SCENARIOS),
            "output_dir": str(out),
        }

    def _sentiment_training_rows(self) -> list[dict]:
        rows: list[dict] = []
        for n in self.news:
            rows.append({"text": n["headline"], "label": n["sentiment_label"]})
        # balance / reinforce with explicit templated examples
        names = list(self.name_of.values())
        for _ in range(120):
            nm = str(self.rng.choice(names))
            for pool, lbl in ((POSITIVE_TEMPLATES, "positive"),
                              (NEGATIVE_TEMPLATES, "negative"),
                              (NEUTRAL_TEMPLATES, "neutral")):
                tmpl, _et = pool[self.rng.integers(len(pool))]
                rows.append({"text": tmpl.format(name=nm), "label": lbl})
        self.rng.shuffle(rows)
        return rows


def _round(x: float) -> float | None:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return round(float(x), 2)


def _write_json(path: Path, data, force: bool) -> None:
    if path.exists() and not force:
        # deterministic generation — overwrite is safe and expected
        pass
    path.write_text(json.dumps(data, indent=2, default=str))


def generate(force: bool = True) -> dict:
    return DatasetGenerator().run(force=force)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate the CADENCE Detective Mode offline dataset")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args()
    summary = generate(force=True)
    print(json.dumps(summary, indent=2))
