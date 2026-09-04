from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.quality import DatasetHealth, SymbolQuality
from app.services.data_quality import DataQualityService

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


@router.get("/health", response_model=DatasetHealth)
async def dataset_health(user: CurrentUser) -> dict:
    return await DataQualityService().dataset_health(user["_id"])


@router.get("/{symbol}", response_model=SymbolQuality)
async def symbol_quality(symbol: str, user: CurrentUser) -> dict:
    svc = DataQualityService()
    ts = await svc.clock.current_timestamp(user["_id"])
    return await svc.symbol_quality(symbol, ts)
