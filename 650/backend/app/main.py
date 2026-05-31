import asyncio
import json
import threading
import time
from typing import Dict, Optional
from collections import deque

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .config import settings, ACTION_CLASSES
from .schemas import (
    MessageType, StartMessage, StopMessage, PauseMessage, ResumeMessage,
    ConfigMessage, RecognitionResult, TemporalResult, StatusUpdate,
    ErrorMessage, Prediction, StatusType, SourceType, ModelType,
    ActionPrediction, PredictionItem, WeaklyLabelMessage, PseudoGroundTruth
)
from ..services.websocket_manager import ConnectionManager
from ..services.video_capture import VideoCapture
from ..services.adaptive_frame_rate import AdaptiveFrameProcessor
from ..services.inference import InferenceService
from ..services.precision_temporal_locator import PrecisionTemporalLocator
from ..services.weakly_supervised_localizer import WeaklySupervisedLocalizer
from ..services.action_predictor import ActionPredictionEngine
from ..models.model_loader import get_model


app = FastAPI(title=settings.app_name, version=settings.version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()


class RecognitionSession:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.status: StatusType = StatusType.IDLE
        self.config: Optional[StartMessage] = None

        self.video_capture = VideoCapture()
        self.frame_processor = AdaptiveFrameProcessor(
            target_size=(settings.frame_size, settings.frame_size),
            min_fps=8,
            max_fps=60,
            base_fps=16,
            window_size=60
        )
        self.temporal_locator = PrecisionTemporalLocator(
            num_classes=len(ACTION_CLASSES),
            min_duration=settings.action_min_duration,
            max_duration=10.0,
            peak_min_distance=15,
            peak_min_prominence=0.15,
            rising_edge_threshold=0.25,
            falling_edge_threshold=0.25,
            smooth_sigma=2.0,
            history_size=500
        )
        self.weakly_supervised_localizer = WeaklySupervisedLocalizer(
            num_classes=len(ACTION_CLASSES),
            feature_dim=512,
            top_k_instances=3,
            min_segment_length=5,
            history_size=500
        )
        self.action_predictor = ActionPredictionEngine(
            num_classes=len(ACTION_CLASSES),
            history_size=50,
            prediction_horizon=10,
            model_type="lstm",
            device=settings.device,
            multi_label=True
        )
        self.inference_service: Optional[InferenceService] = None

        self.frame_index: int = 0
        self.start_time: float = 0.0

        self._capture_thread: Optional[threading.Thread] = None
        self._inference_thread: Optional[threading.Thread] = None
        self._prediction_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._paused: bool = False
        self._pause_event = threading.Event()

        self._recent_predictions = deque(maxlen=10)
        self._last_detection_time: float = 0.0
        self._last_prediction_time: float = 0.0
        self._current_fps: int = 16
        self._motion_level: float = 0.0

        self._weakly_labels: Dict[int, int] = {}

    async def start(self, config: StartMessage):
        self.config = config
        self.status = StatusType.CONNECTING
        await self._send_status(StatusType.CONNECTING, "正在初始化模型...")

        try:
            model = get_model(
                model_type=config.model_type.value,
                device=settings.device,
                class_names=ACTION_CLASSES,
                confidence_threshold=config.confidence_threshold,
                fp16=settings.fp16,
                multi_label=True
            )

            self.inference_service = InferenceService(
                model=model,
                num_classes=len(ACTION_CLASSES),
                confidence_threshold=config.confidence_threshold
            )
            self.inference_service.start()

        except Exception as e:
            await self._send_error(1001, f"模型加载失败: {str(e)}")
            self.status = StatusType.ERROR
            return

        await self._send_status(StatusType.CONNECTING, "正在打开视频源...")

        try:
            source_type = config.source.value
            camera_index = config.camera_index if config.source == SourceType.CAMERA else 0
            file_path = config.file_path if config.source == SourceType.FILE else None

            self.video_capture.start(
                source_type=source_type,
                camera_index=camera_index,
                file_path=file_path,
                fps=config.fps
            )

        except Exception as e:
            await self._send_error(1002, f"视频源打开失败: {str(e)}")
            self.status = StatusType.ERROR
            return

        self._running = True
        self._paused = False
        self._pause_event.set()
        self.frame_index = 0
        self.start_time = time.time()
        self._last_detection_time = 0.0
        self._last_prediction_time = 0.0

        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._prediction_thread = threading.Thread(target=self._prediction_loop, daemon=True)

        self._capture_thread.start()
        self._inference_thread.start()
        self._prediction_thread.start()

        self.status = StatusType.RUNNING
        await self._send_status(StatusType.RUNNING, "识别已开始")

    async def stop(self):
        self._running = False
        self._pause_event.set()

        if self.video_capture:
            self.video_capture.stop()

        if self.inference_service:
            self.inference_service.stop()

        for thread_name in ['_capture_thread', '_inference_thread', '_prediction_thread']:
            thread = getattr(self, thread_name, None)
            if thread and thread.is_alive():
                thread.join(timeout=2.0)

        self.frame_processor.clear_buffer()
        self.temporal_locator.clear_history()
        self.weakly_supervised_localizer.clear_history()
        self.action_predictor.clear_history()

        self.status = StatusType.IDLE
        await self._send_status(StatusType.IDLE, "识别已停止")

    async def pause(self):
        if self.status == StatusType.RUNNING:
            self._paused = True
            self._pause_event.clear()
            self.status = StatusType.PAUSED
            await self._send_status(StatusType.PAUSED, "识别已暂停")

    async def resume(self):
        if self.status == StatusType.PAUSED:
            self._paused = False
            self._pause_event.set()
            self.status = StatusType.RUNNING
            await self._send_status(StatusType.RUNNING, "识别已恢复")

    async def update_config(self, config: ConfigMessage):
        if config.confidence_threshold is not None:
            if self.inference_service:
                self.inference_service.confidence_threshold = config.confidence_threshold

        await self._send_status(self.status, "配置已更新")

    async def add_weakly_label(self, label_msg: WeaklyLabelMessage):
        try:
            features = np.zeros(512, dtype=np.float32)
            confidence_curve = np.zeros(len(ACTION_CLASSES), dtype=np.float32)

            self.weakly_supervised_localizer.update_with_video_label(
                features=features,
                confidence_curve=confidence_curve,
                video_level_label=label_msg.video_level_label,
                timestamp=label_msg.timestamp
            )

            await self._send_status(self.status, f"已添加弱监督标签: {ACTION_CLASSES.get(label_msg.video_level_label, '未知')}")

        except Exception as e:
            await self._send_error(1005, f"添加弱监督标签失败: {str(e)}")

    async def generate_pseudo_ground_truth(self):
        try:
            labels = list(self._weakly_labels.keys())
            if not labels:
                labels = list(range(len(ACTION_CLASSES)))

            pseudo_gt = self.weakly_supervised_localizer.generate_pseudo_ground_truth(labels)

            msg = PseudoGroundTruth(
                type=MessageType.PSEUDO_GT,
                num_segments=pseudo_gt['num_segments'],
                segments=pseudo_gt['segments'],
                video_level_labels=pseudo_gt['video_level_labels'],
                method=pseudo_gt['method']
            )
            await manager.send_to_client(self.client_id, msg.model_dump_json())

        except Exception as e:
            await self._send_error(1006, f"生成伪标签失败: {str(e)}")

    def _capture_loop(self):
        while self._running:
            try:
                self._pause_event.wait()
                if not self._running:
                    break

                frame = self.video_capture.read_frame()
                if frame is None:
                    if self.video_capture.source_type == "file":
                        break
                    time.sleep(0.01)
                    continue

                timestamp = time.time() - self.start_time

                sampled = self.frame_processor.add_frame(frame, timestamp)

                if sampled:
                    self._current_fps = self.frame_processor.get_current_fps()
                    self._motion_level = self.frame_processor.get_motion_level()

                self.frame_index += 1

                if self.frame_processor.is_ready(num_frames=8):
                    clips = self.frame_processor.sliding_window_sample(
                        step=8,
                        num_frames=8,
                        sampling_rate=settings.sampling_rate
                    )
                    for clip, timestamps in clips:
                        clip_timestamp = timestamps[-1] if timestamps else timestamp
                        self.inference_service.submit_clip(clip, [clip_timestamp])

                time.sleep(1.0 / max(self._current_fps, 8))

            except Exception as e:
                print(f"采集线程错误: {e}")
                time.sleep(0.1)

    def _inference_loop(self):
        while self._running:
            try:
                self._pause_event.wait()
                if not self._running:
                    break

                result = self.inference_service.get_result(timeout=0.1)
                if result is None:
                    continue

                predictions = result["prediction"]
                all_probs = result["all_probabilities"]
                timestamps = result["timestamps"]
                latency = result["latency"]

                clip_timestamp = timestamps[-1] if timestamps else 0.0

                preds = []
                for action, conf, idx in predictions:
                    preds.append(Prediction(
                        action=action,
                        confidence=float(conf)
                    ))

                if len(all_probs) == len(ACTION_CLASSES):
                    self.temporal_locator.update(all_probs, clip_timestamp)

                    if preds:
                        top_action_idx = predictions[0][2] if predictions else 0
                        top_action_conf = predictions[0][1] if predictions else 0.0
                        self.action_predictor.update_history(
                            action_idx=top_action_idx,
                            confidence=top_action_conf,
                            timestamp=clip_timestamp,
                            all_confidences=all_probs
                        )

                    current_time = time.time()
                    if current_time - self._last_detection_time >= 0.1:
                        actions = self.temporal_locator.detect_actions()
                        for action_data in actions:
                            action_idx = int(action_data["action"])
                            action_name = ACTION_CLASSES.get(action_idx, "其他")
                            action_data["action"] = action_name
                            asyncio.run_coroutine_threadsafe(
                                self._send_temporal_result(action_data),
                                asyncio.get_event_loop()
                            )
                        self._last_detection_time = current_time

                if preds:
                    self._recent_predictions.append((preds[0], clip_timestamp))

                stats = self.inference_service.get_stats()
                inference_fps = stats.get("current_fps", 0.0)
                effective_fps = (inference_fps + self._current_fps) / 2

                asyncio.run_coroutine_threadsafe(
                    self._send_result(preds, clip_timestamp, effective_fps, latency),
                    asyncio.get_event_loop()
                )

            except Exception as e:
                print(f"推理线程错误: {e}")
                time.sleep(0.1)

    def _prediction_loop(self):
        while self._running:
            try:
                self._pause_event.wait()
                if not self._running:
                    break

                current_time = time.time()
                if current_time - self._last_prediction_time >= 0.5:
                    if self.action_predictor.is_ready():
                        predictions = self.action_predictor.predict_next_action()
                        multi_step = self.action_predictor.predict_multi_step(steps=5)
                        transition_matrix = self.action_predictor.get_action_transition_matrix()

                        pred_items = []
                        if predictions:
                            for pred in predictions:
                                action_name = ACTION_CLASSES.get(pred['class_idx'], "其他")
                                pred_items.append(PredictionItem(
                                    class_idx=pred['class_idx'],
                                    action=action_name,
                                    confidence=pred['confidence'],
                                    prediction_step=pred['prediction_step']
                                ))

                        multi_step_items = []
                        if multi_step:
                            for step_preds in multi_step:
                                step_items = []
                                for pred in step_preds:
                                    action_name = ACTION_CLASSES.get(pred['class_idx'], "其他")
                                    step_items.append(PredictionItem(
                                        class_idx=pred['class_idx'],
                                        action=action_name,
                                        confidence=pred['confidence'],
                                        prediction_step=pred['prediction_step']
                                    ))
                                multi_step_items.append(step_items)

                        pred_msg = ActionPrediction(
                            type=MessageType.PREDICTION,
                            predictions=pred_items,
                            multi_step_predictions=multi_step_items if multi_step_items else None,
                            transition_matrix=transition_matrix.tolist() if transition_matrix is not None else None,
                            prediction_confidence=self.action_predictor.get_prediction_confidence(),
                            is_ready=True
                        )
                        asyncio.run_coroutine_threadsafe(
                            manager.send_to_client(self.client_id, pred_msg.model_dump_json()),
                            asyncio.get_event_loop()
                        )

                    self._last_prediction_time = current_time

                time.sleep(0.1)

            except Exception as e:
                print(f"预测线程错误: {e}")
                time.sleep(0.1)

    async def _send_result(self, predictions: list, timestamp: float, fps: float, latency: float):
        result = RecognitionResult(
            type=MessageType.RESULT,
            timestamp=timestamp,
            frame_index=self.frame_index,
            predictions=predictions,
            fps=fps,
            latency=latency
        )
        await manager.send_to_client(self.client_id, result.model_dump_json())

    async def _send_temporal_result(self, action_data: dict):
        result = TemporalResult(
            type=MessageType.TEMPORAL,
            action=str(action_data["action"]),
            start_time=float(action_data["start_time"]),
            end_time=float(action_data["end_time"]),
            duration=float(action_data["duration"]),
            avg_confidence=float(action_data["avg_confidence"])
        )
        await manager.send_to_client(self.client_id, result.model_dump_json())

    async def _send_status(self, status: StatusType, message: str = None):
        update = StatusUpdate(
            type=MessageType.STATUS,
            status=status,
            message=message
        )
        await manager.send_to_client(self.client_id, update.model_dump_json())

    async def _send_error(self, error_code: int, error_message: str):
        error = ErrorMessage(
            type=MessageType.ERROR,
            error_code=error_code,
            error_message=error_message
        )
        await manager.send_to_client(self.client_id, error.model_dump_json())

    def cleanup(self):
        asyncio.run_coroutine_threadsafe(self.stop(), asyncio.get_event_loop())


sessions: Dict[str, RecognitionSession] = {}


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    if len(sessions) >= settings.max_clients:
        await websocket.close(code=1008, reason="已达到最大客户端连接数")
        return

    await manager.connect(websocket, client_id)
    session = RecognitionSession(client_id)
    sessions[client_id] = session

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == MessageType.START:
                    config = StartMessage(**message)
                    await session.start(config)

                elif msg_type == MessageType.STOP:
                    await session.stop()

                elif msg_type == MessageType.PAUSE:
                    await session.pause()

                elif msg_type == MessageType.RESUME:
                    await session.resume()

                elif msg_type == MessageType.CONFIG:
                    config = ConfigMessage(**message)
                    await session.update_config(config)

                elif msg_type == MessageType.WEAKLY_LABEL:
                    label_msg = WeaklyLabelMessage(**message)
                    await session.add_weakly_label(label_msg)

                elif msg_type == "generate_pseudo_gt":
                    await session.generate_pseudo_ground_truth()

                else:
                    await session._send_error(1000, f"未知消息类型: {msg_type}")

            except ValidationError as e:
                await session._send_error(1003, f"消息格式错误: {str(e)}")

            except Exception as e:
                await session._send_error(1004, f"处理错误: {str(e)}")

    except WebSocketDisconnect:
        pass

    finally:
        session.cleanup()
        manager.disconnect(client_id)
        del sessions[client_id]


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.version,
        "active_clients": len(sessions),
        "features": {
            "adaptive_frame_rate": True,
            "peak_detection": True,
            "multi_label_classification": True,
            "lightweight_models": True,
            "weakly_supervised_localization": True,
            "action_prediction": True
        }
    }


