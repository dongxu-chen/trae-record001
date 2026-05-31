import os
import uuid
import json
import logging
import threading
import numpy as np
from flask import Blueprint, request, jsonify, send_file
from config import UPLOAD_DIR, OUTPUT_DIR, MODEL_DIR, MVSNET_CONFIG, RECONSTRUCTION_CONFIG

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)

tasks = {}
task_lock = threading.Lock()

from modules.depth_estimation import DepthEstimator
from modules.point_cloud import PointCloudFusion
from modules.surface_recon import SurfaceReconstructor
from modules.depth_completion import MultiViewDepthCompletion
from modules.adaptive_fusion import AdaptivePointCloudFusion
from modules.hole_filling import EnhancedSurfaceReconstructor
from modules.realtime import VideoStreamProcessor, IncrementalReconstructor
from modules.dynamic_removal import DynamicObjectRemover
from modules.texture_mapping import MeshTexturer

_estimator = None
_fuser = None
_reconstructor = None
_depth_completer = None
_adaptive_fuser = None
_enhanced_reconstructor = None
_dynamic_remover = None
_mesh_texturer = None
_stream_processor = None


def get_estimator():
    global _estimator
    if _estimator is None:
        _estimator = DepthEstimator()
        ckpt = os.path.join(MODEL_DIR, "mvsnet.ckpt")
        if os.path.exists(ckpt):
            _estimator.load_pretrained(ckpt)
    return _estimator


def get_fuser():
    global _fuser
    if _fuser is None:
        _fuser = PointCloudFusion()
    return _fuser


def get_reconstructor():
    global _reconstructor
    if _reconstructor is None:
        _reconstructor = SurfaceReconstructor()
    return _reconstructor


def get_depth_completer():
    global _depth_completer
    if _depth_completer is None:
        _depth_completer = MultiViewDepthCompletion()
    return _depth_completer


def get_adaptive_fuser():
    global _adaptive_fuser
    if _adaptive_fuser is None:
        _adaptive_fuser = AdaptivePointCloudFusion()
    return _adaptive_fuser


def get_enhanced_reconstructor():
    global _enhanced_reconstructor
    if _enhanced_reconstructor is None:
        _enhanced_reconstructor = EnhancedSurfaceReconstructor()
    return _enhanced_reconstructor


def get_dynamic_remover():
    global _dynamic_remover
    if _dynamic_remover is None:
        _dynamic_remover = DynamicObjectRemover()
    return _dynamic_remover


def get_mesh_texturer():
    global _mesh_texturer
    if _mesh_texturer is None:
        _mesh_texturer = MeshTexturer()
    return _mesh_texturer


def get_stream_processor():
    global _stream_processor
    return _stream_processor


@api_bp.route("/health", methods=["GET"])
def health_check():
    cuda_available = False
    try:
        import torch
        cuda_available = torch.cuda.is_available()
    except Exception:
        pass
    return jsonify({"status": "ok", "cuda_available": cuda_available})


@api_bp.route("/depth/estimate", methods=["POST"])
def estimate_depth():
    task_id = str(uuid.uuid4())

    ref_image = request.files.get("ref_image")
    if ref_image is None:
        return jsonify({"error": "ref_image is required"}), 400

    src_images = request.files.getlist("src_images")
    if not src_images:
        return jsonify({"error": "src_images are required"}), 400

    cam_params = request.form.get("cam_params")
    if cam_params is None:
        return jsonify({"error": "cam_params JSON is required"}), 400

    try:
        cam_params = json.loads(cam_params)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid cam_params JSON"}), 400

    task_dir = os.path.join(OUTPUT_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    ref_path = os.path.join(task_dir, "ref.png")
    ref_image.save(ref_path)

    src_paths = []
    for i, img in enumerate(src_images):
        src_path = os.path.join(task_dir, f"src_{i}.png")
        img.save(src_path)
        src_paths.append(src_path)

    ref_cam = cam_params.get("ref_cam")
    src_cams = cam_params.get("src_cams", [])

    if ref_cam is None:
        return jsonify({"error": "ref_cam is required in cam_params"}), 400

    depth_min = request.form.get("depth_min", type=float)
    depth_max = request.form.get("depth_max", type=float)

    try:
        estimator = get_estimator()
        depth_map, prob_map, depth_values = estimator.estimate_depth(
            ref_path, src_paths, ref_cam, src_cams, depth_min, depth_max
        )

        depth_path = os.path.join(task_dir, "depth.npy")
        prob_path = os.path.join(task_dir, "prob.npy")
        np.save(depth_path, depth_map)
        np.save(prob_path, prob_map)

        import cv2
        depth_vis = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min() + 1e-8)
        depth_vis = (depth_vis * 255).astype(np.uint8)
        depth_vis_path = os.path.join(task_dir, "depth_vis.png")
        cv2.imwrite(depth_vis_path, depth_vis)

        return jsonify({
            "task_id": task_id,
            "depth_shape": list(depth_map.shape),
            "depth_min": float(depth_map.min()),
            "depth_max": float(depth_map.max()),
            "depth_file": depth_path,
            "prob_file": prob_path,
        })

    except Exception as e:
        logger.exception("Depth estimation failed")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/depth/batch", methods=["POST"])
