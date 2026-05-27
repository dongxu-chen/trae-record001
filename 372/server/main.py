import io
import json
import os
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, WebSocket, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from schemas import ExportRequest, SAMStatus
from image_service import image_service
from websocket_handler import ws_handler
from sam_model import sam_service
from video_service import video_service
from quality_service import quality_check_service
from version_service import version_service

app = FastAPI(title="Image Segmentation Annotation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if sam_service.is_model_available():
        sam_service.load_model()
    else:
        print("""
        ============================================================
        SAM model weights not found. SAM functionality will be disabled.
        Please download the model weights:
        
        For vit_b (default):
        https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
        
        For vit_l:
        https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth
        
        For vit_h:
        https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth
        
        Place the downloaded file in: server/models/
        ============================================================
        """)
    yield
    sam_service.clear_cache()

app.router.lifespan_context = lifespan


@app.get("/")
async def root():
    return {
        "name": "Image Segmentation Annotation API",
        "version": "3.0.0",
        "features": {
            "sam_gpu": "SAM model with GPU acceleration and caching",
            "edge_smoothing": "Edge post-processing for smoother masks",
            "export_formats": ["json", "mask", "yolo", "labelme", "voc", "coco"],
            "video_annotation": "Video annotation with keyframe interpolation",
            "quality_check": "Automatic quality check for overlaps and missing regions",
            "version_control": "Annotation version management with rollback"
        },
        "endpoints": {
            "images": "/api/images",
            "videos": "/api/videos",
            "sam_status": "/api/sam/status",
            "sam_stats": "/api/sam/stats",
            "export": "/api/export/{format}",
            "quality": "/api/quality/check",
            "versions": "/api/versions/{image_id}",
            "websocket": "/ws/sam"
        }
    }


@app.get("/api/sam/status", response_model=SAMStatus)
async def get_sam_status():
    status = sam_service.get_status()
    return SAMStatus(
        loaded=status["loaded"],
        modelType=status["modelType"]
    )


@app.get("/api/sam/stats")
async def get_sam_stats():
    return sam_service.get_status()


@app.get("/api/sam/cache/clear")
async def clear_sam_cache(image_id: Optional[str] = None):
    if image_id:
        sam_service.reset_image(image_id)
        return {"success": True, "message": f"Cache cleared for image {image_id}"}
    else:
        sam_service.clear_cache()
        return {"success": True, "message": "All cache cleared"}


@app.get("/api/images")
async def list_images():
    return image_service.list_images()


@app.post("/api/images")
async def upload_image(file: UploadFile = File(...)):
    try:
        content = await file.read()
        image_info = image_service.save_image(content, file.filename)
        return image_info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/images/{image_id}")
async def get_image_info(image_id: str):
    info = image_service.get_image_info(image_id)
    if not info:
        raise HTTPException(status_code=404, detail="Image not found")
    return info


@app.get("/api/images/{image_id}/data")
async def get_image_data(image_id: str):
    filepath = image_service.get_image_path(image_id)
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found")
    
    with open(filepath, 'rb') as f:
        content = f.read()
    
    ext = os.path.splitext(filepath)[1].lower()
    media_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        '.tiff': 'image/tiff'
    }.get(ext, 'image/png')
    
    return StreamingResponse(io.BytesIO(content), media_type=media_type)


@app.delete("/api/images/{image_id}")
async def delete_image(image_id: str):
    success = image_service.delete_image(image_id)
    if not success:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"success": True}


@app.get("/api/videos")
async def list_videos():
    return video_service.list_videos()


@app.post("/api/videos")
async def upload_video(file: UploadFile = File(...)):
    try:
        content = await file.read()
        video_info = video_service.upload_video(content, file.filename)
        return video_info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/videos/{video_id}")
async def get_video_info(video_id: str):
    info = video_service.get_video_info(video_id)
    if not info:
        raise HTTPException(status_code=404, detail="Video not found")
    return info


@app.post("/api/videos/{video_id}/keyframes")
async def extract_keyframes(
    video_id: str,
    interval: int = Query(30, ge=1, le=300),
    max_keyframes: int = Query(100, ge=1, le=500)
):
    try:
        keyframes = video_service.extract_keyframes(video_id, interval, max_keyframes)
        return {"keyframes": keyframes}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/videos/{video_id}/frames/{frame_idx}")
