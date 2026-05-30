import numpy as np


GESTURE_LABELS = {
    "fist": "✊ 拳头",
    "thumbs_up": "👍 点赞",
    "thumbs_down": "👎 踩",
    "one": "☝️ 1",
    "two": "✌️ 2",
    "three": "🤟 3",
    "four": "🖖 4",
    "five": "🖐 5",
    "ok": "👌 OK",
    "rock": "🤘 摇滚",
    "peace": "✌️ 和平",
    "call": "🤙 打电话",
    "point": "👆 指向",
    "unknown": "❓ 未知",
}


class GestureClassifier:
    def __init__(self):
        self._gesture_map = {
            (0, 0, 0, 0, 0): "fist",
            (1, 0, 0, 0, 0): "thumbs_up",
            (0, 0, 0, 0, 1): "thumbs_down",
            (0, 1, 0, 0, 0): "point",
            (0, 1, 1, 0, 0): "two",
            (0, 1, 1, 1, 0): "three",
            (0, 1, 1, 1, 1): "four",
            (1, 1, 1, 1, 1): "five",
            (1, 1, 0, 0, 1): "rock",
            (1, 0, 0, 0, 1): "call",
        }

    def classify(self, hand_info, detector):
        fingers = detector.get_finger_states(hand_info)
        lm = hand_info["landmarks"]

        ok_gesture = self._check_ok(lm, fingers)
        if ok_gesture:
            return "ok", 0.9

        thumb_up = fingers[0]
        if not thumb_up:
            thumb_tip = lm[4]
            thumb_ip = lm[3]
            if thumb_tip[1] > thumb_ip[1]:
                if all(not f for f in fingers[1:]):
                    return "thumbs_down", 0.8

        key = tuple(int(f) for f in fingers)
        gesture = self._gesture_map.get(key, None)
        if gesture:
            confidence = hand_info["confidence"]
            return gesture, confidence

        if fingers[0] and not any(fingers[1:]):
            return "thumbs_up", 0.7

        if sum(fingers) >= 3:
            return "five", 0.5

        return "unknown", 0.0

    def _check_ok(self, lm, fingers):
        thumb_tip = np.array([lm[4][0], lm[4][1]])
        index_tip = np.array([lm[8][0], lm[8][1]])
        dist = np.linalg.norm(thumb_tip - index_tip)

        thumb_ip = np.array([lm[3][0], lm[3][1]])
        index_pip = np.array([lm[6][0], lm[6][1]])
        ref_dist = np.linalg.norm(thumb_ip - index_pip)

        if ref_dist > 0:
            ratio = dist / ref_dist
        else:
            ratio = 1.0

        middle_up = fingers[2]
        ring_up = fingers[3]
        pinky_up = fingers[4]

        if ratio < 0.5 and middle_up and ring_up and pinky_up:
            return True

        if ratio < 0.4 and not fingers[1] and middle_up:
            return True

        return False

    def get_number(self, fingers):
        return sum(int(f) for f in fingers)

    def get_label(self, gesture_name):
        return GESTURE_LABELS.get(gesture_name, gesture_name)