def estimate_depth_batch():
    task_id = str(uuid.uuid4())

    images = request.files.getlist("images")
    if len(images) < 2:
        return jsonify({"error": "At least 2 images required"}), 400

    cam_params = request.form.get("cam_params")
    if cam_params is None:
        return jsonify({"error": "cam_params JSON is required"}), 400

    try:
        cam_params = json.loads(cam_params)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid cam_params JSON"}), 400

    if len(cam_params) != len(images):
        return jsonify({"error": "Number of cam_params must match number of images"}), 400

    task_dir = os.path.join(OUTPUT_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    image_paths = []
    for i, img in enumerate(images):
        img_path = os.path.join(task_dir, f"img_{i}.png")
        img.save(img_path)
        image_paths.append(img_path)

    depth_min = request.form.get("depth_min", type=float)
    depth_max = request.form.get("depth_max", type=float)

    def run_batch():
        try:
            with task_lock:
                tasks[task_id]["status"] = "processing"

            estimator = get_estimator()
            all_depths, all_probs, depth_values = estimator.estimate_depth_batch(
                image_paths, cam_params, depth_min, depth_max
            )

            results = {}
            for idx, (depth, prob) in zip(all_depths.keys(), zip(all_depths.values(), all_probs.values())):
                d_path = os.path.join(task_dir, f"depth_{idx}.npy")
                p_path = os.path.join(task_dir, f"prob_{idx}.npy")
                np.save(d_path, depth)
                np.save(p_path, prob)
                results[idx] = {"depth_file": d_path, "prob_file": p_path}

            with task_lock:
                tasks[task_id]["status"] = "completed"
                tasks[task_id]["results"] = results

        except Exception as e:
            logger.exception("Batch depth estimation failed")
            with task_lock:
                tasks[task_id]["status"] = "failed"
                tasks[task_id]["error"] = str(e)

    with task_lock:
        tasks[task_id] = {"status": "queued", "type": "depth_batch"}

    thread = threading.Thread(target=run_batch)
    thread.start()

    return jsonify({"task_id": task_id, "status": "queued"})


@api_bp.route("/pointcloud/fuse", methods=["POST"])
def fuse_point_cloud():
    task_id = str(uuid.uuid4())

    depth_files = request.form.getlist("depth_files")
    prob_files = request.form.getlist("prob_files")
    cam_params = request.form.get("cam_params")

    if not depth_files or not prob_files or not cam_params:
        return jsonify({"error": "depth_files, prob_files, and cam_params are required"}), 400

    try:
        cam_params = json.loads(cam_params)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid cam_params JSON"}), 400

    depth_maps = [np.load(f) for f in depth_files]
    prob_maps = [np.load(f) for f in prob_files]

    image_paths = request.form.getlist("image_paths")

    prob_threshold = request.form.get("prob_threshold", type=float)
    voxel_size = request.form.get("voxel_size", type=float)

    recon_config = RECONSTRUCTION_CONFIG.copy()
    if prob_threshold is not None:
        recon_config["prob_threshold"] = prob_threshold
    if voxel_size is not None:
        recon_config["voxel_size"] = voxel_size

    try:
        fuser = PointCloudFusion(config=recon_config)
        points, colors = fuser.fuse_depth_maps(
            depth_maps, prob_maps, cam_params,
            image_paths=image_paths if image_paths else None
        )

        if points is None:
            return jsonify({"error": "Fusion produced no points"}), 500

        task_dir = os.path.join(OUTPUT_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)

        pcd = fuser.filter_point_cloud(points, colors, voxel_size=recon_config["voxel_size"])
        pcd = fuser.estimate_normals(
            np.asarray(pcd.points),
            np.asarray(pcd.colors) if pcd.has_colors() else None,
            voxel_size=recon_config["voxel_size"],
        )

        ply_path = os.path.join(task_dir, "point_cloud.ply")
        o3d.io.write_point_cloud(ply_path, pcd)

        return jsonify({
            "task_id": task_id,
            "num_points": len(pcd.points),
            "ply_file": ply_path,
        })

    except Exception as e:
        logger.exception("Point cloud fusion failed")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/surface/reconstruct", methods=["POST"])
def reconstruct_surface():
    task_id = str(uuid.uuid4())

    ply_file = request.form.get("ply_file")
    if not ply_file or not os.path.exists(ply_file):
        return jsonify({"error": "Valid ply_file path is required"}), 400

    method = request.form.get("method", "poisson")
    poisson_depth = request.form.get("poisson_depth", type=int)
    do_simplify = request.form.get("simplify", "true").lower() == "true"
    do_smooth = request.form.get("smooth", "true").lower() == "true"

    try:
        import open3d as o3d
        pcd = o3d.io.read_point_cloud(ply_file)

        if len(pcd.points) == 0:
            return jsonify({"error": "Point cloud is empty"}), 400

        recon_config = RECONSTRUCTION_CONFIG.copy()
        if poisson_depth is not None:
            recon_config["poisson_depth"] = poisson_depth

        reconstructor = SurfaceReconstructor(config=recon_config)

        kwargs = {}
        if method == "poisson" and poisson_depth is not None:
            kwargs["depth"] = poisson_depth

        mesh = reconstructor.reconstruct(
            pcd, method=method, simplify=do_simplify, smooth=do_smooth, **kwargs
        )

        if mesh is None:
            return jsonify({"error": "Reconstruction produced empty mesh"}), 500

        task_dir = os.path.join(OUTPUT_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)

        output_path = os.path.join(task_dir, "mesh")
        ply_path, obj_path = SurfaceReconstructor.save_mesh(mesh, output_path)

        stats = reconstructor.compute_mesh_quality(mesh)

        return jsonify({
            "task_id": task_id,
            "method": method,
            "mesh_stats": stats,
            "ply_file": ply_path,
            "obj_file": obj_path,
        })

    except Exception as e:
        logger.exception("Surface reconstruction failed")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/reconstruct/full", methods=["POST"])
def full_reconstruction():
    task_id = str(uuid.uuid4())

    images = request.files.getlist("images")
    if len(images) < 2:
        return jsonify({"error": "At least 2 images required"}), 400

    cam_params = request.form.get("cam_params")
    if cam_params is None:
        return jsonify({"error": "cam_params JSON is required"}), 400

    try:
        cam_params = json.loads(cam_params)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid cam_params JSON"}), 400

    if len(cam_params) != len(images):
        return jsonify({"error": "Number of cam_params must match number of images"}), 400

    method = request.form.get("method", "poisson")
    depth_min = request.form.get("depth_min", type=float)
    depth_max = request.form.get("depth_max", type=float)

    task_dir = os.path.join(OUTPUT_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    image_paths = []
    for i, img in enumerate(images):
        img_path = os.path.join(task_dir, f"img_{i}.png")
        img.save(img_path)
        image_paths.append(img_path)

    def run_full():
        try:
            import open3d as o3d

            with task_lock:
                tasks[task_id]["status"] = "estimating_depth"

            estimator = get_estimator()
            all_depths, all_probs, depth_values = estimator.estimate_depth_batch(
                image_paths, cam_params, depth_min, depth_max
            )

            depth_list = [all_depths[i] for i in sorted(all_depths.keys())]
            prob_list = [all_probs[i] for i in sorted(all_probs.keys())]

            for idx in sorted(all_depths.keys()):
                np.save(os.path.join(task_dir, f"depth_{idx}.npy"), all_depths[idx])
                np.save(os.path.join(task_dir, f"prob_{idx}.npy"), all_probs[idx])

            with task_lock:
                tasks[task_id]["status"] = "fusing_point_cloud"

            fuser = get_fuser()
            points, colors = fuser.fuse_depth_maps(
                depth_list, prob_list, cam_params, image_paths=image_paths
            )

            if points is None:
                with task_lock:
                    tasks[task_id]["status"] = "failed"
                    tasks[task_id]["error"] = "Fusion produced no points"
                return

            pcd = fuser.filter_point_cloud(points, colors)
            pcd = fuser.estimate_normals(
                np.asarray(pcd.points),
                np.asarray(pcd.colors) if pcd.has_colors() else None,
            )

            ply_path = os.path.join(task_dir, "point_cloud.ply")
            o3d.io.write_point_cloud(ply_path, pcd)

            with task_lock:
                tasks[task_id]["status"] = "reconstructing_surface"
                tasks[task_id]["point_cloud_file"] = ply_path
                tasks[task_id]["num_points"] = len(pcd.points)

            reconstructor = get_reconstructor()
            mesh = reconstructor.reconstruct(pcd, method=method)

            if mesh is None:
                with task_lock:
                    tasks[task_id]["status"] = "failed"
                    tasks[task_id]["error"] = "Reconstruction produced empty mesh"
                return

            output_path = os.path.join(task_dir, "mesh")
            ply_mesh, obj_mesh = SurfaceReconstructor.save_mesh(mesh, output_path)
            stats = reconstructor.compute_mesh_quality(mesh)

            with task_lock:
                tasks[task_id]["status"] = "completed"
                tasks[task_id]["mesh_stats"] = stats
                tasks[task_id]["mesh_ply"] = ply_mesh
                tasks[task_id]["mesh_obj"] = obj_mesh

        except Exception as e:
            logger.exception("Full reconstruction failed")
            with task_lock:
                tasks[task_id]["status"] = "failed"
                tasks[task_id]["error"] = str(e)

    with task_lock:
        tasks[task_id] = {"status": "queued", "type": "full_reconstruction"}

    thread = threading.Thread(target=run_full)
    thread.start()

    return jsonify({"task_id": task_id, "status": "queued"})


@api_bp.route("/task/<task_id>", methods=["GET"])
def get_task_status(task_id):
    with task_lock:
        task = tasks.get(task_id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
    return jsonify({"task_id": task_id, **task})


@api_bp.route("/download/<path:filepath>", methods=["GET"])
def download_file(filepath):
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    return send_file(filepath, as_attachment=True)


@api_bp.route("/depth/complete", methods=["POST"])
def complete_depth():
    task_id = str(uuid.uuid4())

    depth_files = request.form.getlist("depth_files")
    cam_params = request.form.get("cam_params")
    image_files = request.files.getlist("images")

    if not depth_files or not cam_params:
        return jsonify({"error": "depth_files and cam_params are required"}), 400

    try:
        cam_params = json.loads(cam_params)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid cam_params JSON"}), 400

    if len(depth_files) != len(cam_params):
        return jsonify({"error": "Number of depth_files must match cam_params"}), 400

    depth_maps = [np.load(f) for f in depth_files]

    images = None
    if image_files and len(image_files) == len(depth_files):
        import cv2
        images = []
        for img_file in image_files:
            img = cv2.imdecode(
                np.frombuffer(img_file.read(), np.uint8),
                cv2.IMREAD_COLOR
            )
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            images.append(img)

    try:
        completer = get_depth_completer()
        completed_depths, hole_masks = completer.complete_all_views(
            depth_maps, cam_params, images=images
        )

        task_dir = os.path.join(OUTPUT_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)

        results = []
        for idx, (depth, hole_mask) in enumerate(zip(completed_depths, hole_masks)):
            depth_path = os.path.join(task_dir, f"completed_{idx}.npy")
            np.save(depth_path, depth)

            original_holes = depth_maps[idx] <= 0
            filled_count = np.sum(original_holes & ~hole_mask)
            remaining_count = np.sum(hole_mask)

            results.append({
                "view_idx": idx,
                "depth_file": depth_path,
                "original_holes": int(np.sum(original_holes)),
                "filled_holes": int(filled_count),
                "remaining_holes": int(remaining_count),
            })

        return jsonify({
            "task_id": task_id,
            "completed_views": len(completed_depths),
            "results": results,
        })

    except Exception as e:
        logger.exception("Depth completion failed")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/pointcloud/fuse_adaptive", methods=["POST"])
def fuse_point_cloud_adaptive():
    task_id = str(uuid.uuid4())

    depth_files = request.form.getlist("depth_files")
    prob_files = request.form.getlist("prob_files")
    cam_params = request.form.get("cam_params")

    if not depth_files or not prob_files or not cam_params:
        return jsonify({"error": "depth_files, prob_files, and cam_params are required"}), 400

    try:
        cam_params = json.loads(cam_params)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid cam_params JSON"}), 400

    depth_maps = [np.load(f) for f in depth_files]
    prob_maps = [np.load(f) for f in prob_files]

    image_paths = request.form.getlist("image_paths")
    use_adaptive = request.form.get("use_adaptive", "true").lower() == "true"

    prob_threshold = request.form.get("prob_threshold", type=float)
    voxel_size = request.form.get("voxel_size", type=float)

    try:
        fuser = AdaptivePointCloudFusion()

        if prob_threshold is not None:
            fuser.prob_threshold = prob_threshold
        if voxel_size is not None:
            fuser.base_voxel_size = voxel_size

        points, colors, texture_scores = fuser.fuse_depth_maps_adaptive(
            depth_maps, prob_maps, cam_params,
            image_paths=image_paths if image_paths else None,
            use_adaptive=use_adaptive,
        )

        if points is None:
            return jsonify({"error": "Fusion produced no points"}), 500

        task_dir = os.path.join(OUTPUT_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)

        if use_adaptive and texture_scores is not None:
            pcd = fuser.adaptive_voxel_downsample(points, colors, texture_scores)
        else:
            import open3d as o3d
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(points)
            if colors is not None:
                pcd.colors = o3d.utility.Vector3dVector(colors)
            pcd = pcd.voxel_down_sample(fuser.base_voxel_size)

        pcd = fuser.filter_point_cloud_adaptive(pcd)
        pcd = fuser.estimate_normals(pcd)

        ply_path = os.path.join(task_dir, "point_cloud_adaptive.ply")
        import open3d as o3d
        o3d.io.write_point_cloud(ply_path, pcd)

        texture_stats = None
        if texture_scores is not None:
            texture_stats = {
                "mean": float(np.mean(texture_scores)),
                "median": float(np.median(texture_scores)),
                "high_texture_ratio": float(np.mean(texture_scores > fuser.texture_threshold)),
            }

        return jsonify({
            "task_id": task_id,
            "num_points": len(pcd.points),
            "adaptive_resolution": use_adaptive,
            "texture_stats": texture_stats,
            "ply_file": ply_path,
        })

    except Exception as e:
        logger.exception("Adaptive point cloud fusion failed")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/surface/reconstruct_enhanced", methods=["POST"])
def reconstruct_surface_enhanced():
    task_id = str(uuid.uuid4())

    ply_file = request.form.get("ply_file")
    if not ply_file or not os.path.exists(ply_file):
        return jsonify({"error": "Valid ply_file path is required"}), 400

    method = request.form.get("method", "poisson")
    fill_holes = request.form.get("fill_holes", "true").lower() == "true"
    do_simplify = request.form.get("simplify", "true").lower() == "true"
    do_smooth = request.form.get("smooth", "true").lower() == "true"

    try:
        import open3d as o3d
        pcd = o3d.io.read_point_cloud(ply_file)

        if len(pcd.points) == 0:
            return jsonify({"error": "Point cloud is empty"}), 400

        reconstructor = get_enhanced_reconstructor()

        mesh, fill_stats = reconstructor.reconstruct_with_hole_handling(
            pcd, method=method, fill_holes=fill_holes,
            simplify=do_simplify, smooth=do_smooth,
        )

        if mesh is None:
            return jsonify({"error": "Reconstruction produced empty mesh"}), 500

        task_dir = os.path.join(OUTPUT_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)

        output_path = os.path.join(task_dir, "mesh_enhanced")
        ply_path, obj_path = SurfaceReconstructor.save_mesh(mesh, output_path)

        stats = reconstructor.base_reconstructor.compute_mesh_quality(mesh)

        hole_report = reconstructor.get_hole_report(mesh)

        return jsonify({
            "task_id": task_id,
            "method": method,
            "fill_holes_enabled": fill_holes,
            "mesh_stats": stats,
            "fill_stats": fill_stats,
            "hole_report": hole_report,
            "ply_file": ply_path,
            "obj_file": obj_path,
        })

    except Exception as e:
        logger.exception("Enhanced surface reconstruction failed")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/surface/analyze_holes", methods=["POST"])
def analyze_mesh_holes():
    mesh_file = request.form.get("mesh_file")
    if not mesh_file or not os.path.exists(mesh_file):
        return jsonify({"error": "Valid mesh_file path is required"}), 400

    try:
        import open3d as o3d
        mesh = o3d.io.read_triangle_mesh(mesh_file)

        reconstructor = get_enhanced_reconstructor()
        report = reconstructor.get_hole_report(mesh)

        return jsonify({
            "hole_analysis": report,
        })

    except Exception as e:
        logger.exception("Hole analysis failed")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/reconstruct/full_enhanced", methods=["POST"])
def full_reconstruction_enhanced():
    task_id = str(uuid.uuid4())

    images = request.files.getlist("images")
    if len(images) < 2:
        return jsonify({"error": "At least 2 images required"}), 400

    cam_params = request.form.get("cam_params")
    if cam_params is None:
        return jsonify({"error": "cam_params JSON is required"}), 400

    try:
        cam_params = json.loads(cam_params)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid cam_params JSON"}), 400

    if len(cam_params) != len(images):
        return jsonify({"error": "Number of cam_params must match number of images"}), 400

    method = request.form.get("method", "poisson")
    depth_min = request.form.get("depth_min", type=float)
    depth_max = request.form.get("depth_max", type=float)
    complete_depth = request.form.get("complete_depth", "true").lower() == "true"
    adaptive_fusion = request.form.get("adaptive_fusion", "true").lower() == "true"
    fill_holes = request.form.get("fill_holes", "true").lower() == "true"

    task_dir = os.path.join(OUTPUT_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    image_paths = []
    for i, img in enumerate(images):
        img_path = os.path.join(task_dir, f"img_{i}.png")
        img.save(img_path)
        image_paths.append(img_path)

    def run_full_enhanced():
        try:
            import open3d as o3d

            with task_lock:
                tasks[task_id]["status"] = "estimating_depth"

            estimator = get_estimator()
            all_depths, all_probs, depth_values = estimator.estimate_depth_batch(
                image_paths, cam_params, depth_min, depth_max
            )

            depth_list = [all_depths[i] for i in sorted(all_depths.keys())]
            prob_list = [all_probs[i] for i in sorted(all_probs.keys())]

            for idx in sorted(all_depths.keys()):
                np.save(os.path.join(task_dir, f"depth_{idx}.npy"), all_depths[idx])
                np.save(os.path.join(task_dir, f"prob_{idx}.npy"), all_probs[idx])

            if complete_depth:
                with task_lock:
                    tasks[task_id]["status"] = "completing_depth"

                completer = get_depth_completer()
                import cv2
                images_for_completion = []
                for path in image_paths:
                    img = cv2.imread(path)
                    if img is not None:
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        h, w = depth_list[0].shape
                        img = cv2.resize(img, (w, h))
                        images_for_completion.append(img)

                depth_list, _ = completer.complete_all_views(
                    depth_list, cam_params, images=images_for_completion
                )

                for idx, depth in enumerate(depth_list):
                    np.save(os.path.join(task_dir, f"depth_completed_{idx}.npy"), depth)

            with task_lock:
                tasks[task_id]["status"] = "fusing_point_cloud"

            if adaptive_fusion:
                fuser = get_adaptive_fuser()
                points, colors, texture_scores = fuser.fuse_depth_maps_adaptive(
                    depth_list, prob_list, cam_params, image_paths=image_paths
                )

                if points is None:
                    with task_lock:
                        tasks[task_id]["status"] = "failed"
                        tasks[task_id]["error"] = "Fusion produced no points"
                    return

                if texture_scores is not None:
                    pcd = fuser.adaptive_voxel_downsample(points, colors, texture_scores)
                else:
                    pcd = o3d.geometry.PointCloud()
                    pcd.points = o3d.utility.Vector3dVector(points)
                    if colors is not None:
                        pcd.colors = o3d.utility.Vector3dVector(colors)
                    pcd = pcd.voxel_down_sample(fuser.base_voxel_size)

                pcd = fuser.filter_point_cloud_adaptive(pcd)
                pcd = fuser.estimate_normals(pcd)
            else:
                fuser = get_fuser()
                points, colors = fuser.fuse_depth_maps(
                    depth_list, prob_list, cam_params, image_paths=image_paths
                )

                if points is None:
                    with task_lock:
                        tasks[task_id]["status"] = "failed"
                        tasks[task_id]["error"] = "Fusion produced no points"
                    return

                pcd = fuser.filter_point_cloud(points, colors)
                pcd = fuser.estimate_normals(
                    np.asarray(pcd.points),
                    np.asarray(pcd.colors) if pcd.has_colors() else None,
                )

            ply_path = os.path.join(task_dir, "point_cloud.ply")
            o3d.io.write_point_cloud(ply_path, pcd)

            with task_lock:
                tasks[task_id]["status"] = "reconstructing_surface"
                tasks[task_id]["point_cloud_file"] = ply_path
                tasks[task_id]["num_points"] = len(pcd.points)

            reconstructor = get_enhanced_reconstructor()
            mesh, fill_stats = reconstructor.reconstruct_with_hole_handling(
                pcd, method=method, fill_holes=fill_holes,
            )

            if mesh is None:
                with task_lock:
                    tasks[task_id]["status"] = "failed"
                    tasks[task_id]["error"] = "Reconstruction produced empty mesh"
                return

            output_path = os.path.join(task_dir, "mesh")
            ply_mesh, obj_mesh = SurfaceReconstructor.save_mesh(mesh, output_path)
            stats = reconstructor.base_reconstructor.compute_mesh_quality(mesh)

            with task_lock:
                tasks[task_id]["status"] = "completed"
                tasks[task_id]["mesh_stats"] = stats
                tasks[task_id]["mesh_ply"] = ply_mesh
                tasks[task_id]["mesh_obj"] = obj_mesh
                tasks[task_id]["fill_stats"] = fill_stats

        except Exception as e:
            logger.exception("Enhanced full reconstruction failed")
            with task_lock:
                tasks[task_id]["status"] = "failed"
                tasks[task_id]["error"] = str(e)

    with task_lock:
        tasks[task_id] = {"status": "queued", "type": "full_reconstruction_enhanced"}

    thread = threading.Thread(target=run_full_enhanced)
    thread.start()

    return jsonify({"task_id": task_id, "status": "queued"})


@api_bp.route("/config", methods=["GET"])
def get_config():
    return jsonify({
        "mvsnet": MVSNET_CONFIG,
        "reconstruction": RECONSTRUCTION_CONFIG,
        "features": {
            "depth_completion": "Cross-view hole filling",
            "adaptive_fusion": "Texture-aware adaptive resolution",
            "smart_hole_filling": "Geometry-aware hole filling",
            "realtime_reconstruction": "Video stream real-time point cloud",
            "dynamic_removal": "Static scene only reconstruction",
            "texture_mapping": "Projective texture mapping & atlas",
        },
    })


@api_bp.route("/stream/start", methods=["POST"])
def start_stream():
    global _stream_processor

    video_source = request.form.get("video_source", "0")
    if video_source.isdigit():
        video_source = int(video_source)

    frame_skip = request.form.get("frame_skip", type=int, default=2)
    voxel_size = request.form.get("voxel_size", type=float, default=0.01)

    cam_params = request.form.get("cam_params")
    cam_dicts = {}
    if cam_params:
        try:
            cam_dicts = json.loads(cam_params)
        except json.JSONDecodeError:
            pass

    try:
        estimator = get_estimator()
        _stream_processor = VideoStreamProcessor(
            depth_estimator=estimator,
            cam_dicts=cam_dicts,
            frame_skip=frame_skip,
            voxel_size=voxel_size,
        )
        _stream_processor.start_stream(video_source)

        return jsonify({
            "status": "streaming",
            "video_source": str(video_source),
            "frame_skip": frame_skip,
            "voxel_size": voxel_size,
        })
    except Exception as e:
        logger.exception("Failed to start stream")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/stream/stop", methods=["POST"])
def stop_stream():
    global _stream_processor

    if _stream_processor is None:
        return jsonify({"error": "No active stream"}), 400

    _stream_processor.stop_stream()

    task_id = str(uuid.uuid4())
    task_dir = os.path.join(OUTPUT_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    pcd_path = os.path.join(task_dir, "realtime_pointcloud.ply")
    _stream_processor.save_point_cloud(pcd_path)

    stats = _stream_processor.get_stream_stats()
    _stream_processor = None

    return jsonify({
        "status": "stopped",
        "stats": stats,
        "pointcloud_file": pcd_path,
    })


@api_bp.route("/stream/status", methods=["GET"])
def stream_status():
    sp = get_stream_processor()
    if sp is None:
        return jsonify({"status": "inactive"})

    stats = sp.get_stream_stats()
    latest = sp.get_latest_result()

    return jsonify({
        "status": "streaming" if stats["running"] else "inactive",
        "stats": stats,
        "latest_frame": latest,
    })


@api_bp.route("/stream/pointcloud", methods=["GET"])
def stream_pointcloud():
    sp = get_stream_processor()
    if sp is None:
        return jsonify({"error": "No active stream"}), 400

    pcd = sp.get_cumulative_point_cloud()

    task_id = str(uuid.uuid4())
    task_dir = os.path.join(OUTPUT_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    pcd_path = os.path.join(task_dir, "current_pointcloud.ply")
    import open3d as o3d
    o3d.io.write_point_cloud(pcd_path, pcd)

    return jsonify({
        "num_points": len(pcd.points),
        "ply_file": pcd_path,
    })


@api_bp.route("/dynamic/remove", methods=["POST"])
def remove_dynamic_objects():
    task_id = str(uuid.uuid4())

    depth_files = request.form.getlist("depth_files")
    cam_params = request.form.get("cam_params")
    image_files = request.files.getlist("images")

    if not depth_files or not cam_params:
        return jsonify({"error": "depth_files and cam_params are required"}), 400

    try:
        cam_params = json.loads(cam_params)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid cam_params JSON"}), 400

    depth_maps = [np.load(f) for f in depth_files]

    images = None
    if image_files and len(image_files) == len(depth_files):
        import cv2
        images = []
        for img_file in image_files:
            img = cv2.imdecode(
                np.frombuffer(img_file.read(), np.uint8),
                cv2.IMREAD_COLOR
            )
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            images.append(img)

    try:
        remover = get_dynamic_remover()
        static_depths = remover.filter_dynamic_from_depth(
            depth_maps, cam_params, images
        )

        task_dir = os.path.join(OUTPUT_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)

        results = []
        for idx, depth in enumerate(static_depths):
            depth_path = os.path.join(task_dir, f"static_depth_{idx}.npy")
            np.save(depth_path, depth)

            original_pts = np.sum(depth_maps[idx] > 0)
            static_pts = np.sum(depth > 0)
            removed_pts = original_pts - static_pts

            results.append({
                "view_idx": idx,
                "depth_file": depth_path,
                "original_points": int(original_pts),
                "static_points": int(static_pts),
                "removed_points": int(removed_pts),
                "removal_ratio": float(removed_pts / max(original_pts, 1)),
            })

        if images is not None:
            pcd = remover.filter_dynamic_point_cloud(
                None, depth_maps, cam_dicts=cam_params, images=images
            )
            if pcd is not None:
                pcd_path = os.path.join(task_dir, "static_pointcloud.ply")
                import open3d as o3d
                o3d.io.write_point_cloud(pcd_path, pcd)
            else:
                pcd_path = None
        else:
            pcd_path = None

        return jsonify({
            "task_id": task_id,
            "static_pointcloud": pcd_path,
            "view_results": results,
        })

    except Exception as e:
        logger.exception("Dynamic object removal failed")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/texture/map", methods=["POST"])
def texture_map_mesh():
    task_id = str(uuid.uuid4())

    mesh_file = request.form.get("mesh_file")
    if not mesh_file or not os.path.exists(mesh_file):
        return jsonify({"error": "Valid mesh_file is required"}), 400

    cam_params = request.form.get("cam_params")
    if cam_params is None:
        return jsonify({"error": "cam_params JSON is required"}), 400

    try:
        cam_params = json.loads(cam_params)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid cam_params JSON"}), 400

    image_files = request.files.getlist("images")
    image_paths = request.form.getlist("image_paths")

    images = []
    if image_files:
        import cv2
        for img_file in image_files:
            img = cv2.imdecode(
                np.frombuffer(img_file.read(), np.uint8),
                cv2.IMREAD_COLOR
            )
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            images.append(img)
    elif image_paths:
        import cv2
        for path in image_paths:
            if os.path.exists(path):
                img = cv2.imread(path)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                images.append(img)

    if not images:
        return jsonify({"error": "Images are required (upload or paths)"}), 400

    if len(images) != len(cam_params):
        return jsonify({"error": "Number of images must match cam_params"}), 400

    method = request.form.get("texture_method", "projective")

    try:
        import open3d as o3d
        mesh = o3d.io.read_triangle_mesh(mesh_file)

        if len(mesh.triangles) == 0:
            return jsonify({"error": "Mesh has no triangles"}), 400

        task_dir = os.path.join(OUTPUT_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)

        texturer = get_mesh_texturer()
        mesh_textured, atlas_path = texturer.texture(
            mesh, images, cam_params, output_dir=task_dir
        )

        output_path = os.path.join(task_dir, "textured_mesh")
        ply_path, obj_path = SurfaceReconstructor.save_mesh(mesh_textured, output_path)

        stats = {
            "num_vertices": len(mesh_textured.vertices),
            "num_triangles": len(mesh_textured.triangles),
            "has_vertex_colors": mesh_textured.has_vertex_colors(),
            "atlas_generated": atlas_path is not None,
        }

        return jsonify({
            "task_id": task_id,
            "texture_method": method,
            "mesh_stats": stats,
            "ply_file": ply_path,
            "obj_file": obj_path,
            "atlas_file": atlas_path,
        })

    except Exception as e:
        logger.exception("Texture mapping failed")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/reconstruct/full_pipeline", methods=["POST"])
def full_pipeline():
    task_id = str(uuid.uuid4())

    images = request.files.getlist("images")
    if len(images) < 2:
        return jsonify({"error": "At least 2 images required"}), 400

    cam_params = request.form.get("cam_params")
    if cam_params is None:
        return jsonify({"error": "cam_params JSON is required"}), 400

    try:
        cam_params = json.loads(cam_params)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid cam_params JSON"}), 400

    if len(cam_params) != len(images):
        return jsonify({"error": "Number of cam_params must match number of images"}), 400

    method = request.form.get("method", "poisson")
    depth_min = request.form.get("depth_min", type=float)
    depth_max = request.form.get("depth_max", type=float)
    complete_depth = request.form.get("complete_depth", "true").lower() == "true"
    adaptive_fusion = request.form.get("adaptive_fusion", "true").lower() == "true"
    remove_dynamic = request.form.get("remove_dynamic", "true").lower() == "true"
    fill_holes = request.form.get("fill_holes", "true").lower() == "true"
    apply_texture = request.form.get("apply_texture", "true").lower() == "true"

    task_dir = os.path.join(OUTPUT_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    image_paths = []
    for i, img in enumerate(images):
        img_path = os.path.join(task_dir, f"img_{i}.png")
        img.save(img_path)
        image_paths.append(img_path)

    def run_pipeline():
        try:
            import open3d as o3d
            import cv2

            with task_lock:
                tasks[task_id]["status"] = "estimating_depth"

            estimator = get_estimator()
            all_depths, all_probs, depth_values = estimator.estimate_depth_batch(
                image_paths, cam_params, depth_min, depth_max
            )

            depth_list = [all_depths[i] for i in sorted(all_depths.keys())]
            prob_list = [all_probs[i] for i in sorted(all_probs.keys())]

            for idx in sorted(all_depths.keys()):
                np.save(os.path.join(task_dir, f"depth_{idx}.npy"), all_depths[idx])
                np.save(os.path.join(task_dir, f"prob_{idx}.npy"), all_probs[idx])

            loaded_images = []
            for path in image_paths:
                img = cv2.imread(path)
                if img is not None:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    loaded_images.append(img)

            if remove_dynamic and len(depth_list) >= 2:
                with task_lock:
                    tasks[task_id]["status"] = "removing_dynamic"

                remover = get_dynamic_remover()
                depth_list = remover.filter_dynamic_from_depth(
                    depth_list, cam_params, loaded_images
                )

            if complete_depth:
                with task_lock:
                    tasks[task_id]["status"] = "completing_depth"

                completer = get_depth_completer()
                depth_list, _ = completer.complete_all_views(
                    depth_list, cam_params, images=loaded_images
                )

            with task_lock:
                tasks[task_id]["status"] = "fusing_point_cloud"

            if adaptive_fusion:
                fuser = get_adaptive_fuser()
                points, colors, texture_scores = fuser.fuse_depth_maps_adaptive(
                    depth_list, prob_list, cam_params, image_paths=image_paths
                )

                if points is None:
                    with task_lock:
                        tasks[task_id]["status"] = "failed"
                        tasks[task_id]["error"] = "Fusion produced no points"
                    return

                if texture_scores is not None:
                    pcd = fuser.adaptive_voxel_downsample(points, colors, texture_scores)
                else:
                    pcd = o3d.geometry.PointCloud()
                    pcd.points = o3d.utility.Vector3dVector(points)
                    if colors is not None:
                        pcd.colors = o3d.utility.Vector3dVector(colors)
                    pcd = pcd.voxel_down_sample(fuser.base_voxel_size)

                pcd = fuser.filter_point_cloud_adaptive(pcd)
                pcd = fuser.estimate_normals(pcd)
            else:
                fuser = get_fuser()
                points, colors = fuser.fuse_depth_maps(
                    depth_list, prob_list, cam_params, image_paths=image_paths
                )

                if points is None:
                    with task_lock:
                        tasks[task_id]["status"] = "failed"
                        tasks[task_id]["error"] = "Fusion produced no points"
                    return

                pcd = fuser.filter_point_cloud(points, colors)
                pcd = fuser.estimate_normals(
                    np.asarray(pcd.points),
                    np.asarray(pcd.colors) if pcd.has_colors() else None,
                )

            ply_path = os.path.join(task_dir, "point_cloud.ply")
            o3d.io.write_point_cloud(ply_path, pcd)

            with task_lock:
                tasks[task_id]["status"] = "reconstructing_surface"
                tasks[task_id]["point_cloud_file"] = ply_path
                tasks[task_id]["num_points"] = len(pcd.points)

            reconstructor = get_enhanced_reconstructor()
            mesh, fill_stats = reconstructor.reconstruct_with_hole_handling(
                pcd, method=method, fill_holes=fill_holes,
            )

            if mesh is None:
                with task_lock:
                    tasks[task_id]["status"] = "failed"
                    tasks[task_id]["error"] = "Reconstruction produced empty mesh"
                return

            if apply_texture:
                with task_lock:
                    tasks[task_id]["status"] = "applying_texture"

                texturer = get_mesh_texturer()
                mesh, atlas_path = texturer.texture(
                    mesh, loaded_images, cam_params, output_dir=task_dir
                )
            else:
                atlas_path = None

            output_path = os.path.join(task_dir, "mesh")
            ply_mesh, obj_mesh = SurfaceReconstructor.save_mesh(mesh, output_path)
            stats = reconstructor.base_reconstructor.compute_mesh_quality(mesh)

            with task_lock:
                tasks[task_id]["status"] = "completed"
                tasks[task_id]["mesh_stats"] = stats
                tasks[task_id]["mesh_ply"] = ply_mesh
                tasks[task_id]["mesh_obj"] = obj_mesh
                tasks[task_id]["fill_stats"] = fill_stats
                tasks[task_id]["atlas_file"] = atlas_path

        except Exception as e:
            logger.exception("Full pipeline failed")
            with task_lock:
                tasks[task_id]["status"] = "failed"
                tasks[task_id]["error"] = str(e)

    with task_lock:
        tasks[task_id] = {"status": "queued", "type": "full_pipeline"}

    thread = threading.Thread(target=run_pipeline)
    thread.start()

    return jsonify({"task_id": task_id, "status": "queued"})
