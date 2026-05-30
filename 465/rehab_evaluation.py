import numpy as np
from collections import deque
from datetime import datetime
import json
import os


FINGER_NAMES = ["拇指", "食指", "中指", "无名指", "小指"]

NORMAL_RANGE = {
    "拇指": {"min": 15, "max": 75, "target": 60},
    "食指": {"min": 20, "max": 120, "target": 100},
    "中指": {"min": 20, "max": 120, "target": 100},
    "无名指": {"min": 15, "max": 110, "target": 90},
    "小指": {"min": 15, "max": 100, "target": 80},
}

REHAB_EXERCISES = {
    "fist_clench": {
        "name": "握拳训练",
        "description": "缓慢握拳再松开，重复10次",
        "target_reps": 10,
        "duration": 30,
        "difficulty": "简单",
    },
    "finger_spread": {
        "name": "张指训练",
        "description": "手指尽量张开再合拢，重复10次",
        "target_reps": 10,
        "duration": 30,
        "difficulty": "简单",
    },
    "thumb_touch": {
        "name": "拇指对指",
        "description": "拇指依次触碰其他四指指尖，每指5次",
        "target_reps": 20,
        "duration": 45,
        "difficulty": "中等",
    },
    "individual_finger": {
        "name": "单指运动",
        "description": "每根手指独立弯曲伸展，每指5次",
        "target_reps": 25,
        "duration": 60,
        "difficulty": "困难",
    },
    "wave_fingers": {
        "name": "波浪运动",
        "description": "手指依次弯曲形成波浪动作",
        "target_reps": 15,
        "duration": 45,
        "difficulty": "困难",
    },
}


