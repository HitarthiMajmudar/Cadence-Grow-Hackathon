"""
Feature engineering.

Every rolling statistic is TRAILING only: baselines use ``.shift(1)`` so the
current bar is never part of its own reference window, and no feature reads a
value dated after the bar it describes. These features are what the Attention
Score consumes, so they must be computable in real time.

(Retrospective sequence facts — e.g. "the first related headline is dated after
this move" — are established later, at case-generation time, and never feed the
score. See docs/MODEL_CARD.md.)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.scoring_config import feature_params

MARKET_SYMBOL_DEFAULT = "NIFTYMD"


def _mad(x: np.ndarray) -> float:
    """Median absolute deviation — robust to the very outliers we hunt for."""
    x = x[~np.isnan(x)]
    if x.size == 0:
        return np.nan
    return float(np.median(np.abs(x - np.median(x))))


def _rolling_robust(series: pd.Series, window: int, min_periods: int) -> tuple[pd.Series, pd.Series]:
    """Trailing (shifted) rolling median and robust-sigma (1.4826 * MAD)."""
    roll = series.shift(1).rolling(window, min_periods=min_periods)
    median = roll.median()
    mad = roll.apply(_mad, raw=True)
    robust_sigma = 1.4826 * mad
    return median, robust_sigma


class FeatureEngine:
    def __init__(
        self,
        observations: pd.DataFrame,
        stocks_meta: list[dict],
        sectors: dict,
        news: list[dict] | pd.DataFrame,
        market_symbol: str = MARKET_SYMBOL_DEFAULT,
    ) -> None:
        self.params = feature_params()
        self.market_symbol = market_symbol
        self.sector_of = {s["symbol"]: s["sector"] for s in stocks_meta}
        self.name_of = {s["symbol"]: s["name"] for s in stocks_meta}
        self.members_of: dict[str, list[str]] = {}
        for s in stocks_meta:
            self.members_of.setdefault(s["sector"], []).append(s["symbol"])

        obs = observations.copy()
        obs["timestamp"] = pd.to_datetime(obs["timestamp"])
        obs = obs.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
        self.obs = obs

        self.symbols = [s["symbol"] for s in stocks_meta]

        news_df = pd.DataFrame(news) if not isinstance(news, pd.DataFrame) else news.copy()
        if not news_df.empty:
            news_df["timestamp"] = pd.to_datetime(news_df["timestamp"])
        self.news = news_df

        # market return series indexed by timestamp
        mkt = obs[obs["symbol"] == market_symbol].set_index("timestamp").sort_index()
        self.market_close = mkt["close"]
        self.market_ret = mkt["close"].pct_change()

        # per-symbol close/return frames aligned on the union of timestamps
        wide_close = (
            obs[obs["symbol"] != market_symbol]
            .pivot_table(index="timestamp", columns="symbol", values="close")
            .sort_index()
        )
        self.wide_close = wide_close
        self.wide_ret = wide_close.pct_change(fill_method=None)

    # ------------------------------------------------------------------ #

    def _sector_return_ex_self(self, symbol: str) -> pd.Series:
        sector = self.sector_of[symbol]
        peers = [s for s in self.members_of[sector] if s != symbol and s in self.wide_ret.columns]
        if not peers:
            return pd.Series(0.0, index=self.wide_ret.index)
        return self.wide_ret[peers].mean(axis=1)

    def _news_features(self, symbol: str, index: pd.DatetimeIndex) -> pd.DataFrame:
        w = self.params["news_window_bars"]
        cols = ["news_count", "news_count_prev", "news_count_change",
                "news_sentiment", "news_sentiment_prev", "news_sentiment_shift",
                "news_relevance"]
        out = pd.DataFrame(0.0, index=index, columns=cols)
        if self.news.empty:
            return out
        rel = self.news[self.news["symbols"].apply(lambda xs: symbol in (xs or []))]
        if rel.empty:
            return out
        rel = rel.sort_values("timestamp")
        ts_list = list(index)
        for i, ts in enumerate(ts_list):
            lo_cur = ts_list[max(0, i - w)]
            lo_prev = ts_list[max(0, i - 2 * w)]
            cur = rel[(rel["timestamp"] > lo_cur) & (rel["timestamp"] <= ts)]
            prev = rel[(rel["timestamp"] > lo_prev) & (rel["timestamp"] <= lo_cur)]
            c_cur, c_prev = len(cur), len(prev)
            s_cur = float(cur["sentiment_score"].mean()) if c_cur else 0.0
            s_prev = float(prev["sentiment_score"].mean()) if c_prev else 0.0
            out.iloc[i] = [
                c_cur, c_prev, c_cur - c_prev,
                s_cur, s_prev, s_cur - s_prev,
                min(1.0, c_cur / 2.0),
            ]
        return out

    # ------------------------------------------------------------------ #

    def compute_for_symbol(self, symbol: str) -> pd.DataFrame:
        p = self.params
        g = self.obs[self.obs["symbol"] == symbol].copy()
        g = g.set_index("timestamp").sort_index()
        if g.empty:
            return pd.DataFrame()

        close = g["close"].astype(float)
        volume = g["volume"].astype(float)
        valid_close = close.ffill()

        ret = valid_close.pct_change()
        g["ret"] = ret
        g["return_pct"] = ret * 100.0

        rw = p["return_baseline_window"]
        mp = max(6, rw // 2)
        base_mean = ret.shift(1).rolling(rw, min_periods=mp).mean()
        base_std_classic = ret.shift(1).rolling(rw, min_periods=mp).std()
        base_median, base_std = _rolling_robust(ret, rw, mp)
        # fall back to classic sigma where MAD collapses (e.g. flat / stale runs)
        base_std = base_std.where(base_std > 1e-9, base_std_classic).replace(0, np.nan)
        g["return_baseline_mean"] = base_mean
        g["return_baseline_std"] = base_std
        # clip at ±10 so a single huge concentrated move doesn't produce an
        # absurd headline z-score; the signal is already "off the charts" by 6.
        g["return_zscore"] = ((ret - base_median) / base_std).clip(-10, 10)

        vw = p["volume_baseline_window"]
        vmp = max(6, vw // 2)
        vol_median, vol_sigma = _rolling_robust(volume, vw, vmp)
        vol_ma = volume.shift(1).rolling(vw, min_periods=vmp).mean()
        vol_sigma = vol_sigma.where(vol_sigma > 1e-9,
                                    volume.shift(1).rolling(vw, min_periods=vmp).std())
        g["volume_ma"] = vol_ma
        g["volume_ratio"] = volume / vol_median.replace(0, np.nan)
        g["volume_zscore"] = (volume - vol_median) / vol_sigma.replace(0, np.nan)

        fast = ret.rolling(p["volatility_fast_window"], min_periods=4).std()
        slow = ret.rolling(p["volatility_slow_window"], min_periods=10).std()
        g["volatility_fast"] = fast
        g["volatility_slow"] = slow
        g["volatility_ratio"] = fast / slow.replace(0, np.nan)

        # how "choppy" the recent window is: count of trailing bars whose robust
        # z-score exceeds 1.5 (range expansion without a single dominant move)
        g["vol_regime_strength"] = (g["return_zscore"].abs() > 1.5).rolling(
            p["volatility_fast_window"], min_periods=3).sum()

        maw = p["moving_average_window"]
        ma = valid_close.rolling(maw, min_periods=maw // 2).mean()
        g["moving_average"] = ma
        g["dist_from_ma"] = valid_close / ma - 1.0

        bw = p["breakout_window"]
        roll_max = g["high"].astype(float).shift(1).rolling(bw, min_periods=bw // 2).max()
        roll_min = g["low"].astype(float).shift(1).rolling(bw, min_periods=bw // 2).min()
        atr = (g["high"].astype(float) - g["low"].astype(float)).shift(1).rolling(
            bw, min_periods=bw // 2).mean()
        g["breakout_strength"] = (valid_close - roll_max) / atr.replace(0, np.nan)
        g["breakdown_strength"] = (roll_min - valid_close) / atr.replace(0, np.nan)

        ddw = p["drawdown_window"]
        g["drawdown"] = valid_close / valid_close.rolling(ddw, min_periods=ddw // 2).max() - 1.0

        # ---- market / sector -------------------------------------------- #
        mkt_ret = self.market_ret.reindex(g.index)
        g["market_return"] = mkt_ret
        bwd = p["beta_window"]
        cov = ret.rolling(bwd, min_periods=bwd // 2).cov(mkt_ret).shift(1)
        var = mkt_ret.rolling(bwd, min_periods=bwd // 2).var().shift(1)
        beta_m = (cov / var.replace(0, np.nan)).clip(-3, 3).fillna(1.0)
        g["beta_market"] = beta_m
        g["market_adjusted_return"] = ret - beta_m * mkt_ret

        sec_ret = self._sector_return_ex_self(symbol).reindex(g.index)
        g["sector_return"] = sec_ret
        g["sector_adjusted_return"] = ret - sec_ret

        # cumulative moves over the trailing comparison window. Multi-bar events
        # dilute single-bar z-scores, so the score also looks at these.
        cw = self.params.get("news_window_bars", 7)
        sqrt_cw = cw ** 0.5
        g["ret_cum_short"] = ret.rolling(cw, min_periods=2).sum()
        g["market_ret_cum_short"] = mkt_ret.rolling(cw, min_periods=2).sum()
        g["sector_ret_cum_short"] = sec_ret.rolling(cw, min_periods=2).sum()
        g["ret_cum_zscore"] = g["ret_cum_short"] / (base_std.replace(0, np.nan) * sqrt_cw)
        g["sector_adj_cum"] = g["ret_cum_short"] - g["sector_ret_cum_short"]
        g["market_adj_cum"] = g["ret_cum_short"] - beta_m * g["market_ret_cum_short"]
        g["ret_cum_20"] = ret.rolling(20, min_periods=5).sum()

        # ---- news ------------------------------------------------------- #
        nf = self._news_features(symbol, g.index)
        for c in nf.columns:
            g[c] = nf[c].values

        # ---- data quality --------------------------------------------- #
        g["freshness_status"] = g["freshness_status"].fillna("fresh")
        g["is_missing"] = close.isna() | g["freshness_status"].eq("missing")
        valid_count = (~close.isna()).astype(int).cumsum()
        g["history_bars"] = valid_count
        g["short_history"] = valid_count < p["warmup_bars"]

        g["symbol"] = symbol
        g["sector"] = self.sector_of[symbol]
        g["company_name"] = self.name_of[symbol]
        g = g.reset_index().rename(columns={"index": "timestamp"})

        drop_first = p["warmup_bars"]
        return g.iloc[drop_first:].reset_index(drop=True)

    def compute(self) -> pd.DataFrame:
        frames = [self.compute_for_symbol(s) for s in self.symbols if s != self.market_symbol]
        frames = [f for f in frames if not f.empty]
        out = pd.concat(frames, ignore_index=True)
        num_cols = out.select_dtypes(include=[float, "float64"]).columns
        out[num_cols] = out[num_cols].replace([np.inf, -np.inf], np.nan)
        return out


FEATURE_COLUMNS = [
    "return_pct", "return_zscore", "return_baseline_mean", "return_baseline_std",
    "volume_ratio", "volume_zscore", "volatility_fast", "volatility_slow", "volatility_ratio",
    "dist_from_ma", "drawdown", "breakout_strength", "breakdown_strength",
    "market_return", "market_adjusted_return", "beta_market",
    "sector_return", "sector_adjusted_return",
    "ret_cum_short", "market_ret_cum_short", "sector_ret_cum_short",
    "ret_cum_zscore", "sector_adj_cum", "market_adj_cum", "ret_cum_20", "vol_regime_strength",
    "news_count", "news_count_change", "news_sentiment", "news_sentiment_shift", "news_relevance",
    "history_bars",
]