async def get_video_frame(video_id: str, frame_idx: int):
    frame_path = video_service.get_frame_image(video_id, frame_idx)
    if not frame_path or not os.path.exists(frame_path):
        frame_info = video_service.extract_single_frame(video_id, frame_idx)
        if not frame_info:
            raise HTTPException(status_code=404, detail="Frame not found")
        frame_path = video_service.get_frame_image(video_id, frame_idx)
    
    if not frame_path or not os.path.exists(frame_path):
        raise HTTPException(status_code=404, detail="Frame not found")
    
    with open(frame_path, 'rb') as f:
        content = f.read()
    
    return StreamingResponse(io.BytesIO(content), media_type='image/jpeg')


@app.post("/api/videos/{video_id}/interpolate")
async def interpolate_annotations(
    video_id: str,
    start_frame: int = Body(...),
    end_frame: int = Body(...),
    start_annotations: list = Body(...),
    end_annotations: list = Body(...)
):
    try:
        interpolated = video_service.interpolate_annotations(
            video_id, start_frame, end_frame,
            start_annotations, end_annotations
        )
        return {"interpolated": interpolated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/videos/{video_id}/annotations")
async def save_video_annotations(
    video_id: str,
    frame_idx: int = Body(...),
    annotations: list = Body(...)
):
    video_service.set_frame_annotations(video_id, frame_idx, annotations)
    return {"success": True}


@app.get("/api/videos/{video_id}/annotations")
async def get_video_annotations(video_id: str):
    return video_service.get_all_annotations(video_id)


@app.delete("/api/videos/{video_id}")
async def delete_video(video_id: str):
    success = video_service.delete_video(video_id)
    if not success:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"success": True}


@app.post("/api/quality/check")
async def check_annotation_quality(
    image_id: str = Body(...),
    annotations: list = Body(...)
):
    try:
        image_info = image_service.get_image_info(image_id)
        if not image_info:
            raise HTTPException(status_code=404, detail="Image not found")
        
        image_array = image_service.get_image_array(image_id)
        
        report = quality_check_service.check_annotations(
            annotations,
            image_info.width,
            image_info.height,
            image_array
        )
        
        return {
            "quality_score": report.quality_score,
            "total_annotations": report.total_annotations,
            "issues": [issue.__dict__ for issue in report.issues],
            "overlap_regions": report.overlap_regions,
            "missing_regions": report.missing_regions,
            "details": report.details
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/quality/check-video")
async def check_video_quality(
    video_id: str = Body(...),
    frame_annotations: dict = Body(...)
):
    try:
        video_info = video_service.get_video_info(video_id)
        if not video_info:
            raise HTTPException(status_code=404, detail="Video not found")
        
        report = quality_check_service.check_video_annotations(
            frame_annotations,
            video_info.width,
            video_info.height
        )
        
        return {
            "quality_score": report.quality_score,
            "total_annotations": report.total_annotations,
            "issues": [issue.__dict__ for issue in report.issues],
            "details": report.details
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/versions/{image_id}")
async def get_versions(image_id: str):
    versions = version_service.get_versions(image_id)
    return {"versions": [v.__dict__ for v in versions]}


@app.post("/api/versions/{image_id}")
async def save_version(
    image_id: str,
    annotations: list = Body(...),
    description: str = Body(default=""),
    author: str = Body(default="user")
):
    try:
        version = version_service.save_version(image_id, annotations, description, author)
        return {"version": version.__dict__}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/versions/{image_id}/{version_id}")
async def get_version(image_id: str, version_id: str):
    version = version_service.get_version(image_id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"version": version.__dict__}


@app.post("/api/versions/{image_id}/{version_id}/rollback")
async def rollback_to_version(image_id: str, version_id: str):
    annotations = version_service.rollback_to_version(image_id, version_id)
    if annotations is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"annotations": annotations}


@app.get("/api/versions/{image_id}/compare/{version_id_1}/{version_id_2}")
async def compare_versions(image_id: str, version_id_1: str, version_id_2: str):
    diff = version_service.compare_versions(image_id, version_id_1, version_id_2)
    if not diff:
        raise HTTPException(status_code=404, detail="Versions not found")
    return {
        "added": diff.added,
        "removed": diff.removed,
        "modified": diff.modified,
        "unchanged": diff.unchanged
    }


@app.delete("/api/versions/{image_id}/{version_id}")
async def delete_version(image_id: str, version_id: str):
    success = version_service.delete_version(image_id, version_id)
    if not success:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"success": True}


