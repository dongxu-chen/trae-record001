import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional, Any
from collections import deque
import threading
import math


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, 1, d_model)
        pe[:, 0, 0::2] = torch.sin(position * div_term)
        pe[:, 0, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:x.size(0)]
        return self.dropout(x)


class ActionLSTMPredictor(nn.Module):
    def __init__(
        self,
        num_classes: int = 8,
        hidden_size: int = 256,
        num_layers: int = 2,
        dropout: float = 0.3,
        bidirectional: bool = False
    ):
        super().__init__()
        self.num_classes = num_classes
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.directions = 2 if bidirectional else 1

        self.embedding = nn.Linear(num_classes, hidden_size)

        self.lstm = nn.LSTM(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )

        self.fc = nn.Sequential(
            nn.Linear(hidden_size * self.directions, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_classes)
        )

        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LSTM):
                for name, param in m.named_parameters():
                    if 'weight' in name:
                        nn.init.xavier_normal_(param)
                    elif 'bias' in name:
                        nn.init.zeros_(param)

    def forward(self, x: torch.Tensor, hidden: Optional[Tuple] = None):
        batch_size = x.size(0)

        x = self.embedding(x)

        if hidden is None:
            h0 = torch.zeros(
                self.num_layers * self.directions,
                batch_size,
                self.hidden_size,
                device=x.device
            )
            c0 = torch.zeros(
                self.num_layers * self.directions,
                batch_size,
                self.hidden_size,
                device=x.device
            )
            hidden = (h0, c0)

        output, hidden = self.lstm(x, hidden)
        output = self.fc(output[:, -1, :])

        return output, hidden


class ActionTransformerPredictor(nn.Module):
    def __init__(
        self,
        num_classes: int = 8,
        d_model: int = 128,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
        max_seq_len: int = 100
    ):
        super().__init__()
        self.num_classes = num_classes
        self.d_model = d_model

        self.embedding = nn.Linear(num_classes, d_model)
        self.pos_encoder = PositionalEncoding(d_model, max_len=max_seq_len, dropout=dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.fc = nn.Sequential(
            nn.Linear(d_model, d_model * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model * 2, num_classes)
        )

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None):
        x = self.embedding(x) * math.sqrt(self.d_model)
        x = self.pos_encoder(x.transpose(0, 1)).transpose(0, 1)

        if mask is not None:
            output = self.transformer(x, src_key_padding_mask=mask)
        else:
            output = self.transformer(x)

        output = self.fc(output[:, -1, :])

        return output


class TemporalConvolutionalNetwork(nn.Module):
    def __init__(
        self,
        num_classes: int = 8,
        hidden_size: int = 128,
        kernel_size: int = 3,
        num_layers: int = 4,
        dropout: float = 0.2
    ):
        super().__init__()
        self.num_classes = num_classes
        self.hidden_size = hidden_size

        self.embedding = nn.Linear(num_classes, hidden_size)

        layers = []
        for i in range(num_layers):
            dilation = 2 ** i
            padding = (kernel_size - 1) * dilation // 2
            layers.extend([
                nn.Conv1d(
                    hidden_size, hidden_size,
                    kernel_size=kernel_size,
                    padding=padding,
                    dilation=dilation
                ),
                nn.BatchNorm1d(hidden_size),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])

        self.tcn = nn.Sequential(*layers)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x: torch.Tensor):
        x = self.embedding(x)
        x = x.transpose(1, 2)
        x = self.tcn(x)
        x = x.transpose(1, 2)
        x = self.fc(x[:, -1, :])
        return x


