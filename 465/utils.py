import cv2
import numpy as np


COLORS = {
    "primary": (0, 255, 0),
    "secondary": (255, 0, 0),
    "accent": (0, 200, 255),
    "warning": (0, 140, 255),
    "text_bg": (0, 0, 0),
    "white": (255, 255, 255),
    "fps": (0, 255, 255),
    "window": (255, 0, 255),
    "depth": (255, 100, 100),
    "rehab": (100, 255, 200),
    "command": (200, 100, 255),
}

FINGER_NAMES = ["拇指", "食指", "中指", "无名指", "小指"]


def draw_gesture_info(img, gesture_name, gesture_label, confidence, hand_info, dynamic_label=None, dynamic_conf=None):
    h, w = img.shape[:2]
    x_min, y_min, x_max, y_max = hand_info["bbox"]
    pad = 10
    x_min = max(0, x_min - pad)
    y_min = max(0, y_min - pad)
    x_max = min(w, x_max + pad)
    y_max = min(h, y_max + pad)

    hand_id = hand_info.get("hand_id", 0)
    id_colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0)]
    color = id_colors[hand_id % len(id_colors)] if confidence > 0.7 else COLORS["warning"]

    cv2.rectangle(img, (x_min, y_min), (x_max, y_max), color, 2)

    handedness = "右手" if hand_info["handedness"] == "Right" else "左手"
    hand_id_text = f"ID:{hand_id}"
    text = f"{hand_id_text} {gesture_label} ({handedness}) {confidence:.0%}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 2
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    cv2.rectangle(img, (x_min, y_min - th - 10), (x_min + tw + 10, y_min), COLORS["text_bg"], -1)
    cv2.putText(img, text, (x_min + 5, y_min - 5), font, font_scale, color, thickness)

    if "speed" in hand_info and hand_info["speed"] > 5:
        speed_text = f"速度: {hand_info['speed']:.1f}px/s"
        (st, sth), _ = cv2.getTextSize(speed_text, font, 0.5, 1)
        cv2.rectangle(img, (x_min, y_max + 5), (x_min + st + 10, y_max + sth + 15), COLORS["text_bg"], -1)
        cv2.putText(img, speed_text, (x_min + 5, y_max + sth + 10), font, 0.5, COLORS["window"], 1)

    if dynamic_label and dynamic_conf and dynamic_conf > 0.4:
        dy = y_max + 45
        dyn_text = f"动态: {dynamic_label} {dynamic_conf:.0%}"
        (dtw, dth), _ = cv2.getTextSize(dyn_text, font, 0.6, 2)
        cv2.rectangle(img, (x_min, dy - dth - 5), (x_min + dtw + 10, dy + 5), COLORS["text_bg"], -1)
        cv2.putText(img, dyn_text, (x_min + 5, dy), font, 0.6, COLORS["accent"], 2)

    return img


def draw_3d_pose_info(img, hand_info, x_offset=10, y_offset=150):
    if "pose_3d" not in hand_info or hand_info["pose_3d"] is None:
        return img

    pose = hand_info["pose_3d"]
    orientation = pose.get_hand_orientation()
    center_3d = hand_info.get("center_3d", (0, 0, 0))

    font = cv2.FONT_HERSHEY_SIMPLEX
    y = y_offset

    cv2.putText(img, f"Yaw: {orientation['yaw']:.1f}°", (x_offset, y), font, 0.5, COLORS["depth"], 1)
    y += 20
    cv2.putText(img, f"Pitch: {orientation['pitch']:.1f}°", (x_offset, y), font, 0.5, COLORS["depth"], 1)
    y += 20
    cv2.putText(img, f"深度: {center_3d[2]:.3f}", (x_offset, y), font, 0.5, COLORS["depth"], 1)
    y += 20

    for i, finger in enumerate(FINGER_NAMES):
        angles = pose.finger_angles.get(finger, [])
        if angles:
            total_angle = sum(angles)
            cv2.putText(img, f"{finger}: {total_angle:.0f}°", (x_offset, y), font, 0.45, COLORS["depth"], 1)
            y += 18

    return img


def draw_fps(img, fps, target_fps=30):
    color = COLORS["primary"] if fps >= target_fps else COLORS["warning"]
    text = f"FPS: {fps:.1f}/{target_fps}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(text, font, 0.8, 2)
    h, w = img.shape[:2]
    cv2.rectangle(img, (w - tw - 20, 5), (w - 5, th + 15), COLORS["text_bg"], -1)
    cv2.putText(img, text, (w - tw - 15, th + 10), font, 0.8, color, 2)
    return img


