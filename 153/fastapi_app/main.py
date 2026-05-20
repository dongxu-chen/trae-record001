from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from .core.config import settings
from .core.database import engine, Base
from .api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    from sqlalchemy.ext.asyncio import AsyncSession
    from .models.models import Counselor
    
    async with AsyncSession(engine) as db:
        from sqlalchemy import select
        result = await db.execute(select(Counselor))
        existing = result.scalars().first()
        
        if not existing:
            default_counselors = [
                Counselor(name='张医生', title='心理咨询师', specialty='青少年心理、情绪管理', available_times='周一、周三 9:00-17:00'),
                Counselor(name='李医生', title='高级心理咨询师', specialty='人际关系、学业压力', available_times='周二、周四 10:00-18:00'),
                Counselor(name='王医生', title='心理治疗师', specialty='焦虑抑郁、职业规划', available_times='周五、周六 9:00-16:00'),
                Counselor(name='赵医生', title='心理咨询师', specialty='家庭关系、自我成长', available_times='周一至周五 14:00-20:00')
            ]
            db.add_all(default_counselors)
            await db.commit()
    
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="校园心理健康预约系统 - FastAPI异步版本",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="", tags=["API"])


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "2.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        "fastapi_app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        workers=1,
        ws="websockets"
    )
