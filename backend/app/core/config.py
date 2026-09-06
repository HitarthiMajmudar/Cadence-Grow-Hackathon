"""Application configuration, loaded from environment / .env with validation."""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
DATASET_DIR = REPO_ROOT / "data" / "generated"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -- persistence ------------------------------------------------------- #
    db_backend: Literal["auto", "mongo", "memory"] = "auto"
    mongodb_uri: str | None = None
    mongodb_db_name: str = "cadence"
    mongodb_test_uri: str | None = None
    mongodb_test_db_name: str = "cadence_test"
    local_store_dir: str = ".local_store"

    # -- api ------------------------------------------------------------- #
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    app_env: Literal["dev", "test", "prod"] = "dev"

    # -- demo dataset / clock ------------------------------------------- #
    demo_clock_advance_bars: int = 18

    # -- auth -------------------------------------------------------------- #
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 60 * 24 * 14  # 14 days, no refresh-token flow

    # -- live market data (Twelve Data) ------------------------------------ #
    twelve_data_api_key: str | None = None
    twelve_data_base_url: str = "https://api.twelvedata.com"

    # -- test-safety guard ------------------------------------------------ #
    market_detective_allow_unsafe_test_db: bool = False

    @field_validator("backend_cors_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @property
    def local_store_path(self) -> Path:
        p = Path(self.local_store_dir)
        if not p.is_absolute():
            p = BACKEND_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def effective_backend(self) -> Literal["mongo", "memory"]:
        if self.db_backend == "mongo":
            return "mongo"
        if self.db_backend == "memory":
            return "memory"
        # auto
        return "mongo" if self.mongodb_uri else "memory"

    def safe_uri_display(self) -> str:
        """Connection target with credentials stripped — safe to log."""
        uri = self.mongodb_uri or ""
        if "@" in uri:
            scheme, rest = uri.split("://", 1) if "://" in uri else ("", uri)
            host = rest.split("@", 1)[1]
            return f"{scheme}://***:***@{host.split('/')[0]}"
        return "local file-backed store" if self.effective_backend == "memory" else uri


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_startup(settings: Settings | None = None) -> list[str]:
    """Return a list of human-readable warnings; raise on fatal misconfig."""
    settings = settings or get_settings()
    warnings: list[str] = []

    if settings.effective_backend == "mongo" and not settings.mongodb_uri:
        raise RuntimeError(
            "DB_BACKEND=mongo but MONGODB_URI is not set. "
            "Set MONGODB_URI or use DB_BACKEND=memory / auto."
        )

    if not settings.jwt_secret_key or not settings.jwt_secret_key.strip():
        raise RuntimeError(
            "JWT_SECRET_KEY is not set. Set a strong random "
            "secret (e.g. `openssl rand -hex 32`) before starting the API."
        )

    if not settings.twelve_data_api_key:
        warnings.append(
            "TWELVE_DATA_API_KEY is not set. Live Markets will respond with "
            "503 market_data_not_configured until it is provided; Detective "
            "Mode is unaffected."
        )

    if settings.effective_backend == "memory":
        warnings.append(
            "Using the file-backed local store (no MongoDB). Data persists on this "
            "machine only. Set MONGODB_URI for MongoDB Atlas persistence."
        )

    if not DATASET_DIR.exists() or not (DATASET_DIR / "dataset_meta.json").exists():
        warnings.append(
            "Offline dataset not found at data/generated/. Run: "
            "python -m app.data.generator"
        )

    return warnings


def assert_test_database(db_name: str, settings: Settings | None = None) -> None:
    """Refuse to run destructive test setup against a non-test database."""
    settings = settings or get_settings()
    if settings.market_detective_allow_unsafe_test_db:
        return
    if db_name == settings.mongodb_db_name:
        raise RuntimeError(
            f"Refusing to run tests against the production database '{db_name}'."
        )
    if not db_name.endswith("_test"):
        raise RuntimeError(
            f"Test database name '{db_name}' must end with '_test' "
            f"(or set MARKET_DETECTIVE_ALLOW_UNSAFE_TEST_DB=1)."
        )


if __name__ == "__main__":
    s = get_settings()
    print("effective backend:", s.effective_backend)
    print("target:", s.safe_uri_display())
    for w in validate_startup(s):
        print("warning:", w, file=sys.stderr)