class ActionPredictionEngine:
    def __init__(
        self,
        num_classes: int = 8,
        history_size: int = 30,
        prediction_horizon: int = 5,
        model_type: str = "lstm",
        device: str = "cpu",
        multi_label: bool = True
    ):
        self.num_classes = num_classes
        self.history_size = history_size
        self.prediction_horizon = prediction_horizon
        self.model_type = model_type
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.multi_label = multi_label

        self._action_history: deque = deque(maxlen=history_size)
        self._confidence_history: deque = deque(maxlen=history_size)
        self._timestamp_history: deque = deque(maxlen=history_size)

        self._lock = threading.Lock()
        self._last_predictions: Optional[List[Dict[str, Any]]] = None
        self._prediction_counter: int = 0

        self._build_model()

    def _build_model(self):
        if self.model_type == "lstm":
            self.model = ActionLSTMPredictor(
                num_classes=self.num_classes,
                hidden_size=256,
                num_layers=2,
                dropout=0.3
            )
        elif self.model_type == "transformer":
            self.model = ActionTransformerPredictor(
                num_classes=self.num_classes,
                d_model=128,
                nhead=4,
                num_layers=2,
                dropout=0.1
            )
        elif self.model_type == "tcn":
            self.model = TemporalConvolutionalNetwork(
                num_classes=self.num_classes,
                hidden_size=128,
                kernel_size=3,
                num_layers=4
            )
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

        self.model = self.model.to(self.device)
        self.model.eval()

    def update_history(
        self,
        action_idx: int,
        confidence: float,
        timestamp: float,
        all_confidences: Optional[np.ndarray] = None
    ):
        with self._lock:
            self._action_history.append(action_idx)
            self._confidence_history.append(confidence)
            self._timestamp_history.append(timestamp)

    def _prepare_sequence(self) -> Optional[torch.Tensor]:
        if len(self._action_history) < 5:
            return None

        sequence = np.zeros((len(self._action_history), self.num_classes), dtype=np.float32)

        for i, (action_idx, conf) in enumerate(
            zip(self._action_history, self._confidence_history)
        ):
            sequence[i, action_idx] = conf

        history = list(self._confidence_history)
        avg_conf = np.mean(history) if history else 0.0
        for i in range(sequence.shape[0]):
            for j in range(sequence.shape[1]):
                if sequence[i, j] == 0:
                    sequence[i, j] = avg_conf * 0.1

        sequence_tensor = torch.from_numpy(sequence).float().to(self.device)
        sequence_tensor = sequence_tensor.unsqueeze(0)

        return sequence_tensor

    def predict_next_action(self) -> Optional[List[Dict[str, Any]]]:
        with self._lock:
            if len(self._action_history) < 5:
                return None

            sequence = self._prepare_sequence()
            if sequence is None:
                return None

            with torch.no_grad():
                if self.model_type == "lstm":
                    logits, _ = self.model(sequence)
                else:
                    logits = self.model(sequence)

                if self.multi_label:
                    probabilities = torch.sigmoid(logits)
                else:
                    probabilities = torch.softmax(logits, dim=1)

                probs_np = probabilities[0].cpu().numpy()

            predictions = []
            for class_idx in range(self.num_classes):
                confidence = float(probs_np[class_idx])
                if confidence >= 0.3:
                    predictions.append({
                        'class_idx': class_idx,
                        'confidence': confidence,
                        'prediction_step': 1
                    })

            predictions.sort(key=lambda x: x['confidence'], reverse=True)
            self._last_predictions = predictions[:5]
            self._prediction_counter += 1

            return self._last_predictions

    def predict_multi_step(
        self,
        steps: int = 5
    ) -> List[List[Dict[str, Any]]]:
        with self._lock:
            if len(self._action_history) < 5:
                return []

            all_predictions = []
            current_sequence = self._prepare_sequence()

            if current_sequence is None:
                return []

            with torch.no_grad():
                for step in range(steps):
                    if self.model_type == "lstm":
                        logits, _ = self.model(current_sequence)
                    else:
                        logits = self.model(current_sequence)

                    if self.multi_label:
                        probabilities = torch.sigmoid(logits)
                    else:
                        probabilities = torch.softmax(logits, dim=1)

                    probs_np = probabilities[0].cpu().numpy()

                    step_predictions = []
                    for class_idx in range(self.num_classes):
                        confidence = float(probs_np[class_idx])
                        if confidence >= 0.3:
                            step_predictions.append({
                                'class_idx': class_idx,
                                'confidence': confidence,
                                'prediction_step': step + 1
                            })

                    step_predictions.sort(key=lambda x: x['confidence'], reverse=True)
                    all_predictions.append(step_predictions[:3])

                    next_input = torch.zeros_like(current_sequence[:, -1:, :])
                    top_idx = int(np.argmax(probs_np))
                    next_input[0, 0, top_idx] = probs_np[top_idx]

                    current_sequence = torch.cat(
                        [current_sequence[:, 1:, :], next_input],
                        dim=1
                    )

            return all_predictions

    def get_action_transition_matrix(self) -> np.ndarray:
        if len(self._action_history) < 2:
            return np.zeros((self.num_classes, self.num_classes), dtype=np.float32)

        transition_matrix = np.zeros(
            (self.num_classes, self.num_classes),
            dtype=np.float32
        )

        history = list(self._action_history)
        for i in range(len(history) - 1):
            from_action = history[i]
            to_action = history[i + 1]
            if 0 <= from_action < self.num_classes and 0 <= to_action < self.num_classes:
                transition_matrix[from_action, to_action] += 1

        row_sums = transition_matrix.sum(axis=1, keepdims=True)
        transition_matrix = np.divide(
            transition_matrix, row_sums,
            out=np.zeros_like(transition_matrix),
            where=row_sums != 0
        )

        return transition_matrix

    def get_most_probable_next(self) -> Optional[Dict[str, Any]]:
        predictions = self.predict_next_action()
        if not predictions:
            return None
        return predictions[0] if predictions else None

    def get_prediction_confidence(self) -> float:
        if self._last_predictions is None:
            return 0.0
        if not self._last_predictions:
            return 0.0
        return float(np.mean([p['confidence'] for p in self._last_predictions]))

    def get_history_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'history_length': len(self._action_history),
                'unique_actions': len(set(self._action_history)),
                'avg_confidence': np.mean(self._confidence_history) if self._confidence_history else 0.0,
                'prediction_count': self._prediction_counter
            }

    def is_ready(self) -> bool:
        return len(self._action_history) >= 10

    def clear_history(self):
        with self._lock:
            self._action_history.clear()
            self._confidence_history.clear()
            self._timestamp_history.clear()
            self._last_predictions = None
            self._prediction_counter = 0


