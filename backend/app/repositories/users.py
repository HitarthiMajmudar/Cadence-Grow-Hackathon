from __future__ import annotations

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

    async def get_or_create(self, name: str, email: str, *, is_seeded: bool = False) -> tuple[dict, bool]:
        norm = normalize_email(email)
        existing = await self.find_one({"email_normalized": norm})
        if existing:
            await self.update(
                {"_id": existing["_id"]},
                {"last_login_at": utcnow(), "name": name or existing["name"]},
            )
            existing["last_login_at"] = utcnow()
            if name:
                existing["name"] = name
            return existing, False

        doc = {
            "_id": new_id(),
            "name": name,
            "email": email.strip(),
            "email_normalized": norm,
            "created_at": utcnow(),
            "last_login_at": utcnow(),
            "preferences": dict(DEFAULT_PREFERENCES),
            "is_seeded": is_seeded,
        }
        await self.insert(doc)
        return doc, True

    async def by_email(self, email: str) -> dict | None:
        return await self.find_one({"email_normalized": normalize_email(email)})

    async def update_preferences(self, user_id: str, changes: dict) -> dict:
        user = await self.get(user_id)
        if not user:
            raise KeyError(user_id)
        prefs = {**DEFAULT_PREFERENCES, **(user.get("preferences") or {})}
        prefs.update({k: v for k, v in changes.items() if v is not None})
        await self.update({"_id": user_id}, {"preferences": prefs, "last_login_at": utcnow()})
        user["preferences"] = prefs
        return user

    async def list_seeded(self) -> list[dict]:
        return await self.find({"is_seeded": True}, sort=[("created_at", 1)])
