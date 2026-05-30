import streamlit as st
import cv2
import numpy as np
from hand_detector import HandDetector
from gesture_classifier import GestureClassifier
from dynamic_gesture import DynamicGestureRecognizer, TORCH_AVAILABLE
from gesture_commands import GestureCommandMapper, create_demo_mapper, DEFAULT_COMMANDS
from rehab_evaluation import (
    FingerFlexibilityEvaluator, RehabTrainingSession,
    REHAB_EXERCISES, FINGER_NAMES, NORMAL_RANGE
)
from utils import (
    draw_gesture_info, draw_fps, draw_finger_states, draw_info_panel,
    draw_trajectory, draw_3d_pose_info, draw_rehab_progress,
    draw_command_history, draw_rehab_training_session
)

WEBRTC_AVAILABLE = False
try:
    import av
    from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode
    WEBRTC_AVAILABLE = True
except (ImportError, OSError):
    pass


st.set_page_config(
    page_title="手部关键点检测与手势识别 - 完整版",
    page_icon="🖐",
    layout="wide",
)


if WEBRTC_AVAILABLE:
    class HandGestureProcessor(VideoProcessorBase):
        def __init__(self):
            self.detector = None
            self.classifier = None
            self.dynamic_recognizers = {}
            self.command_mapper = None
            self.rehab_evaluator = None
            self.rehab_session = None

            self.max_hands = 2
            self.det_confidence = 0.7
            self.show_landmarks = True
            self.show_info = True
            self.show_fingers = True
            self.show_trajectory = True
            self.show_3d_info = True
            self.show_commands = True
            self.show_rehab = True
            self.enable_dynamic = True
            self.adaptive_window = True
            self.use_tracking = True
            self.enable_command = True

        def _init_models(self):
            if self.detector is None:
                self.detector = HandDetector(
                    max_num_hands=self.max_hands,
                    min_detection_confidence=self.det_confidence,
                )
            if self.classifier is None:
                self.classifier = GestureClassifier()
            if self.command_mapper is None and self.enable_command:
                self.command_mapper = create_demo_mapper()
            if self.rehab_evaluator is None and self.show_rehab:
                self.rehab_evaluator = FingerFlexibilityEvaluator()

        def recv(self, frame):
            self._init_models()
            img = frame.to_ndarray(format="bgr24")

            if self.detector.max_num_hands != self.max_hands:
                self.detector.release()
                self.detector = HandDetector(
                    max_num_hands=self.max_hands,
                    min_detection_confidence=self.det_confidence,
                )

            img, hands = self.detector.find_hands(
                img, draw=self.show_landmarks, use_tracking=self.use_tracking, compute_3d=True
            )

            static_gesture = "无"
            dynamic_gesture = "无"
            window_info = None
            active_hand_ids = set()

            for hand_info in hands:
                hand_id = hand_info["hand_id"]
                active_hand_ids.add(hand_id)
                gesture_name, confidence = self.classifier.classify(hand_info, self.detector)
                gesture_label = self.classifier.get_label(gesture_name)
                static_gesture = gesture_label

                if self.enable_command and self.command_mapper:
                    self.command_mapper.process_static_gesture(gesture_name, confidence)

                dynamic_label = None
                dynamic_conf = None
                if self.enable_dynamic:
                    if hand_id not in self.dynamic_recognizers:
                        self.dynamic_recognizers[hand_id] = DynamicGestureRecognizer(
                            base_sequence_length=30,
                            use_lstm=False,
                            adaptive_window=self.adaptive_window
                        )
                    recognizer = self.dynamic_recognizers[hand_id]
                    lm_array = self.detector.get_landmark_array(hand_info)
                    recognizer.update(lm_array, hand_info)
                    dyn_class, dyn_conf = recognizer.predict()
                    window_info = recognizer.get_window_info()

                    if self.enable_command and self.command_mapper and dyn_class != 6:
                        self.command_mapper.process_dynamic_gesture(dyn_class, dyn_conf)

                    if dyn_class != 6:
                        dynamic_label = DynamicGestureRecognizer.get_label(dyn_class)
                        dynamic_conf = dyn_conf
                        dynamic_gesture = dynamic_label

                if self.show_info:
                    draw_gesture_info(
                        img, gesture_name, gesture_label, confidence,
                        hand_info, dynamic_label, dynamic_conf,
                    )

                if self.show_fingers:
                    fingers = self.detector.get_finger_states(hand_info)
                    draw_finger_states(img, fingers, hand_info)

                if self.show_trajectory:
                    draw_trajectory(img, hand_info)

                if self.show_3d_info and "pose_3d" in hand_info:
                    draw_3d_pose_info(img, hand_info)

                if self.show_rehab and self.rehab_evaluator:
                    self.rehab_evaluator.update(hand_info.get("pose_3d"))

                if self.rehab_session and self.rehab_session.is_running:
                    self.rehab_session.update(hand_info.get("pose_3d"))

            for hid in list(self.dynamic_recognizers.keys()):
                if hid not in active_hand_ids:
                    del self.dynamic_recognizers[hid]

            if self.show_info:
                draw_info_panel(
                    img, len(hands), static_gesture, dynamic_gesture,
                    self.detector.fps, window_info
                )

            if self.show_rehab:
                draw_rehab_progress(img, self.rehab_evaluator)

            if self.show_commands and self.command_mapper:
                draw_command_history(img, self.command_mapper)

            if self.rehab_session:
                draw_rehab_training_session(img, self.rehab_session)

            draw_fps(img, self.detector.fps)
            return av.VideoFrame.from_ndarray(img, format="bgr24")

        def start_rehab_session(self, exercise_type):
            self.rehab_session = RehabTrainingSession(exercise_type)
            return self.rehab_session.start()

        def stop_rehab_session(self):
            if self.rehab_session:
                return self.rehab_session.stop()
            return None

        def reset_all(self):
            for recognizer in self.dynamic_recognizers.values():
                recognizer.reset()
            if self.command_mapper:
                self.command_mapper.reset()
            if self.rehab_evaluator:
                self.rehab_evaluator.reset()
            self.rehab_session = None