@app.post("/api/export/json")
async def export_json(request: ExportRequest):
    try:
        export_data = image_service.export_annotations_to_json(
            request.imageId,
            request.annotations
        )
        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        return StreamingResponse(
            io.BytesIO(json_str.encode('utf-8')),
            media_type='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="annotations_{request.imageId}.json"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/export/mask")
async def export_mask(request: ExportRequest):
    try:
        image_info = image_service.get_image_info(request.imageId)
        if not image_info:
            raise HTTPException(status_code=404, detail="Image not found")
        
        mask_bytes = image_service.export_mask_to_png(
            request.annotations,
            image_info.width,
            image_info.height
        )
        
        return StreamingResponse(
            io.BytesIO(mask_bytes),
            media_type='image/png',
            headers={
                'Content-Disposition': f'attachment; filename="mask_{request.imageId}.png"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/export/yolo")
async def export_yolo(request: ExportRequest):
    try:
        image_info = image_service.get_image_info(request.imageId)
        if not image_info:
            raise HTTPException(status_code=404, detail="Image not found")
        
        yolo_content = image_service.export_yolo_format(
            request.imageId,
            request.annotations,
            image_info.width,
            image_info.height
        )
        
        label_map = image_service.export_label_map()
        
        return JSONResponse({
            "annotations": yolo_content,
            "label_map": label_map,
            "image_width": image_info.width,
            "image_height": image_info.height
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/export/labelme")
async def export_labelme(request: ExportRequest):
    try:
        image_info = image_service.get_image_info(request.imageId)
        if not image_info:
            raise HTTPException(status_code=404, detail="Image not found")
        
        labelme_data = image_service.export_labelme_format(
            request.imageId,
            request.annotations,
            image_info.width,
            image_info.height,
            image_info.filename
        )
        
        json_str = json.dumps(labelme_data, indent=2, ensure_ascii=False)
        return StreamingResponse(
            io.BytesIO(json_str.encode('utf-8')),
            media_type='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="labelme_{request.imageId}.json"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/export/voc")
async def export_voc(request: ExportRequest):
    try:
        image_info = image_service.get_image_info(request.imageId)
        if not image_info:
            raise HTTPException(status_code=404, detail="Image not found")
        
        voc_content = image_service.export_voc_format(
            request.imageId,
            request.annotations,
            image_info.width,
            image_info.height,
            image_info.filename
        )
        
        return StreamingResponse(
            io.BytesIO(voc_content.encode('utf-8')),
            media_type='application/xml',
            headers={
                'Content-Disposition': f'attachment; filename="voc_{request.imageId}.xml"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/export/coco")
async def export_coco(request: ExportRequest):
    try:
        image_info = image_service.get_image_info(request.imageId)
        if not image_info:
            raise HTTPException(status_code=404, detail="Image not found")
        
        coco_data = image_service.export_coco_format(
            request.imageId,
            request.annotations,
            image_info.width,
            image_info.height,
            image_info.filename
        )
        
        json_str = json.dumps(coco_data, indent=2, ensure_ascii=False)
        return StreamingResponse(
            io.BytesIO(json_str.encode('utf-8')),
            media_type='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="coco_{request.imageId}.json"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/export/formats")
async def get_export_formats():
    return {
        "formats": [
            {"id": "json", "name": "JSON", "description": "Custom JSON format with all annotation data", "extension": ".json"},
            {"id": "mask", "name": "Mask PNG", "description": "Colored segmentation mask image", "extension": ".png"},
            {"id": "yolo", "name": "YOLO", "description": "YOLO object detection format", "extension": ".txt"},
            {"id": "labelme", "name": "LabelMe", "description": "LabelMe annotation format", "extension": ".json"},
            {"id": "voc", "name": "Pascal VOC", "description": "Pascal VOC XML format", "extension": ".xml"},
            {"id": "coco", "name": "COCO", "description": "COCO JSON format", "extension": ".json"}
        ]
    }


@app.websocket("/ws/sam")
async def websocket_endpoint(websocket: WebSocket):
    await ws_handler.handle_connection(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
