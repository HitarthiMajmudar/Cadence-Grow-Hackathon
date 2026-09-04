from __future__ import annotations

from app.core.errors import ConflictError
from app.repositories.base import BaseRepository, new_id, utcnow


def normalize_email(email: str) -> str:
    return email.strip().lower()


DEFAULT_PREFERENCES = {
    "default_watchlist_id": None,
    "attention_threshold": 55,
    "daily_attention_budget": "top_3",
    "reduced_motion": False,
    "theme": "dark",
}


class UserRepository(BaseRepository):
    collection_name = "users"

    async def create(self, name: str, email: str, password_hash: str) -> dict:
        norm = normalize_email(email)
        if await self.find_one({"email_normalized": norm}):
            raise ConflictError("An account with this email already exists.")
        doc = {
            "_id": new_id(),
            "name": name,
            "email": email.strip(),
            "email_normalized": norm,
            "password_hash": password_hash,
            "created_at": utcnow(),
            "last_login_at": utcnow(),
            "preferences": dict(DEFAULT_PREFERENCES),
        }
        await self.insert(doc)
        return doc

    async def by_email(self, email: str) -> dict | None:
        return await self.find_one({"email_normalized": normalize_email(email)})

    async def touch_login(self, user_id: str) -> None:
        await self.update({"_id": user_id}, {"last_login_at": utcnow()})

    async def update_preferences(self, user_id: str, changes: dict) -> dict:
        user = await self.get(user_id)
        if not user:
            raise KeyError(user_id)
        prefs = {**DEFAULT_PREFERENCES, **(user.get("preferences") or {})}
        prefs.update({k: v for k, v in changes.items() if v is not None})
        await self.update({"_id": user_id}, {"preferences": prefs, "last_login_at": utcnow()})
        user["preferences"] = prefs
        return user
