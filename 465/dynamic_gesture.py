import numpy as np
from collections import deque, Counter
import os

TORCH_AVAILABLE = False
try:
    import torch
    import torch.nn as nn
    import torch.nn.utils.prune as prune
    TORCH_AVAILABLE = True
except (ImportError, OSError):
    pass


DYNAMIC_GESTURE_LABELS = {
    0: "🔄 挥手",
    1: "👈 左滑",
    2: "👉 右滑",
    3: "⭕ 画圈",
    4: "👆 上下",
    5: "🤝 来回",
    6: "❌ 无动作",
}

FEATURE_DIM = 42
NUM_CLASSES = len(DYNAMIC_GESTURE_LABELS)
MIN_SEQ_LENGTH = 15
MAX_SEQ_LENGTH = 45
DEFAULT_SEQ_LENGTH = 30


if TORCH_AVAILABLE:
    class GestureLSTM(nn.Module):
        def __init__(self, input_dim=FEATURE_DIM, hidden_dim=32, num_layers=1, num_classes=NUM_CLASSES, dropout=0.2):
            super().__init__()
            self.hidden_dim = hidden_dim
            self.num_layers = num_layers
            self.lstm = nn.LSTM(
                input_dim, hidden_dim, num_layers,
                batch_first=True, dropout=dropout if num_layers > 1 else 0,
                bidirectional=False,
            )
            self.fc = nn.Sequential(
                nn.Linear(hidden_dim, 16),
                nn.ReLU(inplace=True),
                nn.Linear(16, num_classes),
            )

        def forward(self, x):
            out, _ = self.lstm(x)
            out = self.fc(out[:, -1, :])
            return out

    def prune_model(model, amount=0.3):
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                try:
                    prune.l1_unstructured(module, name='weight', amount=amount)
                    prune.remove(module, 'weight')
                except:
                    pass
        return model

else:
    class GestureLSTM:
        def __init__(self, **kwargs):
            pass


class DynamicWindowBuffer:
    def __init__(self, max_len=MAX_SEQ_LENGTH):
        self.max_len = max_len
        self.data = []
        self.timestamps = []

    def append(self, item, timestamp=None):
        self.data.append(item)
        self.timestamps.append(timestamp if timestamp else 0)
        if len(self.data) > self.max_len:
            self.data.pop(0)
            self.timestamps.pop(0)

    def get_window(self, window_size):
        window_size = min(window_size, len(self.data))
        return self.data[-window_size:]

    def __len__(self):
        return len(self.data)

    def clear(self):
        self.data.clear()
        self.timestamps.clear()