def main():
    st.title("🖐 手部关键点检测与手势识别系统 (完整版)")
    st.markdown("---")

    col1, col2 = st.columns([3, 1])

    with col2:
        st.subheader("⚙️ 参数设置")
        max_hands = st.selectbox("最大手部数量", [1, 2], index=1)
        det_confidence = st.slider("检测置信度", 0.3, 1.0, 0.7, 0.05)

        st.subheader("🎨 显示选项")
        show_landmarks = st.checkbox("显示关键点", value=True)
        show_info = st.checkbox("显示手势信息", value=True)
        show_fingers = st.checkbox("显示手指状态", value=True)
        show_trajectory = st.checkbox("显示运动轨迹", value=True)
        show_3d_info = st.checkbox("显示3D姿态", value=True)

        st.subheader("🧠 高级功能")
        enable_dynamic = st.checkbox("启用动态手势", value=True)
        adaptive_window = st.checkbox("动态时序窗口", value=True)
        use_tracking = st.checkbox("手部ID追踪", value=True)
        enable_command = st.checkbox("手势指令映射", value=True)
        show_rehab = st.checkbox("康复评估模式", value=True)
        show_commands = st.checkbox("显示指令历史", value=True)

        st.markdown("---")

        st.subheader("🏥 康复训练")
        exercise_options = [(k, v["name"]) for k, v in REHAB_EXERCISES.items()]
        selected_exercise = st.selectbox(
            "选择训练项目",
            options=[k for k, _ in exercise_options],
            format_func=lambda x: dict(exercise_options)[x]
        )

        col_start, col_stop = st.columns(2)
        with col_start:
            start_training = st.button("� 开始训练", use_container_width=True)
        with col_stop:
            stop_training = st.button("⏹️ 结束训练", use_container_width=True)

        st.markdown("---")
        st.subheader("📊 功能概览")
        torch_status = "✅ LSTM模型" if TORCH_AVAILABLE else "🔧 规则引擎(更快)"
        webrtc_status = "✅ 已加载" if WEBRTC_AVAILABLE else "⚠️ 未加载"
        st.markdown(f"""
        - **检测**: MediaPipe Hands (21关键点)
        - **3D姿态**: Yaw/Pitch + 手指角度 + 深度
        - **指令映射**: 12种手势 → 可自定义动作
        - **康复评估**: 5种训练 + 灵活度评分
        - **动态识别**: {torch_status}
        - **WebRTC**: {webrtc_status}
        """)

        with st.expander("📖 手势指令说明"):
            static_cmds, dynamic_cmds = [], []
            for key, cmd in DEFAULT_COMMANDS.items():
                if cmd.get("is_dynamic", False):
                    dynamic_cmds.append(f"- {cmd['name']} → `{cmd['action']}`")
                else:
                    static_cmds.append(f"- {cmd['name']} → `{cmd['action']}`")
            st.markdown("**静态手势:**")
            st.markdown("\n".join(static_cmds))
            st.markdown("**动态手势:**")
            st.markdown("\n".join(dynamic_cmds))

        with st.expander("🏋️ 康复训练项目"):
            for key, ex in REHAB_EXERCISES.items():
                st.markdown(f"""
                **{ex['name']}** ({ex['difficulty']})
                - {ex['description']}
                - 目标: {ex['target_reps']}次 / {ex['duration']}秒
                """)

    with col1:
        if not WEBRTC_AVAILABLE:
            st.warning("⚠️ `streamlit-webrtc` 未安装，WebRTC 实时模式不可用。")
            st.info("请运行以下命令安装依赖：\n```\npip install streamlit-webrtc av\n```")
            st.markdown("---")
            st.subheader("🚀 替代方案：使用 OpenCV 独立模式")
            st.code("python main_opencv.py", language="bash")
            st.markdown("**OpenCV模式特性：**")
            st.markdown("""
            - ✅ 双手ID追踪 + 颜色区分
            - ✅ 动态时序窗口 (速度自适应)
            - ✅ 3D姿态重建 + 深度信息
            - ✅ 手势指令映射 (可自定义回调)
            - ✅ 康复训练评估 (5种训练项目)
            - ✅ 运动轨迹绘制
            - ✅ FPS 30+ 高性能
            """)
        else:
            ctx = webrtc_streamer(
                key="hand-gesture-full",
                mode=WebRtcMode.SENDRECV,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
                media_stream_constraints={
                    "video": {"width": 800, "height": 600, "frameRate": 30},
                    "audio": False,
                },
                video_processor_factory=HandGestureProcessor,
                async_processing=True,
            )

            if ctx.video_processor:
                processor = ctx.video_processor
                processor.max_hands = max_hands
                processor.det_confidence = det_confidence
                processor.show_landmarks = show_landmarks
                processor.show_info = show_info
                processor.show_fingers = show_fingers
                processor.show_trajectory = show_trajectory
                processor.show_3d_info = show_3d_info
                processor.show_commands = show_commands
                processor.show_rehab = show_rehab
                processor.enable_dynamic = enable_dynamic
                processor.adaptive_window = adaptive_window
                processor.use_tracking = use_tracking
                processor.enable_command = enable_command

                if start_training:
                    processor.start_rehab_session(selected_exercise)
                    st.success(f"开始训练: {REHAB_EXERCISES[selected_exercise]['name']}")

                if stop_training:
                    report = processor.stop_rehab_session()
                    if report:
                        st.success(f"训练完成！得分: {report['overall_score']:.1f}/100")
                        with st.expander("📋 查看完整报告"):
                            st.json(report)

                if st.button("🔄 重置所有", use_container_width=True):
                    processor.reset_all()
                    st.info("已重置")

    st.markdown("---")
    st.subheader("📈 实时数据面板")

    tab1, tab2, tab3 = st.tabs(["3D姿态信息", "指令映射", "康复评估"])

    with tab1:
        st.markdown("**关键点说明:**")
        cols = st.columns(4)
        for i, name in enumerate([
            "手腕", "拇指CMC", "拇指MCP", "拇指IP", "拇指指尖",
            "食指MCP", "食指PIP", "食指DIP", "食指指尖",
            "中指MCP", "中指PIP", "中指DIP", "中指指尖",
            "无名指MCP", "无名指PIP", "无名指DIP", "无名指指尖",
            "小指MCP", "小指PIP", "小指DIP", "小指指尖",
        ][:20]):
            with cols[i % 4]:
                st.caption(f"{i}: {name}")

        st.markdown("**手指活动范围参考:**")
        cols = st.columns(5)
        for i, finger in enumerate(FINGER_NAMES):
            with cols[i]:
                st.metric(
                    finger,
                    f"{NORMAL_RANGE[finger]['target']}°",
                    f"范围: {NORMAL_RANGE[finger]['min']}-{NORMAL_RANGE[finger]['max']}°"
                )

    with tab2:
        st.markdown("**如何自定义指令:**")
        st.code("""
from gesture_commands import GestureCommandMapper

mapper = GestureCommandMapper()

# 注册自定义动作回调
def my_callback(gesture_name):
    print(f"手势触发: {gesture_name}")
    # 在这里执行你的自定义逻辑

mapper.register_callback("like", my_callback)
mapper.register_callback("next", my_callback)
""", language="python")

        st.markdown("**可用的action名称:**")
        actions = set(cmd["action"] for cmd in DEFAULT_COMMANDS.values())
        st.write(", ".join([f"`{a}`" for a in actions]))

    with tab3:
        st.markdown("**灵活度评分说明:**")
        cols = st.columns(4)
        cols[0].metric("80-100分", "优秀", "正常水平")
        cols[1].metric("60-80分", "良好", "继续保持")
        cols[2].metric("40-60分", "一般", "需要训练")
        cols[3].metric("0-40分", "需加强", "建议就医")

        st.markdown("**评分公式:**")
        st.latex(r"\text{总分} = 0.7 \times \text{活动范围} + 0.3 \times \text{重复次数}")

if __name__ == "__main__":
    main()
