import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .database import engine, history_engine, Base, HistoryBase
from .api import products_router, coupon_router, alert_router
from .api.attributes import router as attributes_router
from .api.coupons_v2 import router as coupons_v2_router
from .api.monitor import router as monitor_router
from .api.procurement import router as procurement_router
from .websocket.server import app as sio_app, start_scheduler, stop_scheduler

load_dotenv()

Base.metadata.create_all(bind=engine)
HistoryBase.metadata.create_all(bind=history_engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="商品比价导购平台 API",
    description="聚合多电商平台商品信息，智能比价，推荐最优购买渠道",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/ws", sio_app)

API_PREFIX = "/api"
app.include_router(products_router, prefix=API_PREFIX)
app.include_router(coupon_router, prefix=API_PREFIX)
app.include_router(alert_router, prefix=API_PREFIX)
app.include_router(attributes_router, prefix=API_PREFIX)
app.include_router(coupons_v2_router, prefix=API_PREFIX)
app.include_router(monitor_router, prefix=API_PREFIX)
app.include_router(procurement_router, prefix=API_PREFIX)


@app.get("/")
async def root():
    return {
        "name": "商品比价导购平台 API",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket": "/ws/alerts"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": os.times()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
