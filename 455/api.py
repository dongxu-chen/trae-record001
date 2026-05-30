import os
import cv2
import uuid
import aiofiles
import tempfile
import numpy as np
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

from detector import YOLODetector
from tracker import DeepSORT
from processor import VideoProcessor
from config import Config

Config.ensure_dirs()

app = FastAPI(
    title="视频目标检测与跟踪系统 API",
    description="基于YOLOv8 + DeepSORT的多目标检测与跟踪系统",
    version="1.0.0"
)

processor: Optional[VideoProcessor] = None
processing_tasks: Dict[str, Dict[str, Any]] = {}


class ProcessRequest(BaseModel):
    source: str
    save_output: bool = True
    show_preview: bool = False


class ProcessResponse(BaseModel):
    success: bool
    message: str
    task_id: Optional[str] = None
    output_path: Optional[str] = None


class TrackInfo(BaseModel):
    id: int
    class_id: int
    class_name: str
    bbox: List[float]
    confidence: float
    trail: List[List[float]]
    age: int
    hits: int


class FrameResult(BaseModel):
    frame_index: int
    tracks: List[TrackInfo]
    num_objects: int


@app.on_event("startup")
async def startup_event():
    global processor
    try:
        processor = VideoProcessor()
        print("VideoProcessor 初始化成功")
    except Exception as e:
        print(f"VideoProcessor 初始化失败: {e}")
        processor = None


