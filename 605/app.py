import logging
import numpy as np
import threading
from flask import Flask
from flask_socketio import SocketIO, emit
from config import FLASK_CONFIG
from api.routes import api_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = FLASK_CONFIG["max_content_length"]
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    socketio.init_app(app)

    _register_socket_events()

    logger.info("Flask app created, API at /api/v1, WebSocket enabled")
    return app


def _register_socket_events():
    @socketio.on("connect")
    def handle_connect():
        logger.info("WebSocket client connected")
        emit("connected", {"message": "MVSNet 3D Reconstruction Server"})

    @socketio.on("disconnect")
    def handle_disconnect():
        logger.info("WebSocket client disconnected")

    @socketio.on("stream_start")
    def handle_stream_start(data):
        from modules.realtime import VideoStreamProcessor
        from api.routes import get_estimator, _stream_processor

        video_source = data.get("video_source", 0)
        frame_skip = data.get("frame_skip", 2)
        voxel_size = data.get("voxel_size", 0.01)

        estimator = get_estimator()

        import api.routes as routes
        routes._stream_processor = VideoStreamProcessor(
            depth_estimator=estimator,
            frame_skip=frame_skip,
            voxel_size=voxel_size,
        )

        def on_frame_result(result):
            try:
                emit("stream_frame", result)
            except Exception:
                pass

        routes._stream_processor.start_stream(video_source)

        def poll_results():
            import api.routes as r
            while r._stream_processor and r._stream_processor._running:
                result = r._stream_processor.get_latest_result()
                if result:
                    try:
                        socketio.emit("stream_frame", result)
                    except Exception:
                        pass
                socketio.sleep(0.1)

        socketio.start_background_task(poll_results)

        emit("stream_started", {"status": "ok", "source": str(video_source)})

    @socketio.on("stream_stop")
    def handle_stream_stop():
        import api.routes as routes
        if routes._stream_processor:
            routes._stream_processor.stop_stream()
            stats = routes._stream_processor.get_stream_stats()
            emit("stream_stopped", {"stats": stats})
            routes._stream_processor = None

    @socketio.on("stream_request_pointcloud")
    def handle_request_pointcloud():
        import api.routes as routes
        if routes._stream_processor:
            pcd = routes._stream_processor.get_cumulative_point_cloud()
            points = np.asarray(pcd.points)
            colors = np.asarray(pcd.colors) if pcd.has_colors() else None

            result = {
                "num_points": len(points),
                "bbox": {
                    "min": points.min(axis=0).tolist(),
                    "max": points.max(axis=0).tolist(),
                },
            }

            if colors is not None:
                result["has_colors"] = True

            emit("pointcloud_info", result)

    @socketio.on("task_subscribe")
    def handle_task_subscribe(data):
        task_id = data.get("task_id")
        if not task_id:
            return

        import api.routes as routes

        def poll_task():
            prev_status = None
            while True:
                with routes.task_lock:
                    task = routes.tasks.get(task_id)
                if task and task.get("status") != prev_status:
                    prev_status = task.get("status")
                    socketio.emit("task_update", {"task_id": task_id, **task})
                    if prev_status in ("completed", "failed"):
                        break
                socketio.sleep(0.5)

        socketio.start_background_task(poll_task)


if __name__ == "__main__":
    app = create_app()
    socketio.run(
        app,
        host=FLASK_CONFIG["host"],
        port=FLASK_CONFIG["port"],
        debug=FLASK_CONFIG["debug"],
    )
