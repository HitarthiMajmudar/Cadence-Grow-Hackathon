"""
Local headline sentiment + event-type classification.

Sentiment: a TF-IDF + Logistic Regression pipeline trained at process start from
the bundled, deterministically generated ``news_training.csv``. No model download,
no network, fixed ``random_state``.

Event type: transparent keyword rules (documented in docs/MODEL_CARD.md).
"""
from __future__ import annotations

import logging
from functools import lru_cache

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.core.config import DATASET_DIR

logger = logging.getLogger("market_detective.ml")

TRAINING_CSV = DATASET_DIR / "news_training.csv"

EVENT_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("earnings", ("earnings", "profit", "revenue", "results", "quarter", "eps", "guidance", "estimates", "margin")),
    ("acquisition", ("acqui", "merger", "stake buy", "takeover", "demerger", "buys", "acquire")),
    ("regulation", ("regulat", "sebi", "rbi", "probe", "penalty", "compliance", "norms", "policy", "tax")),
    ("leadership", ("ceo", "cfo", "chairman", "resign", "appoint", "director", "management", "succession")),
    ("product_launch", ("launch", "unveil", "new product", "flagship", "rollout", "model")),
    ("legal_issue", ("court", "lawsuit", "litigation", "verdict", "dispute", "fraud", "arbitration")),
    ("analyst_action", ("upgrade", "downgrade", "target price", "brokerage", "rating", "buy", "sell", "neutral")),
    ("financing", ("buyback", "dividend", "bond", "fundrais", "qip", "rights issue", "debt", "stake sale")),
    ("operational", ("plant", "production", "output", "capacity", "shutdown", "recall", "supply", "deal", "order", "contract")),
    ("market", ("markets", "sensex", "nifty", "global", "sell-off", "rally", "risk")),
]

POSITIVE_HINTS = ("beats", "raises", "upgrade", "wins", "buyback", "strong", "record", "positive", "surge", "gains")
NEGATIVE_HINTS = ("miss", "cuts", "downgrade", "probe", "recall", "resign", "against", "weak", "slump", "fraud", "penalty")


@lru_cache
def _pipeline() -> Pipeline | None:
    if not TRAINING_CSV.exists():
        logger.warning("sentiment training data missing at %s — using rules only", TRAINING_CSV)
        return None
    df = pd.read_csv(TRAINING_CSV).dropna()
    if len(df) < 30 or df["label"].nunique() < 2:
        return None
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_features=5000)),
        ("clf", LogisticRegression(max_iter=1000, C=4.0, class_weight="balanced", random_state=42)),
    ])
    pipe.fit(df["text"].astype(str), df["label"].astype(str))
    logger.info("sentiment model trained on %d headlines", len(df))
    return pipe


def _rule_sentiment(text: str) -> tuple[str, float]:
    t = text.lower()
    pos = sum(h in t for h in POSITIVE_HINTS)
    neg = sum(h in t for h in NEGATIVE_HINTS)
    if pos > neg:
        return "positive", min(1.0, 0.4 + 0.2 * pos)
    if neg > pos:
        return "negative", -min(1.0, 0.4 + 0.2 * neg)
    return "neutral", 0.0


def analyze_sentiment(text: str) -> dict:
    """Return {label, score in [-1, 1], method}."""
    pipe = _pipeline()
    if pipe is None:
        label, score = _rule_sentiment(text)
        return {"label": label, "score": round(score, 3), "method": "rules"}
    proba = pipe.predict_proba([text])[0]
    classes = list(pipe.named_steps["clf"].classes_)
    p = dict(zip(classes, proba, strict=False))
    score = p.get("positive", 0.0) - p.get("negative", 0.0)
    label = max(p, key=p.get)
    # blend a light rule nudge so obvious words are never mislabelled
    _r_label, r_score = _rule_sentiment(text)
    score = 0.75 * score + 0.25 * r_score
    if abs(score) < 0.12:
        label = "neutral"
    elif score > 0:
        label = "positive"
    else:
        label = "negative"
    return {"label": label, "score": round(float(score), 3), "method": "tfidf_logreg"}


def classify_event_type(text: str) -> str:
    t = text.lower()
    for event_type, keywords in EVENT_RULES:
        if any(k in t for k in keywords):
            return event_type
    return "other"


def model_is_trained() -> bool:
    return _pipeline() is not None
