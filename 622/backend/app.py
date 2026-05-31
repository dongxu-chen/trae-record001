from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
import uuid
import shutil
from PIL import Image
import threading
import time
import queue

from style_transfer import StyleTransfer
from image_utils import process_image

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
STYLES_DIR = BASE_DIR / "backend" / "styles"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
STYLES_DIR.mkdir(exist_ok=True)

style_transfer = StyleTransfer()

preview_queue = queue.Queue(maxsize=1)
current_preview_task = {'cancel': False, 'lock': threading.Lock()}

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


@app.route('/')
def root():
    return jsonify({"message": "AI Style Transfer API", "version": "2.0.0", "model": "SD Turbo"})


@app.route('/api/styles')
def get_styles():
    return jsonify({"styles": STYLE_PRESETS})


@app.route('/api/models')
def get_models():
    return jsonify({
        "models": [
            {"id": "sd_turbo", "name": "SD Turbo", "description": "超高速风格迁移，<1秒推理", "speed": "ultra-fast"},
            {"id": "gan", "name": "GAN", "description": "快速风格迁移，适合实时预览", "speed": "fast"},
            {"id": "diffusion", "name": "Diffusion", "description": "高质量风格迁移，细节更丰富", "speed": "slow"}
        ]
    })


@app.route('/api/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not file.content_type.startswith('image/'):
        return jsonify({"error": "File must be an image"}), 400
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        return jsonify({"error": "Unsupported image format"}), 400
    
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}{file_ext}"
    file.save(str(file_path))
    
    processed_filename = f"{file_id}_processed{file_ext}"
    processed_path = UPLOAD_DIR / processed_filename
    
    try:
        process_image(str(file_path), str(processed_path))
    except Exception as e:
        print(f"Processing error: {e}")
        shutil.copy(str(file_path), str(processed_path))
    
    return jsonify({
        "id": file_id,
        "original_url": f"/uploads/{file_id}{file_ext}",
        "processed_url": f"/uploads/{processed_filename}"
    })


def process_preview_task(content_path, style_id, intensity, model_type, output_path):
    with current_preview_task['lock']:
        if current_preview_task['cancel']:
            return False
        
        try:
            content_img = Image.open(str(content_path)).convert('RGB')
            result_img = style_transfer._sd_turbo_transfer(
                content_img, style_id, StyleTransfer.curve_intensity_map(intensity)
            )
            result_img.save(str(output_path), 'JPEG', quality=85)
            return True
        except Exception as e:
            print(f"Preview processing error: {e}")
            return False


@app.route('/api/preview', methods=['POST'])
def preview_transfer():
    content_id = request.form.get('content_id')
    style_id = request.form.get('style_id')
    intensity = float(request.form.get('intensity', 0.7))
    model_type = request.form.get('model_type', 'sd_turbo')
    
    if not content_id or not style_id:
        return jsonify({"error": "Content ID and Style ID are required"}), 400
    
    content_path = None
    for f in UPLOAD_DIR.glob(f"{content_id}*"):
        if "_processed" not in f.name and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
            content_path = f
            break
    
    if not content_path:
        return jsonify({"error": "Content image not found"}), 404
    
    with current_preview_task['lock']:
        current_preview_task['cancel'] = True
    
    time.sleep(0.02)
    
    with current_preview_task['lock']:
        current_preview_task['cancel'] = False
    
    preview_id = f"preview_{uuid.uuid4().hex[:8]}"
    preview_path = OUTPUT_DIR / f"{preview_id}.jpg"
    
    success = process_preview_task(content_path, style_id, intensity, model_type, preview_path)
    
    if not success:
        return jsonify({"error": "Preview cancelled"}), 499
    
    return jsonify({
        "id": preview_id,
        "preview_url": f"/outputs/{preview_id}.jpg",
        "model": "sd_turbo"
    })


@app.route('/api/transfer', methods=['POST'])
def style_transfer_endpoint():
    content_id = request.form.get('content_id')
    style_id = request.form.get('style_id')
    intensity = float(request.form.get('intensity', 0.7))
    model_type = request.form.get('model_type', 'sd_turbo')
    
    if not content_id:
        return jsonify({"error": "Content ID is required"}), 400
    
    content_path = None
    for f in UPLOAD_DIR.glob(f"{content_id}*"):
        if "_processed" not in f.name and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
            content_path = f
            break
    
    if not content_path:
        return jsonify({"error": "Content image not found"}), 404
    
    style_path = None
    style_file = request.files.get('style_image')
    if style_file:
        style_ext = Path(style_file.filename).suffix.lower()
        style_file_id = str(uuid.uuid4())
        style_path = UPLOAD_DIR / f"{style_file_id}{style_ext}"
        style_file.save(str(style_path))
    else:
        style_path = STYLES_DIR / f"{style_id}.jpg"
        if not style_path.exists():
            style_path = None
    
    output_id = str(uuid.uuid4())
    output_path = OUTPUT_DIR / f"{output_id}.jpg"
    
    start_time = time.time()
    
    try:
        if style_path:
            result_img = style_transfer.transfer(
                content_path=str(content_path),
                style_path=str(style_path),
                model_type=model_type,
                intensity=intensity
            )
        else:
            content_img = Image.open(str(content_path)).convert('RGB')
            perceptual_intensity = StyleTransfer.curve_intensity_map(intensity)
            result_img = style_transfer._sd_turbo_transfer(
                content_img, style_id or 'watercolor', perceptual_intensity
            )
        
        result_img.save(str(output_path), 'JPEG', quality=95)
        elapsed = time.time() - start_time
        
    except Exception as e:
        print(f"Style transfer error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Style transfer failed: {str(e)}"}), 500
    
    return jsonify({
        "id": output_id,
        "output_url": f"/outputs/{output_id}.jpg",
        "intensity": intensity,
        "model": model_type,
        "inference_time_ms": round(elapsed * 1000, 1)
    })


