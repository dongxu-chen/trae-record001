import json
import os
from collections import deque, Counter
from datetime import datetime


DEFAULT_COMMANDS = {
    "thumbs_up": {
        "name": "点赞",
        "action": "like",
        "description": "发送点赞",
        "cooldown_ms": 1000,
    },
    "thumbs_down": {
        "name": "踩",
        "action": "dislike",
        "description": "发送踩",
        "cooldown_ms": 1000,
    },
    "five": {
        "name": "停止",
        "action": "stop",
        "description": "停止当前操作",
        "cooldown_ms": 500,
    },
    "fist": {
        "name": "开始",
        "action": "start",
        "description": "开始录制/执行",
        "cooldown_ms": 500,
    },
    "ok": {
        "name": "确认",
        "action": "confirm",
        "description": "确认选择",
        "cooldown_ms": 500,
    },
    "one": {
        "name": "选项1",
        "action": "option_1",
        "description": "选择选项1",
        "cooldown_ms": 300,
    },
    "two": {
        "name": "选项2",
        "action": "option_2",
        "description": "选择选项2",
        "cooldown_ms": 300,
    },
    "three": {
        "name": "选项3",
        "action": "option_3",
        "description": "选择选项3",
        "cooldown_ms": 300,
    },
    "four": {
        "name": "选项4",
        "action": "option_4",
        "description": "选择选项4",
        "cooldown_ms": 300,
    },
    "wave": {
        "name": "打招呼",
        "action": "greet",
        "description": "挥手打招呼",
        "cooldown_ms": 2000,
        "is_dynamic": True,
    },
    "swipe_left": {
        "name": "左滑",
        "action": "next",
        "description": "下一个/前进",
        "cooldown_ms": 800,
        "is_dynamic": True,
    },
    "swipe_right": {
        "name": "右滑",
        "action": "prev",
        "description": "上一个/后退",
        "cooldown_ms": 800,
        "is_dynamic": True,
    },
}

DYNAMIC_GESTURE_MAP = {
    0: "wave",
    1: "swipe_left",
    2: "swipe_right",
    3: "circle",
    4: "up_down",
    5: "back_forth",
}


class CommandHandler:
    def __init__(self):
        self.callbacks = {}
        self.command_history = deque(maxlen=100)
        self.last_execution = {}

    def register(self, action_name, callback):
        self.callbacks[action_name] = callback

    def execute(self, action_name, gesture_name=None):
        if action_name in self.callbacks:
            try:
                result = self.callbacks[action_name](gesture_name)
                self.command_history.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "action": action_name,
                    "gesture": gesture_name,
                    "success": True,
                })
                return result
            except Exception as e:
                self.command_history.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "action": action_name,
                    "gesture": gesture_name,
                    "success": False,
                    "error": str(e),
                })
        return None

    def get_history(self):
        return list(self.command_history)


