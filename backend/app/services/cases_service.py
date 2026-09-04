"""Reads global Investigation Cases, merges per-user status, ranks by the
user's attention threshold + daily attention budget."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from app.repositories.cases import CaseFeedbackRepository, CaseRepository, UserCaseStateRepository
from app.schemas.watchlist import ATTENTION_BUDGETS
from app.services.analysis_engine import get_engine

EXPLAINED_VERDICTS = {
    "Market-wide movement", "Sector-driven movement", "News-supported movement",
    "Headline noise", "Normal movement",
}


def _cap_per_symbol(cases: list[dict], limit: int) -> list[dict]:
    seen: dict[str, int] = {}
    out: list[dict] = []
    for c in cases:
        n = seen.get(c["symbol"], 0)
        if n < limit:
            out.append(c)
            seen[c["symbol"]] = n + 1
    return out
INVESTIGATING_VERDICTS = {
    "Conflicting evidence", "Insufficient data", "Volatility-regime change",
}


class CasesService:
    def __init__(self) -> None:
        self.cases = CaseRepository()
        self.states = UserCaseStateRepository()
        self.feedback = CaseFeedbackRepository()
        self.engine = get_engine()

    # ------------------------------------------------------------------ #
    async def _merge_state(self, case: dict, states: dict[str, dict], seen_ids: set[str]) -> dict:
        st = states.get(case["case_id"], {})
        return {
            **case,
            "id": case.get("_id", case["case_id"]),
            "status": st.get("status", "new"),
            "viewed_at": st.get("viewed_at"),
            "is_seen": case["case_id"] in seen_ids,
        }

    def _bucket(self, case: dict) -> str:
        v = case["verdict"]
        if v in INVESTIGATING_VERDICTS:
            return "still_investigating"
        if v in EXPLAINED_VERDICTS:
            return "explained"
        return "needs_attention"

    def _apply_budget(self, cases: list[dict], budget: str, threshold: int) -> list[dict]:
        ranked = sorted(cases, key=lambda c: (not c["is_seen"], c["attention_score"],
                                              c["confidence"]), reverse=True)
        if budget == "score_gt_70":
            return [c for c in ranked if c["attention_score"] > 70]
        if budget == "score_gt_55":
            return [c for c in ranked if c["attention_score"] > 55]
        if budget == "unexplained_only":
            return [c for c in ranked if c["verdict"] not in EXPLAINED_VERDICTS
                    and c["attention_score"] >= threshold]
        if budget == "hide_sector_driven":
            return [c for c in ranked if c["verdict"] not in
                    {"Sector-driven movement", "Market-wide movement", "Normal movement"}]
        if budget == "top_3":
            return ranked[:3]
        if budget == "top_5":
            return ranked[:5]
        return ranked  # "all"

    # ------------------------------------------------------------------ #
    async def ranked_for_watchlist(self, user_id: str, *, symbols: list[str] | None,
                                   dataset_ts: pd.Timestamp, threshold: int, budget: str,
                                   seen_ids: set[str] | None = None,
                                   page: int = 1, page_size: int = 100) -> dict:
        seen_ids = seen_ids or set()
        raw = await self.cases.list_up_to(dataset_ts.to_pydatetime(), symbols=symbols)
        state_map = await self.states.states_for_user(user_id, [c["case_id"] for c in raw])
        merged = [await self._merge_state(c, state_map, seen_ids) for c in raw]
        merged = [c for c in merged if c["status"] != "dismissed"]

        needs, investigating, explained = [], [], []
        for c in merged:
            bucket = self._bucket(c)
            if bucket == "needs_attention" and c["attention_score"] >= threshold:
                needs.append(c)
            elif bucket == "needs_attention":
                investigating.append(c)
            elif bucket == "still_investigating":
                investigating.append(c)
            else:
                explained.append(c)

        # unseen, higher-scoring cases first in every bucket
        def rank(c: dict) -> tuple:
            return (not c["is_seen"], c["attention_score"], c["confidence"])

        needs.sort(key=rank, reverse=True)
        needs = self._apply_budget(needs, budget, threshold)
        investigating = _cap_per_symbol(sorted(investigating, key=rank, reverse=True), 2)
        explained = _cap_per_symbol(sorted(explained, key=rank, reverse=True), 2)

        start = (page - 1) * page_size
        return {
            "needs_attention": needs,
            "still_investigating": investigating[start:start + page_size],
            "explained": explained[start:start + page_size],
            "total": len(merged),
            "threshold": threshold,
            "budget": budget,
            "budget_label": ATTENTION_BUDGETS.get(budget, budget),
            "page": page,
            "page_size": page_size,
        }

    async def get_detail(self, user_id: str, case_id: str) -> dict | None:
        case = await self.cases.get_by_case_id(case_id)
        if not case:
            return None
        await self.states.mark_viewed_if_new(user_id, case_id)
        state_map = await self.states.states_for_user(user_id, [case_id])
        merged = await self._merge_state(case, state_map, set())
        merged["feedback_summary"] = await self.feedback.summary(case_id)
        return merged

    async def set_status(self, user_id: str, case_id: str, status: str) -> dict | None:
        case = await self.cases.get_by_case_id(case_id)
        if not case:
            return None
        return await self.states.set_status(user_id, case_id, status)

    async def add_feedback(self, user_id: str, case_id: str, feedback: str, note: str | None) -> dict:
        return await self.feedback.add(user_id, case_id, feedback, note)

    async def story_card(self, case_id: str) -> dict | None:
        case = await self.cases.get_by_case_id(case_id)
        if not case:
            return None
        main_evidence = [e["detail"] for e in case.get("supporting_evidence", [])[:3]]
        if not main_evidence:
            main_evidence = case.get("breakdown", {}).get("top_reasons", [])[:3]
        return {
            "case_id": case["case_id"],
            "symbol": case["symbol"],
            "company_name": case["company_name"],
            "event_date": case["detection_timestamp"],
            "attention_score": case["attention_score"],
            "confidence": case["confidence"],
            "severity": case["severity"],
            "verdict": case["verdict"],
            "one_line": case["headline_explanation"],
            "main_evidence": main_evidence,
            "sparkline": case.get("spark", []),
            "dataset_label": self.engine.meta.get("label", "Offline Research Dataset"),
            "generated_at": datetime.utcnow(),
            "disclaimer": "Educational market analysis. Not investment advice.",
        }

    async def recently_viewed(self, user_id: str, limit: int = 6) -> list[dict]:
        states = await self.states.recently_viewed(user_id, limit)
        out = []
        for st in states:
            case = await self.cases.get_by_case_id(st["case_id"])
            if case:
                out.append({**case, "id": case.get("_id", case["case_id"]),
                            "status": st["status"], "viewed_at": st.get("viewed_at"),
                            "is_seen": True})
        return out