@app.get("/models")
async def list_models():
    return {
        "models": [
            {
                "type": "timesformer",
                "name": "TimeSformer",
                "description": "Facebook AI时空分离注意力模型",
                "multi_label_support": True,
                "size": "Large"
            },
            {
                "type": "videomae",
                "name": "VideoMAE",
                "description": "字节跳动掩码自编码器视频模型",
                "multi_label_support": True,
                "size": "Large"
            },
            {
                "type": "mobilenetv2",
                "name": "MobileNetV2-TSM",
                "description": "轻量级模型+时序偏移模块，移动端实时识别",
                "multi_label_support": True,
                "size": "Small (~3.5MB)",
                "flops": "~0.3 GFLOPs"
            },
            {
                "type": "shufflenetv2",
                "name": "ShuffleNetV2-TSM",
                "description": "高效轻量级模型+时序偏移，边缘设备优化",
                "multi_label_support": True,
                "size": "Extra Small (~2.3MB)",
                "flops": "~0.15 GFLOPs"
            },
            {
                "type": "lightweight",
                "name": "Lightweight (MobileNetV2)",
                "description": "轻量级模型快捷入口",
                "multi_label_support": True,
                "mobile_optimized": True
            }
        ],
        "action_classes": ACTION_CLASSES,
        "temporal_detection": {
            "algorithm": "peak_detection_boundary_regression",
            "min_duration": settings.action_min_duration,
            "description": "峰值检测+边界回归，精准定位动作起始/结束时间"
        },
        "frame_rate": {
            "mode": "adaptive",
            "description": "基于光流的动态帧率调整，快动作时提高采样率",
            "range": "8-60 FPS"
        },
        "classification": {
            "mode": "multi_label",
            "description": "Sigmoid多标签损失，支持同时识别多个动作，解除竞争压制"
        },
        "weakly_supervised": {
            "method": "CAM + MIL",
            "description": "仅使用视频级标签学习时序定位，无需帧级标注",
            "features": ["Class Activation Mapping", "Multiple Instance Learning", "Pseudo Label Generation"]
        },
        "action_prediction": {
            "models": ["LSTM", "Transformer", "TCN"],
            "prediction_horizon": "1-10 steps",
            "description": "基于历史动作序列预测未来动作"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