class AnticipatoryActionPredictor:
    def __init__(
        self,
        num_classes: int = 8,
        history_size: int = 50,
        prediction_horizon: int = 10,
        device: str = "cpu"
    ):
        self.num_classes = num_classes
        self.history_size = history_size
        self.prediction_horizon = prediction_horizon
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")

        self.lstm_predictor = ActionLSTMPredictor(
            num_classes=num_classes,
            hidden_size=256,
            num_layers=2
        ).to(self.device)

        self.tcn_predictor = TemporalConvolutionalNetwork(
            num_classes=num_classes,
            hidden_size=128
        ).to(self.device)

        self._action_history: deque = deque(maxlen=history_size)
        self._confidence_history: deque = deque(maxlen=history_size)
        self._lock = threading.Lock()

        self._ensemble_weights = {
            'lstm': 0.6,
            'tcn': 0.4
        }

    def update(
        self,
        action_idx: int,
        confidence: float,
        all_confidences: Optional[np.ndarray] = None
    ):
        with self._lock:
            self._action_history.append(action_idx)
            self._confidence_history.append(confidence)

    def _encode_history(self) -> Optional[torch.Tensor]:
        if len(self._action_history) < 10:
            return None

        sequence = np.zeros((len(self._action_history), self.num_classes), dtype=np.float32)
        for i, (action_idx, conf) in enumerate(
            zip(self._action_history, self._confidence_history)
        ):
            sequence[i, action_idx] = conf

        return torch.from_numpy(sequence).float().to(self.device).unsqueeze(0)

    def anticipate(self) -> Dict[str, Any]:
        with self._lock:
            sequence = self._encode_history()
            if sequence is None:
                return {
                    'ready': False,
                    'message': 'Insufficient history'
                }

            with torch.no_grad():
                lstm_logits, _ = self.lstm_predictor(sequence)
                tcn_logits = self.tcn_predictor(sequence)

                lstm_probs = torch.sigmoid(lstm_logits)
                tcn_probs = torch.sigmoid(tcn_logits)

                ensemble_probs = (
                    self._ensemble_weights['lstm'] * lstm_probs +
                    self._ensemble_weights['tcn'] * tcn_probs
                )

            probs_np = ensemble_probs[0].cpu().numpy()

            anticipations = []
            for class_idx in range(self.num_classes):
                conf = float(probs_np[class_idx])
                if conf >= 0.25:
                    anticipations.append({
                        'class_idx': class_idx,
                        'confidence': conf,
                        'model_contributions': {
                            'lstm': float(lstm_probs[0, class_idx]),
                            'tcn': float(tcn_probs[0, class_idx])
                        }
                    })

            anticipations.sort(key=lambda x: x['confidence'], reverse=True)

            transition_matrix = self._compute_transition_matrix()
            expected_next = self._expected_next_action(transition_matrix)

            return {
                'ready': True,
                'top_anticipations': anticipations[:5],
                'most_probable': anticipations[0] if anticipations else None,
                'expected_next': expected_next,
                'transition_matrix': transition_matrix.tolist(),
                'history_used': len(self._action_history)
            }

    def _compute_transition_matrix(self) -> np.ndarray:
        if len(self._action_history) < 2:
            return np.zeros((self.num_classes, self.num_classes), dtype=np.float32)

        matrix = np.zeros((self.num_classes, self.num_classes), dtype=np.float32)
        history = list(self._action_history)

        for i in range(len(history) - 1):
            from_idx = history[i]
            to_idx = history[i + 1]
            if 0 <= from_idx < self.num_classes and 0 <= to_idx < self.num_classes:
                matrix[from_idx, to_idx] += 1

        row_sums = matrix.sum(axis=1, keepdims=True)
        matrix = np.divide(
            matrix, row_sums,
            out=np.zeros_like(matrix),
            where=row_sums != 0
        )

        return matrix

    def _expected_next_action(self, transition_matrix: np.ndarray) -> Optional[int]:
        if len(self._action_history) == 0:
            return None

        current_action = self._action_history[-1]
        if current_action < 0 or current_action >= self.num_classes:
            return None

        next_probs = transition_matrix[current_action]
        if np.sum(next_probs) > 0:
            return int(np.argmax(next_probs))
        return None

    def clear(self):
        with self._lock:
            self._action_history.clear()
            self._confidence_history.clear()
