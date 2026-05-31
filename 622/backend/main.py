from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uuid
import shutil
from PIL import Image
import numpy as np
import io

from style_transfer import StyleTransfer
from image_utils import process_image, adjust_intensity

app = FastAPI(title="AI Style Transfer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("../uploads")
OUTPUT_DIR = Path("../outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory="../uploads"), name="uploads")
app.mount("/outputs", StaticFiles(directory="../outputs"), name="outputs")

style_transfer = StyleTransfer()

STYLE_PRESETS = [
    {"id": "vangogh", "name": "梵高星空", "description": "印象派后印象主义风格", "category": "classic"},
    {"id": "picasso", "name": "毕加索立体主义", "description": "立体主义抽象风格", "category": "classic"},
    {"id": "monet", "name": "莫奈睡莲", "description": "印象派光影风格", "category": "classic"},
    {"id": "kanagawa", "name": "神奈川冲浪", "description": "日本浮世绘风格", "category": "classic"},
    {"id": "cyberpunk", "name": "赛博朋克", "description": "未来科技霓虹风格", "category": "modern"},
    {"id": "watercolor", "name": "水彩画", "description": "清新水彩风格", "category": "modern"},
    {"id": "oil_painting", "name": "油画", "description": "厚重油画质感", "category": "modern"},
    {"id": "sketch", "name": "素描", "description": "铅笔素描风格", "category": "modern"},
]


@app.get("/")
async def root():
    return {"message": "AI Style Transfer API", "version": "1.0.0"}


@app.get("/api/styles")
async def get_styles():
    return {"styles": STYLE_PRESETS}


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported image format")
    
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}{file_ext}"
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    processed_path = process_image(file_path, UPLOAD_DIR / f"{file_id}_processed{file_ext}")
    
    return {
        "id": file_id,
        "original_url": f"/uploads/{file_id}{file_ext}",
        "processed_url": f"/uploads/{file_id}_processed{file_ext}"
    }


@app.post("/api/transfer")
async def style_transfer_endpoint(
    content_id: str = Form(...),
    style_id: str = Form(...),
    intensity: float = Form(0.7),
    model_type: str = Form("gan"),
    style_image: UploadFile = File(None)
):
    content_path = next(UPLOAD_DIR.glob(f"{content_id}*"), None)
    if not content_path:
        raise HTTPException(status_code=404, detail="Content image not found")
    
    style_path = None
    if style_image:
        style_ext = Path(style_image.filename).suffix.lower()
        style_file_id = str(uuid.uuid4())
        style_path = UPLOAD_DIR / f"{style_file_id}{style_ext}"
        with style_path.open("wb") as buffer:
            shutil.copyfileobj(style_image.file, buffer)
    else:
        style_path = Path(f"styles/{style_id}.jpg")
        if not style_path.exists():
            raise HTTPException(status_code=404, detail="Style preset not found")
    
    output_id = str(uuid.uuid4())
    output_path = OUTPUT_DIR / f"{output_id}.jpg"
    
    try:
        result_img = style_transfer.transfer(
            content_path=str(content_path),
            style_path=str(style_path),
            model_type=model_type,
            intensity=intensity
        )
        result_img.save(str(output_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Style transfer failed: {str(e)}")
    
    return {
        "id": output_id,
        "output_url": f"/outputs/{output_id}.jpg",
        "intensity": intensity,
        "model": model_type
    }


@app.post("/api/preview")
async def preview_transfer(
    content_id: str = Form(...),
    style_id: str = Form(...),
    intensity: float = Form(0.7),
    model_type: str = Form("fast")
):
    content_path = next(UPLOAD_DIR.glob(f"{content_id}*"), None)
    if not content_path:
        raise HTTPException(status_code=404, detail="Content image not found")
    
    style_path = Path(f"styles/{style_id}.jpg")
    if not style_path.exists():
        style_path = next(UPLOAD_DIR.glob(f"{style_id}*"), None)
    
    if not style_path:
        raise HTTPException(status_code=404, detail="Style image not found")
    
    preview_id = f"preview_{uuid.uuid4().hex[:8]}"
    preview_path = OUTPUT_DIR / f"{preview_id}.jpg"
    
    try:
        result_img = style_transfer.transfer(
            content_path=str(content_path),
            style_path=str(style_path),
            model_type=model_type,
            intensity=intensity,
            preview=True
        )
        result_img.save(str(preview_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")
    
    return {
        "id": preview_id,
        "preview_url": f"/outputs/{preview_id}.jpg"
    }


@app.get("/api/models")
async def get_models():
    return {
        "models": [
            {"id": "gan", "name": "GAN", "description": "快速风格迁移，适合实时预览", "speed": "fast"},
            {"id": "diffusion", "name": "Diffusion", "description": "高质量风格迁移，细节更丰富", "speed": "slow"}
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
