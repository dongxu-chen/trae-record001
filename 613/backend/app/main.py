from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="SkyWalking Alert Rule Optimizer",
    description="SkyWalking告警规则优化工具 - 分析告警历史，识别低效规则，推荐优化配置",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "name": "SkyWalking Alert Rule Optimizer",
        "version": "1.0.0",
        "api_prefix": "/api/v1",
        "docs": "/docs",
        "endpoints": [
            {"method": "GET", "path": "/api/v1/health", "description": "健康检查"},
            {"method": "GET", "path": "/api/v1/alerts", "description": "获取告警数据"},
            {"method": "GET", "path": "/api/v1/rules", "description": "获取告警规则"},
            {"method": "GET", "path": "/api/v1/alerts/clusters", "description": "告警聚类分析"},
            {"method": "GET", "path": "/api/v1/rules/inefficient", "description": "低效规则识别"},
            {"method": "GET", "path": "/api/v1/rules/optimize", "description": "生成优化建议"},
            {"method": "GET", "path": "/api/v1/rules/evaluate", "description": "优化效果评估"},
            {"method": "POST", "path": "/api/v1/rules/compare-configs", "description": "规则配置对比"},
            {"method": "GET", "path": "/api/v1/analysis/report", "description": "完整分析报告"},
            {"method": "GET", "path": "/api/v1/metrics/{metric_name}", "description": "获取指标数据"},
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