@app.route('/api/cancel-preview', methods=['POST'])
def cancel_preview():
    with current_preview_task['lock']:
        current_preview_task['cancel'] = True
    return jsonify({"status": "cancelled"})


@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    style_id = data.get('style_id')
    rating = data.get('rating')
    user_id = data.get('user_id', 'default')
    content_id = data.get('content_id')
    
    if not style_id or rating is None:
        return jsonify({"error": "style_id and rating are required"}), 400
    
    if not isinstance(rating, (int, float)) or rating < 1 or rating > 5:
        return jsonify({"error": "rating must be between 1 and 5"}), 400
    
    content_features = None
    if content_id:
        content_path = None
        for f in UPLOAD_DIR.glob(f"{content_id}*"):
            if "_processed" not in f.name and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                content_path = f
                break
        if content_path:
            try:
                img = Image.open(str(content_path)).convert('RGB')
                content_features = style_transfer.extract_image_features(img)
            except Exception as e:
                print(f"Failed to extract features: {e}")
    
    feedback = style_transfer.add_feedback(style_id, rating, content_features, user_id)
    
    return jsonify({
        "status": "success",
        "feedback": feedback,
        "feedback_count": len(style_transfer.user_feedback[user_id])
    })


@app.route('/api/personalized-models', methods=['GET'])
def get_personalized_models():
    user_id = request.args.get('user_id', 'default')
    models = style_transfer.get_personalized_models(user_id)
    return jsonify({"models": models})


