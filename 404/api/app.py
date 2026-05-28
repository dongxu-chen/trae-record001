from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import cv2
import numpy as np
import time
import base64
import os

from config import (
    API_HOST, API_PORT, API_TITLE, API_VERSION,
    CONF_THRESHOLD, OUTPUT_DIR
)
from detector import YOLODetector, TRTDetector
from processor import VideoProcessor, FrameHandler, StreamFrame


class DetectionRequest(BaseModel):
    conf_threshold: Optional[float] = CONF_THRESHOLD
    filter_category: Optional[str] = None
    filter_class: Optional[str] = None
    return_annotated: bool = True
    use_enhanced_fpn: bool = True
    small_target_threshold: int = 32
    high_res_scale: float = 2.0


class DetectionResponse(BaseModel):
    success: bool
    detections: List[dict]
    statistics: dict
    processing_time: float
    annotated_image: Optional[str] = None
    small_targets_count: int = 0
    high_res_detections_count: int = 0


class VideoStreamRequest(BaseModel):
    source: int = 0
    conf_threshold: float = CONF_THRESHOLD
    width: int = 640
    height: int = 480
    fps: int = 30
    use_enhanced_fpn: bool = True
    enable_adaptive_resolution: bool = True
    process_every_frame: bool = True


class SystemInfoResponse(BaseModel):
    yolo_available: bool
    tensorrt_available: bool
    device: str
    supported_classes: List[str]
    categories: dict
    features: dict


app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description="Traffic Sign Recognition System - 40-class traffic sign detection and classification"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_detector: Optional[YOLODetector] = None
_detector_fpn: Optional[YOLODetector] = None
_trt_detector: Optional[TRTDetector] = None
_video_processor: Optional[VideoProcessor] = None
_frame_handler: Optional[FrameHandler] = None


def get_detector(use_enhanced_fpn: bool = True) -> YOLODetector:
    global _detector, _detector_fpn, _frame_handler

    if use_enhanced_fpn:
        if _detector_fpn is None:
            _detector_fpn = YOLODetector(use_enhanced_fpn=True)
        detector = _detector_fpn
    else:
        if _detector is None:
            _detector = YOLODetector(use_enhanced_fpn=False)
        detector = _detector

    if _frame_handler is None:
        _frame_handler = FrameHandler(detector)

    return detector


def get_trt_detector():
    global _trt_detector
    if _trt_detector is None:
        _trt_detector = TRTDetector()
    return _trt_detector


@app.on_event("startup")
async def startup_event():
    print("[INFO] Initializing Traffic Sign Recognition System...")
    get_detector()
    get_trt_detector()
    print("[INFO] System initialized successfully")