class FingerFlexibilityEvaluator:
    def __init__(self, history_size=100):
        self.finger_angles_history = {finger: deque(maxlen=history_size) for finger in FINGER_NAMES}
        self.finger_max_angles = {finger: 0 for finger in FINGER_NAMES}
        self.finger_min_angles = {finger: 180 for finger in FINGER_NAMES}
        self.finger_current = {finger: 0 for finger in FINGER_NAMES}
        self.finger_previous = {finger: 0 for finger in FINGER_NAMES}
        self.finger_reps = {finger: 0 for finger in FINGER_NAMES}
        self.finger_states = {finger: "unknown" for finger in FINGER_NAMES}
        self.total_reps = 0
        self.session_start = None
        self.session_duration = 0
        self.scores = {}
        self.is_active = False

    def reset(self):
        for finger in FINGER_NAMES:
            self.finger_angles_history[finger].clear()
            self.finger_max_angles[finger] = 0
            self.finger_min_angles[finger] = 180
            self.finger_current[finger] = 0
            self.finger_previous[finger] = 0
            self.finger_reps[finger] = 0
            self.finger_states[finger] = "unknown"
        self.total_reps = 0
        self.session_start = datetime.now()
        self.session_duration = 0
        self.scores = {}
        self.is_active = True

    def update(self, pose_3d):
        if not self.is_active:
            self.reset()

        if pose_3d is None:
            return

        for finger in FINGER_NAMES:
            total_angle = pose_3d.get_finger_total_angle(finger)
            self.finger_current[finger] = total_angle
            self.finger_angles_history[finger].append(total_angle)

            if total_angle > self.finger_max_angles[finger]:
                self.finger_max_angles[finger] = total_angle
            if total_angle < self.finger_min_angles[finger]:
                self.finger_min_angles[finger] = total_angle

            self._detect_repetition(finger)
            self.finger_previous[finger] = total_angle

        self.total_reps = sum(self.finger_reps.values())

        if self.session_start:
            self.session_duration = (datetime.now() - self.session_start).total_seconds()

    def _detect_repetition(self, finger):
        angle = self.finger_current[finger]
        prev_angle = self.finger_previous[finger]
        normal = NORMAL_RANGE[finger]

        if angle < normal["min"] + 5 and self.finger_states[finger] != "closed":
            if self.finger_states[finger] == "open":
                self.finger_reps[finger] += 1
            self.finger_states[finger] = "closed"
        elif angle > normal["target"] - 10 and self.finger_states[finger] != "open":
            self.finger_states[finger] = "open"

    def get_finger_range_of_motion(self, finger):
        max_angle = self.finger_max_angles[finger]
        min_angle = self.finger_min_angles[finger]
        rom = max_angle - min_angle
        normal = NORMAL_RANGE[finger]
        target_rom = normal["target"] - normal["min"]
        percentage = min(100, (rom / target_rom) * 100) if target_rom > 0 else 0
        return {
            "finger": finger,
            "current": self.finger_current[finger],
            "min": min_angle,
            "max": max_angle,
            "rom": rom,
            "target_rom": target_rom,
            "percentage": percentage,
            "reps": self.finger_reps[finger],
            "state": self.finger_states[finger],
        }

    def get_all_fingers_rom(self):
        return {finger: self.get_finger_range_of_motion(finger) for finger in FINGER_NAMES}

    def calculate_flexibility_score(self):
        total_score = 0
        details = {}

        for finger in FINGER_NAMES:
            rom_data = self.get_finger_range_of_motion(finger)
            percentage = rom_data["percentage"]

            reps = self.finger_reps[finger]
            reps_score = min(100, reps * 10)

            finger_score = 0.7 * percentage + 0.3 * reps_score
            total_score += finger_score
            details[finger] = {
                "rom_score": percentage,
                "reps_score": reps_score,
                "total_score": finger_score,
                "reps": reps,
            }

        avg_score = total_score / len(FINGER_NAMES)
        self.scores = {
            "overall": avg_score,
            "details": details,
            "total_reps": self.total_reps,
            "duration": self.session_duration,
        }
        return self.scores

    def get_recommendation(self):
        scores = self.calculate_flexibility_score()
        overall = scores["overall"]
        details = scores["details"]

        if overall >= 80:
            level = "优秀"
            advice = "手指灵活性很好！继续保持，可以尝试更高难度的训练。"
            next_exercise = "individual_finger"
        elif overall >= 60:
            level = "良好"
            advice = "手指灵活性良好，建议增加训练频次进一步提升。"
            next_exercise = "finger_spread"
        elif overall >= 40:
            level = "一般"
            advice = "手指灵活性一般，需要坚持日常训练。"
            next_exercise = "fist_clench"
        else:
            level = "需要加强"
            advice = "建议进行基础康复训练，每次训练10-15分钟。"
            next_exercise = "fist_clench"

        weak_fingers = [f for f, d in details.items() if d["total_score"] < 50]

        return {
            "level": level,
            "advice": advice,
            "next_exercise": next_exercise,
            "weak_fingers": weak_fingers,
            "score": overall,
        }

    def generate_report(self):
        scores = self.calculate_flexibility_score()
        recommendation = self.get_recommendation()

        report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": round(self.session_duration, 1),
            "total_repetitions": self.total_reps,
            "overall_score": round(scores["overall"], 1),
            "flexibility_level": recommendation["level"],
            "finger_details": {},
            "recommendation": recommendation,
        }

        for finger in FINGER_NAMES:
            rom = self.get_finger_range_of_motion(finger)
            report["finger_details"][finger] = {
                "reps": rom["reps"],
                "range_of_motion": round(rom["rom"], 1),
                "score": round(scores["details"][finger]["total_score"], 1),
            }

        return report

    def save_report(self, path):
        report = self.generate_report()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return report

    @staticmethod
    def load_history(path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []


class RehabTrainingSession:
    def __init__(self, exercise_type="fist_clench"):
        self.exercise_type = exercise_type
        self.exercise = REHAB_EXERCISES.get(exercise_type, REHAB_EXERCISES["fist_clench"])
        self.evaluator = FingerFlexibilityEvaluator()
        self.start_time = None
        self.target_reps = self.exercise["target_reps"]
        self.target_duration = self.exercise["duration"]
        self.is_running = False
        self.is_paused = False
        self.milestones = []

    def start(self):
        self.start_time = datetime.now()
        self.evaluator.reset()
        self.is_running = True
        self.is_paused = False
        return self.exercise

    def pause(self):
        self.is_paused = not self.is_paused
        return self.is_paused

    def stop(self):
        self.is_running = False
        report = self.evaluator.generate_report()
        return report

    def update(self, pose_3d):
        if not self.is_running or self.is_paused:
            return None

        self.evaluator.update(pose_3d)

        progress = self.get_progress()
        for milestone in [0.25, 0.5, 0.75, 1.0]:
            if progress >= milestone * 100 and milestone not in self.milestones:
                self.milestones.append(milestone)

        return progress

    def get_progress(self):
        reps_progress = (self.evaluator.total_reps / self.target_reps) * 100
        return min(100, reps_progress)

    def get_time_remaining(self):
        if not self.start_time:
            return self.target_duration
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return max(0, self.target_duration - elapsed)

    def is_complete(self):
        return self.get_progress() >= 100 or self.get_time_remaining() <= 0