@app.route('/api/train-model', methods=['POST'])
def train_model():
    data = request.json
    user_id = data.get('user_id', 'default')
    model_name = data.get('name', 'My Style')
    base_styles = data.get('base_styles')
    
    try:
        model_data = style_transfer.train_personalized_model(user_id, model_name, base_styles)
        return jsonify({
            "status": "success",
            "model": model_data
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Training error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Training failed: {str(e)}"}), 500


@app.route('/api/styles/extended', methods=['GET'])
def get_extended_styles():
    user_id = request.args.get('user_id', 'default')
    base_styles = [dict(s) for s in STYLE_PRESETS]
    personalized_models = style_transfer.get_personalized_models(user_id)
    
    personalized_styles = [
        {
            "id": m['id'],
            "name": m['name'],
            "description": f"个性化风格 - 基于{m['trained_on']}条反馈训练",
            "category": "personalized",
            "style_weights": m['style_weights']
        }
        for m in personalized_models
    ]
    
    all_styles = base_styles + personalized_styles
    return jsonify({"styles": all_styles})


@app.route('/api/transfer-mixed', methods=['POST'])
def transfer_mixed():
    data = request.json
    content_id = data.get('content_id')
    style_weights = data.get('style_weights')
    intensity = float(data.get('intensity', 0.7))
    model_type = data.get('model_type', 'sd_turbo')
    preview = data.get('preview', False)
    
    if not content_id:
        return jsonify({"error": "content_id is required"}), 400
    
    if not style_weights or not isinstance(style_weights, dict):
        return jsonify({"error": "style_weights must be a non-empty dict"}), 400
    
    content_path = None
    for f in UPLOAD_DIR.glob(f"{content_id}*"):
        if "_processed" not in f.name and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
            content_path = f
            break
    
    if not content_path:
        return jsonify({"error": "Content image not found"}), 404
    
    output_id = str(uuid.uuid4())
    output_path = OUTPUT_DIR / f"{output_id}.jpg"
    
    start_time = time.time()
    
    try:
        result_img = style_transfer.transfer_mixed(
            content_path=str(content_path),
            style_weights=style_weights,
            model_type=model_type,
            intensity=intensity,
            preview=preview
        )
        
        result_img.save(str(output_path), 'JPEG', quality=95)
        elapsed = time.time() - start_time
        
    except Exception as e:
        print(f"Mixed transfer error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Mixed transfer failed: {str(e)}"}), 500
    
    return jsonify({
        "id": output_id,
        "output_url": f"/outputs/{output_id}.jpg",
        "style_weights": style_weights,
        "intensity": intensity,
        "model": model_type,
        "inference_time_ms": round(elapsed * 1000, 1)
    })


@app.route('/api/batch-transfer', methods=['POST'])
def batch_transfer():
    data = request.json
    content_ids = data.get('content_ids', [])
    style_ids = data.get('style_ids', [])
    intensity = float(data.get('intensity', 0.7))
    model_type = data.get('model_type', 'sd_turbo')
    
    if not content_ids or not style_ids:
        return jsonify({"error": "content_ids and style_ids are required"}), 400
    
    content_paths = []
    for content_id in content_ids:
        content_path = None
        for f in UPLOAD_DIR.glob(f"{content_id}*"):
            if "_processed" not in f.name and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                content_path = f
                break
        if content_path:
            content_paths.append(str(content_path))
        else:
            return jsonify({"error": f"Content image {content_id} not found"}), 404
    
    start_time = time.time()
    
    try:
        results = style_transfer.batch_transfer(
            content_paths=content_paths,
            style_ids=style_ids,
            model_type=model_type,
            intensity=intensity
        )
        
        output_results = []
        for i, result in enumerate(results):
            if result['success']:
                output_id = str(uuid.uuid4())
                output_path = OUTPUT_DIR / f"{output_id}.jpg"
                result['result'].save(str(output_path), 'JPEG', quality=95)
                output_results.append({
                    "id": output_id,
                    "output_url": f"/outputs/{output_id}.jpg",
                    "content_id": content_ids[i // len(style_ids)],
                    "style_id": result['style_id'],
                    "success": True
                })
            else:
                output_results.append({
                    "content_id": content_ids[i // len(style_ids)],
                    "style_id": result['style_id'],
                    "success": False,
                    "error": result['error']
                })
        
        elapsed = time.time() - start_time
        
    except Exception as e:
        print(f"Batch transfer error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Batch transfer failed: {str(e)}"}), 500
    
    return jsonify({
        "status": "completed",
        "total": len(results),
        "success": sum(1 for r in output_results if r['success']),
        "failed": sum(1 for r in output_results if not r['success']),
        "total_time_ms": round(elapsed * 1000, 1),
        "results": output_results
    })


@app.route('/api/batch-transfer-mixed', methods=['POST'])
def batch_transfer_mixed():
    data = request.json
    content_ids = data.get('content_ids', [])
    style_weights_list = data.get('style_combinations', [])
    intensity = float(data.get('intensity', 0.7))
    model_type = data.get('model_type', 'sd_turbo')
    
    if not content_ids or not style_weights_list:
        return jsonify({"error": "content_ids and style_combinations are required"}), 400
    
    content_paths = []
    for content_id in content_ids:
        content_path = None
        for f in UPLOAD_DIR.glob(f"{content_id}*"):
            if "_processed" not in f.name and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                content_path = f
                break
        if content_path:
            content_paths.append(str(content_path))
        else:
            return jsonify({"error": f"Content image {content_id} not found"}), 404
    
    start_time = time.time()
    
    try:
        results = style_transfer.batch_transfer_mixed(
            content_paths=content_paths,
            style_weights_list=style_weights_list,
            model_type=model_type,
            intensity=intensity
        )
        
        output_results = []
        for result in results:
            if result['success']:
                output_id = str(uuid.uuid4())
                output_path = OUTPUT_DIR / f"{output_id}.jpg"
                result['result'].save(str(output_path), 'JPEG', quality=95)
                try:
                    content_idx = content_paths.index(result['content_path'])
                    content_id = content_ids[content_idx] if content_idx < len(content_ids) else None
                except ValueError:
                    content_id = None
                output_results.append({
                    "id": output_id,
                    "output_url": f"/outputs/{output_id}.jpg",
                    "content_id": content_id,
                    "content_path": result['content_path'],
                    "style_combination": result['style_combination'],
                    "style_weights": result['style_weights'],
                    "success": True
                })
            else:
                output_results.append({
                    "content_path": result['content_path'],
                    "style_combination": result['style_combination'],
                    "success": False,
                    "error": result['error']
                })
        
        elapsed = time.time() - start_time
        
    except Exception as e:
        print(f"Batch mixed transfer error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Batch mixed transfer failed: {str(e)}"}), 500
    
    return jsonify({
        "status": "completed",
        "total": len(results),
        "success": sum(1 for r in output_results if r['success']),
        "failed": sum(1 for r in output_results if not r['success']),
        "total_time_ms": round(elapsed * 1000, 1),
        "results": output_results
    })


@app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(str(UPLOAD_DIR), filename)


@app.route('/outputs/<filename>')
def serve_output(filename):
    return send_from_directory(str(OUTPUT_DIR), filename)


if __name__ == "__main__":
    print("=" * 50)
    print("AI Style Transfer Server - SD Turbo Edition")
    print("=" * 50)
    print(f"Upload directory: {UPLOAD_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"API endpoint: http://localhost:8000")
    print(f"Features:")
    print(f"  - SD Turbo Ultra-fast inference (<1s)")
    print(f"  - Perceptual intensity curve mapping")
    print(f"  - Preview request cancellation")
    print(f"  - User feedback & rating system")
    print(f"  - Personalized style model training")
    print(f"  - Multi-style weighted blending")
    print(f"  - Batch processing (multi-image, multi-style)")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8000, debug=False)
