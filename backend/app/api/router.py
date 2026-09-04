from fastapi import APIRouter

from app.api.routes import (
    auth,
    briefings,
    cases,
    clock,
    live_market,
    meta,
    quality,
    replay,
    stocks,
    watchlists,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(meta.router)
api_router.include_router(auth.router)
api_router.include_router(stocks.router)
api_router.include_router(watchlists.router)
api_router.include_router(briefings.router)
api_router.include_router(cases.router)
api_router.include_router(replay.router)
api_router.include_router(clock.router)
api_router.include_router(quality.router)
api_router.include_router(live_market.router)