class GestureCommandMapper:
    def __init__(self, config_path=None, min_confidence=0.6, min_frames=2):
        self.config_path = config_path
        self.commands = DEFAULT_COMMANDS.copy()
        self.min_confidence = min_confidence
        self.min_frames = min_frames
        self.command_handler = CommandHandler()

        self.static_gesture_buffer = deque(maxlen=5)
        self.dynamic_gesture_buffer = deque(maxlen=3)
        self.last_executed = {}

        if config_path and os.path.exists(config_path):
            self.load_config(config_path)

    def _check_cooldown(self, gesture_name):
        cmd = self.commands.get(gesture_name)
        if not cmd:
            return False

        cooldown = cmd.get("cooldown_ms", 500) / 1000.0
        last_time = self.last_executed.get(gesture_name, 0)
        current_time = datetime.now().timestamp()

        if current_time - last_time >= cooldown:
            self.last_executed[gesture_name] = current_time
            return True
        return False

    def process_static_gesture(self, gesture_name, confidence):
        if confidence < self.min_confidence:
            return None

        self.static_gesture_buffer.append(gesture_name)
        if len(self.static_gesture_buffer) < self.min_frames:
            return None

        recent = list(self.static_gesture_buffer)[-self.min_frames:]
        if all(g == gesture_name for g in recent):
            if gesture_name in self.commands:
                if self._check_cooldown(gesture_name):
                    cmd = self.commands[gesture_name]
                    action = cmd["action"]
                    self.command_handler.execute(action, gesture_name)
                    return {"gesture": gesture_name, "action": action, "confidence": confidence}

        return None

    def process_dynamic_gesture(self, dynamic_class, confidence):
        if confidence < self.min_confidence or dynamic_class == 6:
            return None

        gesture_name = DYNAMIC_GESTURE_MAP.get(dynamic_class)
        if not gesture_name:
            return None

        self.dynamic_gesture_buffer.append(gesture_name)

        if gesture_name in self.commands:
            if self._check_cooldown(gesture_name):
                cmd = self.commands[gesture_name]
                action = cmd["action"]
                self.command_handler.execute(action, gesture_name)
                return {"gesture": gesture_name, "action": action, "confidence": confidence}

        return None

    def register_command(self, gesture_name, name, action, description, cooldown_ms=500, is_dynamic=False):
        self.commands[gesture_name] = {
            "name": name,
            "action": action,
            "description": description,
            "cooldown_ms": cooldown_ms,
            "is_dynamic": is_dynamic,
        }

    def remove_command(self, gesture_name):
        if gesture_name in self.commands:
            del self.commands[gesture_name]
            return True
        return False

    def register_callback(self, action_name, callback):
        self.command_handler.register(action_name, callback)

    def get_command_history(self):
        return self.command_handler.get_history()

    def get_available_gestures(self):
        static = []
        dynamic = []
        for key, cmd in self.commands.items():
            if cmd.get("is_dynamic", False):
                dynamic.append((key, cmd))
            else:
                static.append((key, cmd))
        return static, dynamic

    def save_config(self, path=None):
        save_path = path or self.config_path
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.commands, f, ensure_ascii=False, indent=2)
            return True
        return False

    def load_config(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.commands = json.load(f)
            return True
        return False

    def reset(self):
        self.static_gesture_buffer.clear()
        self.dynamic_gesture_buffer.clear()
        self.last_executed.clear()


class VolumeController:
    def __init__(self):
        self.volume = 50
        self.min_volume = 0
        self.max_volume = 100

    def set_volume(self, gesture_name):
        if gesture_name == "thumbs_up" or gesture_name == "two":
            self.volume = min(self.max_volume, self.volume + 10)
            print(f"🔊 音量+ : {self.volume}%")
        elif gesture_name == "thumbs_down" or gesture_name == "one":
            self.volume = max(self.min_volume, self.volume - 10)
            print(f"🔉 音量- : {self.volume}%")
        elif gesture_name == "fist":
            self.volume = 0
            print(f"🔇 静音")
        elif gesture_name == "five":
            self.volume = 100
            print(f"🔊 最大音量")
        return self.volume


class PresentationController:
    def __init__(self):
        self.current_slide = 1
        self.total_slides = 10

    def next_slide(self, gesture_name):
        self.current_slide = min(self.total_slides, self.current_slide + 1)
        print(f"📄 下一页: {self.current_slide}/{self.total_slides}")
        return self.current_slide

    def prev_slide(self, gesture_name):
        self.current_slide = max(1, self.current_slide - 1)
        print(f"📄 上一页: {self.current_slide}/{self.total_slides}")
        return self.current_slide


def create_demo_mapper():
    mapper = GestureCommandMapper()

    volume_ctrl = VolumeController()
    pres_ctrl = PresentationController()

    mapper.register_callback("like", volume_ctrl.set_volume)
    mapper.register_callback("dislike", volume_ctrl.set_volume)
    mapper.register_callback("stop", lambda g: print("⏹️ 停止操作"))
    mapper.register_callback("start", lambda g: print("▶️ 开始操作"))
    mapper.register_callback("confirm", lambda g: print("✅ 已确认"))
    mapper.register_callback("next", pres_ctrl.next_slide)
    mapper.register_callback("prev", pres_ctrl.prev_slide)
    mapper.register_callback("greet", lambda g: print("👋 Hello!"))

    return mapper