@app.get("/")
async def root():
    return {
        "name": "视频目标检测与跟踪系统",
        "version": "3.0.0",
        "features": {
            "occlusion_robust_tracking": "外观+运动融合关联，降低ID切换",
            "high_resolution_branch": "小目标高分辨率检测，提升召回率",
            "skip_frame_detection": "跳帧检测+卡尔曼插值，平衡速度精度",
            "anomaly_detection": "轨迹异常检测：徘徊/逆行/速度异常",
            "cross_camera_tracking": "跨摄像头接力跟踪，多相机ID协同",
            "metrics_dashboard": "MOTA/IDF1实时评估仪表板",
        },
        "endpoints": {
            "/health": "健康检查",
            "/detect/image": "单张图片检测",
            "/detect/video": "上传视频处理",
            "/process/webcam": "摄像头实时视频流",
            "/process/video/{filename}": "视频文件实时流",
            "/tasks/{task_id}": "查询处理任务状态",
            "/outputs/{filename}": "下载处理结果",
            "/settings": "获取系统设置",
            "/settings/skip_frame/toggle": "切换跳帧检测",
            "/settings/skip_frame/interval": "设置检测间隔",
            "/settings/high_resolution/toggle": "切换高分辨率分支",
            "/settings/anomaly/toggle": "切换异常检测",
            "/settings/cross_camera/toggle": "切换跨摄像头跟踪",
            "/settings/metrics/toggle": "切换评估仪表板",
            "/metrics": "获取评估指标",
            "/anomalies": "获取异常事件",
            "/cross_camera": "获取跨摄像头信息",
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if processor is not None else "unhealthy",
        "processor_initialized": processor is not None,
    }


@app.post("/detect/image")
async def detect_image(file: UploadFile = File(...)):
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    try:
        async with aiofiles.open(temp_file.name, 'wb') as f:
            content = await file.read()
            await f.write(content)

        frame = cv2.imread(temp_file.name)
        if frame is None:
            raise HTTPException(status_code=400, detail="无法读取图片")

        annotated_frame, tracks = processor.process_frame(frame)

        output_filename = f"{uuid.uuid4()}.jpg"
        output_path = os.path.join(Config.OUTPUT_DIR, output_filename)
        cv2.imwrite(output_path, annotated_frame)

        track_list = []
        for track in tracks:
            track_list.append({
                "id": track["id"],
                "class_id": int(track["class_id"]),
                "class_name": processor.detector.get_class_name(track["class_id"]),
                "bbox": track["bbox"].tolist(),
                "confidence": float(track["confidence"]),
                "trail": [[float(p[0]), float(p[1])] for p in track["trail"]],
                "age": track["age"],
                "hits": track["hits"],
            })

        return JSONResponse(content={
            "success": True,
            "num_objects": len(tracks),
            "tracks": track_list,
            "output_url": f"/outputs/{output_filename}"
        })

    finally:
        os.unlink(temp_file.name)


@app.post("/detect/video")
async def detect_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")

    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="请上传视频文件")

    task_id = str(uuid.uuid4())
    input_filename = f"{task_id}_{file.filename}"
    input_path = os.path.join(Config.UPLOAD_DIR, input_filename)
    output_filename = f"{task_id}_output.mp4"
    output_path = os.path.join(Config.OUTPUT_DIR, output_filename)

    async with aiofiles.open(input_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    processing_tasks[task_id] = {
        "id": task_id,
        "status": "pending",
        "input_path": input_path,
        "output_path": output_path,
        "progress": 0,
        "total_frames": 0,
        "current_frame": 0,
        "results": [],
    }

    background_tasks.add_task(process_video_task, task_id, input_path, output_path)

    return JSONResponse(content={
        "success": True,
        "message": "视频处理任务已创建",
        "task_id": task_id,
        "status_url": f"/tasks/{task_id}",
    })


def process_video_task(task_id: str, input_path: str, output_path: str):
    global processor
    if processor is None:
        processing_tasks[task_id]["status"] = "failed"
        processing_tasks[task_id]["error"] = "处理器未初始化"
        return

    try:
        processor.reset_tracker()
        processing_tasks[task_id]["status"] = "processing"

        all_tracks = []
        frame_index = 0

        cap = cv2.VideoCapture(input_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        processing_tasks[task_id]["total_frames"] = total_frames
        cap.release()

        for annotated_frame, tracks in processor.process_video(input_path, output_path, show_progress=False):
            frame_index += 1
            processing_tasks[task_id]["current_frame"] = frame_index
            processing_tasks[task_id]["progress"] = int(100 * frame_index / total_frames) if total_frames > 0 else 0

            track_list = []
            for track in tracks:
                track_list.append({
                    "id": track["id"],
                    "class_id": int(track["class_id"]),
                    "class_name": processor.detector.get_class_name(track["class_id"]),
                    "bbox": track["bbox"].tolist(),
                    "confidence": float(track["confidence"]),
                })

            all_tracks.append({
                "frame_index": frame_index,
                "tracks": track_list,
                "num_objects": len(tracks),
            })

        processing_tasks[task_id]["status"] = "completed"
        processing_tasks[task_id]["results"] = all_tracks
        processing_tasks[task_id]["output_filename"] = os.path.basename(output_path)

    except Exception as e:
        processing_tasks[task_id]["status"] = "failed"
        processing_tasks[task_id]["error"] = str(e)


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = processing_tasks[task_id].copy()
    if "results" in task and len(task["results"]) > 10:
        task["results_preview"] = task["results"][:10]
        del task["results"]

    return JSONResponse(content=task)


@app.get("/process/webcam")
async def process_webcam():
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")

    processor.reset_tracker()

    def generate():
        for annotated_frame, tracks in processor.process_webcam(camera_index=0):
            ret, jpeg = cv2.imencode('.jpg', annotated_frame)
            if not ret:
                continue
            frame_bytes = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')

    return StreamingResponse(
        generate(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )


@app.get("/process/video/{filename}")
async def process_saved_video(filename: str):
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")

    input_path = os.path.join(Config.UPLOAD_DIR, filename)
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="视频文件不存在")

    processor.reset_tracker()

    def generate():
        for annotated_frame, tracks in processor.process_video(input_path):
            ret, jpeg = cv2.imencode('.jpg', annotated_frame)
            if not ret:
                continue
            frame_bytes = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')

    return StreamingResponse(
        generate(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )


@app.get("/outputs/{filename}")
async def download_output(filename: str):
    output_path = os.path.join(Config.OUTPUT_DIR, filename)
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        output_path,
        media_type="application/octet-stream",
        filename=filename
    )


@app.post("/settings/skip_frame/toggle")
async def toggle_skip_frame():
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")
    status = processor.toggle_skip_frame()
    return JSONResponse(content={
        "success": True,
        "skip_frame_enabled": status,
        "detect_interval": processor.detect_interval
    })


@app.post("/settings/skip_frame/interval")
async def set_detect_interval(interval: int):
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")
    actual_interval = processor.set_detect_interval(interval)
    return JSONResponse(content={
        "success": True,
        "detect_interval": actual_interval
    })


@app.post("/settings/high_resolution/toggle")
async def toggle_high_resolution():
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")
    status = processor.toggle_high_resolution()
    processor.reset_tracker()
    return JSONResponse(content={
        "success": True,
        "high_resolution_enabled": status
    })


@app.get("/settings")
async def get_settings():
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")
    return JSONResponse(content={
        "skip_frame_enabled": processor.skip_frame_enable,
        "detect_interval": processor.detect_interval,
        "interpolation_enabled": processor.interpolation_enable,
        "high_resolution_enabled": processor.detector.high_res_enable,
        "high_resolution_scale": processor.detector.high_res_scale,
        "small_object_area_threshold": processor.detector.small_object_area,
        "anomaly_enabled": processor.anomaly_enable,
        "cross_camera_enabled": processor.cross_camera_enable,
        "metrics_enabled": processor.metrics_enable,
        "camera_id": processor.camera_id,
    })


@app.post("/settings/anomaly/toggle")
async def toggle_anomaly():
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")
    status = processor.toggle_anomaly()
    return JSONResponse(content={
        "success": True,
        "anomaly_enabled": status
    })


@app.post("/settings/cross_camera/toggle")
async def toggle_cross_camera():
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")
    status = processor.toggle_cross_camera()
    return JSONResponse(content={
        "success": True,
        "cross_camera_enabled": status
    })


@app.post("/settings/metrics/toggle")
async def toggle_metrics():
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")
    status = processor.toggle_metrics()
    return JSONResponse(content={
        "success": True,
        "metrics_enabled": status
    })


@app.get("/metrics")
async def get_metrics():
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")
    return JSONResponse(content=processor.get_metrics_data())


@app.get("/anomalies")
async def get_anomalies(n: int = 20):
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")
    return JSONResponse(content={
        "events": processor.get_anomaly_events(n),
        "count": len(processor.anomaly_detector.anomaly_events),
    })


@app.get("/cross_camera")
async def get_cross_camera_info():
    if processor is None:
        raise HTTPException(status_code=503, detail="处理器未初始化")
    return JSONResponse(content=processor.get_cross_camera_info())


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    if processor is None:
        await websocket.send_json({"error": "处理器未初始化"})
        await websocket.close()
        return

    processor.reset_tracker()

    try:
        cap = cv2.VideoCapture(0)
        while True:
            data = await websocket.receive_bytes()
            if not data:
                break

            nparr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            annotated_frame, tracks = processor.process_frame(frame)

            track_list = []
            for track in tracks:
                track_list.append({
                    "id": track["id"],
                    "class_id": int(track["class_id"]),
                    "class_name": processor.detector.get_class_name(track["class_id"]),
                    "bbox": track["bbox"].tolist(),
                    "confidence": float(track["confidence"]),
                })

            ret, jpeg = cv2.imencode('.jpg', annotated_frame)
            frame_bytes = jpeg.tobytes()

            await websocket.send_json({
                "num_objects": len(tracks),
                "tracks": track_list,
            })
            await websocket.send_bytes(frame_bytes)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        if 'cap' in locals():
            cap.release()
        try:
            await websocket.close()
        except:
            pass


if __name__ == "__main__":
    Config.ensure_dirs()
    uvicorn.run(
        "api:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=True
    )
