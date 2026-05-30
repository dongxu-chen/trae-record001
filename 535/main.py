from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from api.routes import (
    router,
    set_gallery_manager,
    set_trajectory_tracker,
    set_multi_modal_extractor,
    set_sliding_window_engine,
)
from config import (
    gallery_config,
    reid_config,
    faiss_config,
    st_ranker_config,
    trajectory_config,
    multi_modal_config,
    sliding_window_config,
    server_config,
)
from reid_service.feature_extractor import ReidFeatureExtractor
from reid_service.gallery import GalleryManager
from reid_service.multi_modal import MultiModalFeatureExtractor
from reid_service.search_engine import FaissSearchEngine
from reid_service.sliding_window import SlidingWindowEngine
from reid_service.st_ranker import SpatioTemporalRanker
from reid_service.trajectory_tracker import TrajectoryTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

extractor: ReidFeatureExtractor | None = None
multi_modal_extractor: MultiModalFeatureExtractor | None = None
gallery_manager: GalleryManager | None = None
trajectory_tracker: TrajectoryTracker | None = None
sliding_window_engine: SlidingWindowEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global extractor, multi_modal_extractor, gallery_manager
    global trajectory_tracker, sliding_window_engine

    logger.info("Initializing ReID service...")

    extractor = ReidFeatureExtractor(reid_config)
    search_engine = FaissSearchEngine(
        dimension=reid_config.feature_dim,
        config=faiss_config,
    )
    ranker = SpatioTemporalRanker(st_ranker_config)
    gallery_manager = GalleryManager(
        search_engine=search_engine,
        ranker=ranker,
        config=gallery_config,
    )
    gallery_manager._feature_extractor = extractor

    multi_modal_extractor = MultiModalFeatureExtractor(
        visual_extractor=extractor,
        config=multi_modal_config,
        reid_config=reid_config,
    )

    trajectory_tracker = TrajectoryTracker(
        ranker=ranker,
        config=trajectory_config,
    )

    sliding_window_engine = SlidingWindowEngine(
        gallery_manager=gallery_manager,
        config=sliding_window_config,
    )

    try:
        gallery_manager.load()
        logger.info("Loaded existing gallery data")
    except Exception:
        logger.info("No existing gallery data, starting fresh")

    set_gallery_manager(gallery_manager)
    set_trajectory_tracker(trajectory_tracker)
    set_multi_modal_extractor(multi_modal_extractor)
    set_sliding_window_engine(sliding_window_engine)

    logger.info("ReID service initialized successfully")

    yield

    if gallery_manager:
        try:
            gallery_manager.save()
            logger.info("Saved gallery data on shutdown")
        except Exception as e:
            logger.error(f"Failed to save gallery on shutdown: {e}")


app = FastAPI(
    title="Video ReID Service",
    description="Cross-camera target re-identification service with "
    "feature extraction, vector search, spatio-temporal ranking, "
    "multi-modal fusion, trajectory tracking, and real-time sliding window search",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1", tags=["ReID"])


@app.get("/")
async def root():
    return {
        "service": "Video ReID",
        "version": "2.0.0",
        "docs": "/docs",
        "features": [
            "Multi-modal ReID (visual + gait + color)",
            "Cross-camera trajectory tracking",
            "Sliding window real-time search",
            "Domain adaptation",
            "LRU gallery management",
        ],
    }


def main():
    uvicorn.run(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