def draw_finger_states(img, fingers, hand_info, finger_names=None):
    if finger_names is None:
        finger_names = FINGER_NAMES
    x_min, y_min, _, _ = hand_info["bbox"]
    start_y = y_min + 10
    for i, (name, up) in enumerate(zip(finger_names, fingers)):
        color = COLORS["primary"] if up else (100, 100, 100)
        state = "↑" if up else "↓"
        text = f"{name} {state}"
        cv2.putText(img, text, (x_min, start_y + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    return img


def draw_info_panel(img, num_hands, static_gesture, dynamic_gesture, fps, window_info=None):
    h, w = img.shape[:2]
    panel_h = 155 if window_info else 130
    panel_w = 250
    overlay = img.copy()
    cv2.rectangle(overlay, (5, 5), (panel_w, panel_h), COLORS["text_bg"], -1)
    cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

    font = cv2.FONT_HERSHEY_SIMPLEX
    y = 30
    cv2.putText(img, f"Hands: {num_hands}", (15, y), font, 0.6, COLORS["white"], 1)
    y += 30
    cv2.putText(img, f"Static: {static_gesture}", (15, y), font, 0.6, COLORS["primary"], 1)
    y += 30
    cv2.putText(img, f"Dynamic: {dynamic_gesture}", (15, y), font, 0.6, COLORS["accent"], 1)
    y += 30
    fps_color = COLORS["primary"] if fps >= 30 else COLORS["warning"]
    cv2.putText(img, f"FPS: {fps:.1f}/30", (15, y), font, 0.6, fps_color, 1)

    if window_info:
        y += 30
        cv2.putText(img, f"Window: {window_info.get('window_size', 30)}", (15, y), font, 0.6, COLORS["window"], 1)

    return img


def draw_trajectory(img, hand_info, max_points=30, color=None):
    if "tracker" not in hand_info:
        return img

    tracker = hand_info["tracker"]
    hand_id = hand_info.get("hand_id", 0)
    if color is None:
        id_colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0)]
        color = id_colors[hand_id % len(id_colors)]

    history = list(tracker.history)
    if len(history) > 1:
        for i in range(1, len(history)):
            cv2.line(img, history[i - 1], history[i], color, 2)

    return img


def draw_rehab_progress(img, evaluator, x=280, y=10):
    if not evaluator or not evaluator.is_active:
        return img

    scores = evaluator.calculate_flexibility_score()
    overall = scores["overall"]

    h, w = img.shape[:2]
    panel_w = 200
    panel_h = 200

    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + panel_w, y + panel_h), COLORS["text_bg"], -1)
    cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

    font = cv2.FONT_HERSHEY_SIMPLEX
    y_pos = y + 30

    cv2.putText(img, "🏥 康复评估", (x + 10, y_pos), font, 0.7, COLORS["rehab"], 2)
    y_pos += 30

    cv2.putText(img, f"总分: {overall:.1f}/100", (x + 10, y_pos), font, 0.55, COLORS["white"], 1)
    y_pos += 25

    cv2.putText(img, f"次数: {evaluator.total_reps}", (x + 10, y_pos), font, 0.5, COLORS["white"], 1)
    y_pos += 25

    cv2.putText(img, f"时间: {evaluator.session_duration:.0f}s", (x + 10, y_pos), font, 0.5, COLORS["white"], 1)
    y_pos += 30

    for i, finger in enumerate(FINGER_NAMES):
        finger_data = evaluator.get_finger_range_of_motion(finger)
        score = finger_data["percentage"]
        bar_w = int(80 * min(1, score / 100))
        cv2.rectangle(img, (x + 60, y_pos + i * 16 - 10), (x + 60 + bar_w, y_pos + i * 16 + 3), COLORS["rehab"], -1)
        cv2.rectangle(img, (x + 60, y_pos + i * 16 - 10), (x + 140, y_pos + i * 16 + 3), COLORS["white"], 1)
        cv2.putText(img, finger[0], (x + 10, y_pos + i * 16), font, 0.4, COLORS["white"], 1)

    return img


def draw_command_history(img, command_mapper, x=490, y=10, max_items=8):
    if not command_mapper:
        return img

    history = command_mapper.get_command_history()
    if not history:
        return img

    h, w = img.shape[:2]
    panel_w = 160
    panel_h = 200

    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + panel_w, y + panel_h), COLORS["text_bg"], -1)
    cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

    font = cv2.FONT_HERSHEY_SIMPLEX
    y_pos = y + 25

    cv2.putText(img, "🎮 指令历史", (x + 10, y_pos), font, 0.6, COLORS["command"], 2)
    y_pos += 25

    recent = list(reversed(history))[:max_items]
    for i, cmd in enumerate(recent):
        text = f"{cmd['time']} {cmd['action']}"
        color = COLORS["primary"] if cmd["success"] else COLORS["warning"]
        cv2.putText(img, text, (x + 10, y_pos + i * 18), font, 0.4, color, 1)

    return img


def draw_rehab_training_session(img, session, x=660, y=10):
    if not session or not session.is_running:
        return img

    h, w = img.shape[:2]
    panel_w = 160
    panel_h = 180

    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + panel_w, y + panel_h), COLORS["text_bg"], -1)
    cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

    font = cv2.FONT_HERSHEY_SIMPLEX
    y_pos = y + 25

    cv2.putText(img, "💪 训练中", (x + 10, y_pos), font, 0.6, COLORS["rehab"], 2)
    y_pos += 25

    exercise = session.exercise
    cv2.putText(img, exercise["name"], (x + 10, y_pos), font, 0.45, COLORS["white"], 1)
    y_pos += 20

    progress = session.get_progress()
    time_left = session.get_time_remaining()
    cv2.putText(img, f"进度: {progress:.0f}%", (x + 10, y_pos), font, 0.45, COLORS["white"], 1)
    y_pos += 20
    cv2.putText(img, f"剩余: {time_left:.0f}s", (x + 10, y_pos), font, 0.45, COLORS["white"], 1)
    y_pos += 25

    bar_w = int(140 * min(1, progress / 100))
    cv2.rectangle(img, (x + 10, y_pos), (x + 10 + bar_w, y_pos + 15), COLORS["rehab"], -1)
    cv2.rectangle(img, (x + 10, y_pos), (x + 150, y_pos + 15), COLORS["white"], 1)

    if session.is_complete():
        y_pos += 30
        cv2.putText(img, "✅ 完成!", (x + 40, y_pos), font, 0.6, COLORS["primary"], 2)

    return img