@app.get("/", tags=["System"])
async def root():
    return {
        "service": API_TITLE,
        "version": API_VERSION,
        "endpoints": {
            "health": "/health",
            "detect_image": "/api/v1/detect/image",
            "detect_video": "/api/v1/detect/video",
            "video_stream": "/api/v1/video/stream",
            "info": "/api/v1/system/info",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["System"])
async def health_check():
    detector = get_detector()
    return {
        "status": "healthy",
        "yolo_available": detector._initialized if detector else False,
        "tensorrt_available": get_trt_detector().is_available,
        "timestamp": time.time()
    }


@app.get("/api/v1/system/info", tags=["System"], response_model=SystemInfoResponse)
async def get_system_info():
    detector = get_detector()
    trt = get_trt_detector()
    from config import TRAFFIC_SIGN_CLASSES, CLASS_CATEGORIES

    return SystemInfoResponse(
        yolo_available=detector._initialized if detector else False,
        tensorrt_available=trt.is_available,
        device="CUDA" if trt.is_available else "CPU",
        supported_classes=TRAFFIC_SIGN_CLASSES,
        categories=CLASS_CATEGORIES,
        features={
            "enhanced_fpn": True,
            "hard_example_mining": True,
            "adaptive_resolution": True,
            "per_frame_processing": True,
            "quantization": {
                "fp16": True,
                "int8": True
            }
        }
    )


@app.post("/api/v1/detect/image", tags=["Detection"], response_model=DetectionResponse)
async def detect_image(
    file: UploadFile = File(...),
    conf_threshold: Optional[float] = Query(
        default=CONF_THRESHOLD,
        description="Confidence threshold for detection"
    ),
    filter_category: Optional[str] = Query(
        default=None,
        description="Filter by category (speed_limit, prohibitory, indicative, warning)"
    ),
    filter_class: Optional[str] = Query(
        default=None,
        description="Filter by specific class name"
    ),
    return_annotated: bool = Query(
        default=True,
        description="Return annotated image as base64"
    ),
    use_enhanced_fpn: bool = Query(
        default=True,
        description="Enable enhanced FPN for small target detection"
    )
):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        start_time = time.time()

        detector = get_detector(use_enhanced_fpn=use_enhanced_fpn)
        detections = detector.detect(image, conf_threshold)

        if filter_category:
            detections = [d for d in detections if d.category == filter_category]
        if filter_class:
            detections = [d for d in detections if d.class_name == filter_class]

        processing_time = (time.time() - start_time) * 1000

        small_targets = sum(1 for d in detections if d.is_small_target)
        high_res_count = sum(1 for d in detections if d.scale == "high_res")

        statistics = {
            "total": len(detections),
            "by_category": {},
            "by_class": {},
            "avg_confidence": 0.0,
            "small_targets": small_targets,
            "high_res_detections": high_res_count
        }
        if detections:
            for d in detections:
                statistics["by_category"][d.category] = statistics["by_category"].get(d.category, 0) + 1
                statistics["by_class"][d.class_name] = statistics["by_class"].get(d.class_name, 0) + 1
            statistics["avg_confidence"] = sum(d.confidence for d in detections) / len(detections)

        annotated_base64 = None
        if return_annotated:
            annotated = detector.draw_detections(image, detections)
            _, buffer = cv2.imencode('.jpg', annotated)
            annotated_base64 = base64.b64encode(buffer).decode('utf-8')

        return DetectionResponse(
            success=True,
            detections=[d.to_dict() for d in detections],
            statistics=statistics,
            processing_time=round(processing_time, 2),
            annotated_image=annotated_base64,
            small_targets_count=small_targets,
            high_res_detections_count=high_res_count
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@app.post("/api/v1/detect/video", tags=["Detection"])
async def detect_video(
    file: UploadFile = File(...),
    conf_threshold: Optional[float] = Query(default=CONF_THRESHOLD),
    output_format: str = Query(default="json", description="json or annotated")
):
    try:
        import tempfile
        contents = await file.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            cap = cv2.VideoCapture(tmp_path)
            if not cap.isOpened():
                raise HTTPException(status_code=400, detail="Invalid video file")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            detector = get_detector(use_enhanced_fpn=True)
            all_detections = []
            frame_idx = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                detections = detector.detect(frame, conf_threshold)
                if detections:
                    frame_detections = [d.to_dict() for d in detections]
                    all_detections.append({
                        "frame": frame_idx,
                        "timestamp": frame_idx / fps if fps > 0 else 0,
                        "detections": frame_detections
                    })

                frame_idx += 1
                if frame_idx % 30 == 0:
                    print(f"[INFO] Processed {frame_idx}/{total_frames} frames")

            cap.release()

            return {
                "success": True,
                "total_frames": frame_idx,
                "fps": round(fps, 2),
                "frames_with_detections": len(all_detections),
                "detections": all_detections
            }

        finally:
            os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video processing failed: {str(e)}")


@app.get("/api/v1/video/stream", tags=["Video"])
async def video_stream(
    source: int = Query(default=0, description="Camera index or video source"),
    conf_threshold: float = Query(default=CONF_THRESHOLD),
    width: int = Query(default=640),
    height: int = Query(default=480),
    fps: int = Query(default=30),
    use_enhanced_fpn: bool = Query(default=True, description="Enable enhanced FPN"),
    enable_adaptive_resolution: bool = Query(default=True, description="Enable adaptive resolution"),
    process_every_frame: bool = Query(default=True, description="Process every frame (no skip)")
):
    detector = get_detector(use_enhanced_fpn=use_enhanced_fpn)
    processor = VideoProcessor(
        detector=detector,
        source=source,
        width=width,
        height=height,
        fps=fps,
        conf_threshold=conf_threshold,
        display=False,
        enable_adaptive_resolution=enable_adaptive_resolution,
        process_every_frame=process_every_frame
    )

    if not processor.start():
        raise HTTPException(status_code=500, detail="Failed to start video stream")

    def generate():
        try:
            while True:
                result = processor.get_results(timeout=1.0)
                if result is None:
                    continue

                annotated = result.annotated_frame
                if annotated is None:
                    annotated = result.frame

                _, buffer = cv2.imencode('.jpg', annotated)
                frame_bytes = buffer.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            print(f"[ERROR] Stream error: {e}")
        finally:
            processor.stop()

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace;boundary=frame"
    )


@app.get("/api/v1/video/results", tags=["Video"])
async def get_stream_results(
    source: int = Query(default=0),
    conf_threshold: float = Query(default=CONF_THRESHOLD),
    duration: float = Query(default=10.0, description="Stream duration in seconds")
):
    detector = get_detector()
    processor = VideoProcessor(
        detector=detector,
        source=source,
        conf_threshold=conf_threshold,
        display=False
    )

    if not processor.start():
        raise HTTPException(status_code=500, detail="Failed to start video stream")

    results = []
    start_time = time.time()

    try:
        while time.time() - start_time < duration:
            result = processor.get_results(timeout=0.5)
            if result and result.detections:
                results.append({
                    "timestamp": result.timestamp,
                    "detections": [d.to_dict() for d in result.detections]
                })
    finally:
        processor.stop()

    return {
        "success": True,
        "duration": duration,
        "frames_with_detections": len(results),
        "results": results
    }


@app.get("/api/v1/video/enhanced", tags=["Video"])
async def get_enhanced_stream_results(
    source: int = Query(default=0),
    conf_threshold: float = Query(default=CONF_THRESHOLD),
    duration: float = Query(default=10.0, description="Stream duration in seconds"),
    enable_temporal_fusion: bool = Query(default=True),
    enable_distance_estimation: bool = Query(default=True),
    enable_country_adaptation: bool = Query(default=True),
    country_code: str = Query(default="CN", description="Country code for adaptation"),
    temporal_window_size: int = Query(default=5, description="Temporal fusion window size")
):
    detector = get_detector(use_enhanced_fpn=True)
    processor = VideoProcessor(
        detector=detector,
        source=source,
        conf_threshold=conf_threshold,
        display=False,
        enable_temporal_fusion=enable_temporal_fusion,
        enable_distance_estimation=enable_distance_estimation,
        enable_country_adaptation=enable_country_adaptation,
        country_code=country_code,
        temporal_window_size=temporal_window_size
    )

    if not processor.start():
        raise HTTPException(status_code=500, detail="Failed to start video stream")

    results = []
    start_time = time.time()

    try:
        while time.time() - start_time < duration:
            result = processor.get_results(timeout=0.5)
            if result:
                frame_data = {
                    "timestamp": result.timestamp,
                    "detections": [d.to_dict() for d in result.detections] if result.detections else [],
                    "enhanced": processor.get_enhanced_results()
                }
                results.append(frame_data)
    finally:
        processor.stop()

    return {
        "success": True,
        "duration": duration,
        "total_frames": len(results),
        "results": results
    }


@app.get("/api/v1/country/supported", tags=["Country"])
async def get_supported_countries():
    from processor.country_adapter import CountryAdapter

    adapter = CountryAdapter()
    return {
        "success": True,
        "countries": adapter.get_supported_countries()
    }


@app.get("/api/v1/country/info", tags=["Country"])
async def get_country_info(country_code: str = Query(default="CN")):
    from processor.country_adapter import CountryAdapter

    adapter = CountryAdapter(default_country=country_code)
    info = adapter.get_country_info(country_code)

    if info is None:
        raise HTTPException(status_code=404, detail=f"Country code '{country_code}' not supported")

    return {
        "success": True,
        "country": info
    }


@app.post("/api/v1/detect/enhanced", tags=["Detection"])
async def detect_enhanced(
    file: UploadFile = File(...),
    conf_threshold: float = Query(default=CONF_THRESHOLD),
    use_enhanced_fpn: bool = Query(default=True),
    enable_distance_estimation: bool = Query(default=True),
    enable_country_adaptation: bool = Query(default=True),
    country_code: str = Query(default="CN")
):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        start_time = time.time()

        detector = get_detector(use_enhanced_fpn=use_enhanced_fpn)
        detections = detector.detect(image, conf_threshold)

        distance_results = []
        if enable_distance_estimation:
            from processor.distance_estimator import SignDistanceEstimator

            dist_estimator = SignDistanceEstimator(
                image_width=image.shape[1],
                image_height=image.shape[0]
            )
            distance_results = dist_estimator.estimate_batch(detections, image.shape)

        adapted_results = []
        if enable_country_adaptation:
            from processor.country_adapter import CountryAdapter

            adapter = CountryAdapter(default_country=country_code)
            adapted_results = adapter.batch_adapt(detections)

        processing_time = (time.time() - start_time) * 1000

        annotated = detector.draw_detections(image, detections)
        if distance_results:
            from processor.distance_estimator import SignDistanceEstimator
            dist_estimator = SignDistanceEstimator()
            annotated = dist_estimator.draw_distance(annotated, distance_results)

        _, buffer = cv2.imencode('.jpg', annotated)
        annotated_base64 = base64.b64encode(buffer).decode('utf-8')

        return {
            "success": True,
            "detections": [d.to_dict() for d in detections],
            "distances": [
                {
                    "class_name": dr.distance.class_name,
                    "distance": dr.distance.distance,
                    "unit": dr.distance.unit,
                    "confidence": dr.distance.confidence,
                    "method": dr.distance.method
                }
                for dr in distance_results
            ],
            "adapted": [
                {
                    "original_class": ad.original_class,
                    "adapted_class": ad.adapted_class,
                    "country_code": ad.country_code,
                    "local_name": ad.local_name
                }
                for ad in adapted_results
            ],
            "statistics": {
                "total": len(detections),
                "small_targets": sum(1 for d in detections if d.is_small_target),
                "processing_time_ms": round(processing_time, 2)
            },
            "annotated_image": annotated_base64
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced detection failed: {str(e)}")


@app.get("/api/v1/classes", tags=["Classes"])
async def get_classes(country_code: Optional[str] = Query(default=None)):
    from config import TRAFFIC_SIGN_CLASSES, CLASS_ZH_CN, CLASS_CATEGORIES

    response = {
        "total_classes": len(TRAFFIC_SIGN_CLASSES),
        "classes": [
            {
                "id": i,
                "name": name,
                "name_zh": CLASS_ZH_CN.get(name, name),
                "category": next(
                    (cat for cat, classes in CLASS_CATEGORIES.items() if name in classes),
                    "unknown"
                )
            }
            for i, name in enumerate(TRAFFIC_SIGN_CLASSES)
        ],
        "categories": list(CLASS_CATEGORIES.keys())
    }

    if country_code:
        from processor.country_adapter import CountryAdapter
        adapter = CountryAdapter(default_country=country_code)
        standard = adapter.get_current_standard()
        response["country_adaptation"] = {
            "country_code": country_code,
            "country_name": standard.country_name,
            "units": standard.speed_limit_units,
            "class_mapping": standard.class_mapping
        }

    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
