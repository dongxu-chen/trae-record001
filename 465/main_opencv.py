import cv2
import sys
from hand_detector import HandDetector
from gesture_classifier import GestureClassifier
from dynamic_gesture import DynamicGestureRecognizer
from gesture_commands import GestureCommandMapper, create_demo_mapper
from rehab_evaluation import FingerFlexibilityEvaluator, RehabTrainingSession, REHAB_EXERCISES
from utils import (
    draw_gesture_info, draw_fps, draw_finger_states, draw_info_panel,
    draw_trajectory, draw_3d_pose_info, draw_rehab_progress,
    draw_command_history, draw_rehab_training_session
)


def main():
    max_hands = 2
    det_confidence = 0.7
    show_landmarks = True
    show_info = True
    show_fingers = True
    enable_dynamic = True
    show_trajectory = True
    show_3d_info = True
    show_commands = True
    show_rehab = True
    use_tracking = True

    detector = HandDetector(
        max_num_hands=max_hands,
        min_detection_confidence=det_confidence,
    )
    classifier = GestureClassifier()
    dynamic_recognizers = {}
    command_mapper = create_demo_mapper()
    rehab_evaluator = FingerFlexibilityEvaluator()
    rehab_session = None

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
    cap.set(cv2.CAP_PROP_FPS, 60)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("Error: Cannot open camera")
        sys.exit(1)

    print("=" * 60)
    print("  手部关键点检测与手势识别系统 (完整版)")
    print("=" * 60)
    print("  [Q] 退出  |  [R] 重置  |  [L] 关键点  |  [F] 手指状态")
    print("  [T] 轨迹  |  [3] 3D信息 |  [C] 指令  |  [E] 康复评估")
    print("  [1] 握拳训练 | [2] 张指训练 | [3] 拇指对指")
    print("  [S] 停止训练 | [P] 暂停训练")
    print("=" * 60)

    while True:
        ret, img = cap.read()
        if not ret:
            print("Error: Cannot read frame")
            break

        img = cv2.flip(img, 1)

        img, hands = detector.find_hands(img, draw=show_landmarks, use_tracking=use_tracking)

        static_gesture = "无"
        dynamic_gesture = "无"
        window_info = None
        active_hand_ids = set()

        for hand_info in hands:
            hand_id = hand_info["hand_id"]
            active_hand_ids.add(hand_id)

            gesture_name, confidence = classifier.classify(hand_info, detector)
            gesture_label = classifier.get_label(gesture_name)
            static_gesture = gesture_label

            if show_commands:
                command_mapper.process_static_gesture(gesture_name, confidence)

            dynamic_label = None
            dynamic_conf = None
            if enable_dynamic:
                if hand_id not in dynamic_recognizers:
                    dynamic_recognizers[hand_id] = DynamicGestureRecognizer(
                        base_sequence_length=30,
                        use_lstm=False,
                        adaptive_window=True
                    )
                recognizer = dynamic_recognizers[hand_id]
                lm_array = detector.get_landmark_array(hand_info)
                recognizer.update(lm_array, hand_info)
                dyn_class, dyn_conf = recognizer.predict()
                window_info = recognizer.get_window_info()

                if show_commands and dyn_class != 6:
                    command_mapper.process_dynamic_gesture(dyn_class, dyn_conf)

                if dyn_class != 6:
                    dynamic_label = DynamicGestureRecognizer.get_label(dyn_class)
                    dynamic_conf = dyn_conf
                    dynamic_gesture = dynamic_label

            if show_info:
                draw_gesture_info(
                    img, gesture_name, gesture_label, confidence,
                    hand_info, dynamic_label, dynamic_conf,
                )

            if show_fingers:
                fingers = detector.get_finger_states(hand_info)
                draw_finger_states(img, fingers, hand_info)

            if show_trajectory:
                draw_trajectory(img, hand_info)

            if show_3d_info and "pose_3d" in hand_info:
                draw_3d_pose_info(img, hand_info)

            if show_rehab and rehab_evaluator:
                rehab_evaluator.update(hand_info.get("pose_3d"))

            if rehab_session and rehab_session.is_running:
                rehab_session.update(hand_info.get("pose_3d"))

        for hid in list(dynamic_recognizers.keys()):
            if hid not in active_hand_ids:
                del dynamic_recognizers[hid]

        if show_info:
            draw_info_panel(
                img, len(hands), static_gesture, dynamic_gesture,
                detector.fps, window_info
            )

        if show_rehab:
            draw_rehab_progress(img, rehab_evaluator)

        if show_commands:
            draw_command_history(img, command_mapper)

        if rehab_session:
            draw_rehab_training_session(img, rehab_session)

        draw_fps(img, detector.fps)

        cv2.imshow("Hand Gesture Recognition (Full)", img)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            for recognizer in dynamic_recognizers.values():
                recognizer.reset()
            command_mapper.reset()
            rehab_evaluator.reset()
            print("已重置")
        elif key == ord("l"):
            show_landmarks = not show_landmarks
            print(f"关键点: {'开' if show_landmarks else '关'}")
        elif key == ord("f"):
            show_fingers = not show_fingers
            print(f"手指状态: {'开' if show_fingers else '关'}")
        elif key == ord("t"):
            show_trajectory = not show_trajectory
            print(f"轨迹显示: {'开' if show_trajectory else '关'}")
        elif key == ord("3"):
            show_3d_info = not show_3d_info
            print(f"3D信息: {'开' if show_3d_info else '关'}")
        elif key == ord("c"):
            show_commands = not show_commands
            print(f"指令历史: {'开' if show_commands else '关'}")
        elif key == ord("e"):
            show_rehab = not show_rehab
            print(f"康复评估: {'开' if show_rehab else '关'}")
        elif key == ord("1"):
            rehab_session = RehabTrainingSession("fist_clench")
            rehab_session.start()
            print(f"开始训练: {REHAB_EXERCISES['fist_clench']['name']}")
        elif key == ord("2"):
            rehab_session = RehabTrainingSession("finger_spread")
            rehab_session.start()
            print(f"开始训练: {REHAB_EXERCISES['finger_spread']['name']}")
        elif key == ord("4"):
            rehab_session = RehabTrainingSession("individual_finger")
            rehab_session.start()
            print(f"开始训练: {REHAB_EXERCISES['individual_finger']['name']}")
        elif key == ord("s"):
            if rehab_session:
                report = rehab_session.stop()
                print("训练报告:", report["overall_score"], "分")
        elif key == ord("p"):
            if rehab_session:
                paused = rehab_session.pause()
                print(f"训练: {'暂停' if paused else '继续'}")

    cap.release()
    cv2.destroyAllWindows()
    detector.release()


if __name__ == "__main__":
    main()
