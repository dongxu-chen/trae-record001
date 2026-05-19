from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="参数化保险定价引擎",
        description="基于Python + Pandas + FastAPI的保险定价后端API",
        version="1.0.0",
        debug=settings.DEBUG
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")

    @app.get("/")
    def root():
        return {
            "message": "欢迎使用参数化保险定价引擎API",
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc"
        }

    return app


app = create_app()