class DynamicGestureRecognizer:
    def __init__(self, base_sequence_length=DEFAULT_SEQ_LENGTH, use_lstm=True, model_path=None,
                 adaptive_window=True):
        self.base_sequence_length = base_sequence_length
        self.use_lstm = use_lstm and TORCH_AVAILABLE
        self.adaptive_window = adaptive_window
        self.buffer = DynamicWindowBuffer(MAX_SEQ_LENGTH)
        self.wrist_buffer = DynamicWindowBuffer(MAX_SEQ_LENGTH)
        self.model = None
        self.device = None
        self.current_window_size = base_sequence_length
        self.hand_speed = 0.0
        self.speed_history = deque(maxlen=10)
        self.confidence_history = deque(maxlen=5)

        if self.use_lstm and TORCH_AVAILABLE:
            self.device = torch.device("cpu")
            self.model = GestureLSTM().to(self.device)
            if model_path and os.path.exists(model_path):
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            else:
                try:
                    self.model = prune_model(self.model, amount=0.3)
                except:
                    pass
            self.model.eval()

        self.rule_results = deque(maxlen=5)
        self.lstm_results = deque(maxlen=5)

    def _compute_adaptive_window(self, speed):
        if not self.adaptive_window:
            return self.base_sequence_length

        if speed < 10:
            return MAX_SEQ_LENGTH
        elif speed > 80:
            return MIN_SEQ_LENGTH
        else:
            ratio = (speed - 10) / 70
            window_size = int(MAX_SEQ_LENGTH - ratio * (MAX_SEQ_LENGTH - MIN_SEQ_LENGTH))
            return int(np.clip(window_size, MIN_SEQ_LENGTH, MAX_SEQ_LENGTH))

    def update(self, landmark_array, hand_info=None):
        self.buffer.append(landmark_array)
        if hand_info:
            wrist_pos = hand_info["center"]
            self.wrist_buffer.append(wrist_pos)

            if "speed" in hand_info:
                self.hand_speed = 0.7 * self.hand_speed + 0.3 * hand_info["speed"]
                self.speed_history.append(self.hand_speed)
                if len(self.speed_history) > 0:
                    avg_speed = np.mean(self.speed_history)
                    self.current_window_size = self._compute_adaptive_window(avg_speed)

    def predict_rule_based(self):
        effective_window = self.current_window_size
        if len(self.wrist_buffer) < effective_window:
            return 6, 0.0

        positions = self.wrist_buffer.get_window(effective_window)

        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]

        x_range = max(xs) - min(xs)
        y_range = max(ys) - min(ys)
        total_range = x_range + y_range

        if total_range < 30:
            return 6, 0.2

        n = len(positions)
        mid = n // 2
        first_half_x = np.mean(xs[:mid])
        second_half_x = np.mean(xs[mid:])

        x_direction_changes = 0
        y_direction_changes = 0
        for i in range(2, len(xs)):
            prev_dir = xs[i - 1] - xs[i - 2]
            curr_dir = xs[i] - xs[i - 1]
            if prev_dir * curr_dir < 0:
                x_direction_changes += 1
            prev_dir_y = ys[i - 1] - ys[i - 2]
            curr_dir_y = ys[i] - ys[i - 1]
            if prev_dir_y * curr_dir_y < 0:
                y_direction_changes += 1

        dx = second_half_x - first_half_x

        wave_threshold = max(3, int(5 - self.hand_speed / 20))
        if x_direction_changes >= wave_threshold and x_range > 40:
            return 0, min(0.95, 0.4 + x_direction_changes * 0.12)

        if x_range > y_range * 1.5:
            if dx < -15:
                return 1, min(0.95, 0.5 + x_range / 250)
            elif dx > 15:
                return 2, min(0.95, 0.5 + x_range / 250)

        if y_range > x_range * 1.5 and y_direction_changes >= 1:
            return 4, min(0.9, 0.4 + y_direction_changes * 0.1)

        cx = np.mean(xs)
        cy = np.mean(ys)
        distances_from_center = []
        angles = []
        for x, y in positions:
            dx_c = x - cx
            dy_c = y - cy
            distances_from_center.append(np.sqrt(dx_c ** 2 + dy_c ** 2))
            angles.append(np.arctan2(dy_c, dx_c))

        dist_std = np.std(distances_from_center)
        angle_range = np.max(angles) - np.min(angles)
        if dist_std < 30 and angle_range > 3.5:
            return 3, min(0.95, 0.5 + angle_range / 7)

        if y_direction_changes >= 2 and x_range > 25:
            return 5, min(0.8, 0.4 + y_direction_changes * 0.1)

        return 6, 0.3

    def predict_lstm(self):
        if self.model is None or len(self.buffer) < self.base_sequence_length:
            return 6, 0.0

        try:
            sequence = np.array(self.buffer.get_window(self.current_window_size))
            if len(sequence) < 15:
                return 6, 0.0

            input_tensor = torch.FloatTensor(sequence).unsqueeze(0).to(self.device)
            with torch.no_grad():
                output = self.model(input_tensor)
                probs = torch.softmax(output, dim=1)
                confidence, predicted = torch.max(probs, 1)
                return predicted.item(), confidence.item()
        except Exception:
            return 6, 0.0

    def predict(self):
        rule_label, rule_conf = self.predict_rule_based()
        self.rule_results.append((rule_label, rule_conf))

        if self.model is not None:
            lstm_label, lstm_conf = self.predict_lstm()
            self.lstm_results.append((lstm_label, lstm_conf))

            if lstm_conf > rule_conf and lstm_conf > 0.6:
                return lstm_label, lstm_conf

        if len(self.rule_results) >= 2:
            recent = list(self.rule_results)[-2:]
            labels = [r[0] for r in recent]
            most_common = Counter(labels).most_common(1)[0]
            if most_common[1] >= 2:
                avg_conf = np.mean([r[1] for r in recent if r[0] == most_common[0]])
                return most_common[0], avg_conf

        return rule_label, rule_conf

    def get_window_info(self):
        return {
            "window_size": self.current_window_size,
            "hand_speed": self.hand_speed,
        }

    def reset(self):
        self.buffer.clear()
        self.wrist_buffer.clear()
        self.rule_results.clear()
        self.lstm_results.clear()
        self.speed_history.clear()
        self.confidence_history.clear()
        self.hand_speed = 0.0
        self.current_window_size = self.base_sequence_length

    def save_model(self, path):
        if self.model is not None and TORCH_AVAILABLE:
            torch.save(self.model.state_dict(), path)

    @staticmethod
    def get_label(class_id):
        return DYNAMIC_GESTURE_LABELS.get(class_id, "❓ 未知")

    @staticmethod
    def collect_training_sample(landmark_arrays, label):
        return {
            "sequence": np.array(landmark_arrays),
            "label": label,
        }
