from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import MinMaxScaler
from torch import nn
from torch.utils.data import DataLoader, Dataset


FEATURE_COLUMNS: List[str] = [
    "start_hour",
    "weekday",
    "is_holiday",
    "platform_activity",
    "duration_hours",
    "avg_viewers",
    "engagement_rate",
    "gift_income",
    "peak_viewers",
]

PEAK_INCOME_TARGETS: List[str] = ["peak_viewers", "gift_income"]

ENGAGEMENT_TARGET: List[str] = ["engagement_rate"]

PROFILE_TARGETS: List[str] = [
    "male_pct", "age_18_24", "age_25_34", "age_35_44", "age_45_plus",
]

ALL_TARGETS: List[str] = PEAK_INCOME_TARGETS + ENGAGEMENT_TARGET + PROFILE_TARGETS


@dataclass
class SequenceDataset(Dataset):
    sequences: torch.Tensor
    targets: torch.Tensor

    def __len__(self) -> int:
        return self.sequences.shape[0]

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.sequences[idx], self.targets[idx]


class MultiTaskLSTM(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.1,
        profile_dim: int = 5,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.peak_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
        )
        self.income_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
        )
        self.engagement_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
        )
        self.profile_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, profile_dim),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        out, _ = self.lstm(x)
        last = out[:, -1, :]
        peak = self.peak_head(last).squeeze(-1)
        income = self.income_head(last).squeeze(-1)
        engagement = self.engagement_head(last).squeeze(-1)
        profile = self.profile_head(last)
        return peak, income, engagement, profile


@dataclass
class AudienceProfile:
    male_pct: float
    female_pct: float
    age_18_24: float
    age_25_34: float
    age_35_44: float
    age_45_plus: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "男性占比": round(self.male_pct * 100, 1),
            "女性占比": round(self.female_pct * 100, 1),
            "18-24岁": round(self.age_18_24 * 100, 1),
            "25-34岁": round(self.age_25_34 * 100, 1),
            "35-44岁": round(self.age_35_44 * 100, 1),
            "45岁+": round(self.age_45_plus * 100, 1),
        }


@dataclass
class TrainedModel:
    model: MultiTaskLSTM
    feature_scaler: MinMaxScaler
    target_scaler: MinMaxScaler
    feature_columns: List[str]
    target_columns: List[str]
    seq_len: int
    loss_history: List[float]
    peak_loss_history: List[float]
    income_loss_history: List[float]
    engagement_loss_history: List[float]
    profile_loss_history: List[float]
    feature_importance: List[float]

    def _predict_all(self, df: pd.DataFrame) -> Dict[str, float]:
        df = df.sort_values("date").reset_index(drop=True)
        recent = df[self.feature_columns].iloc[-self.seq_len :].values.astype(np.float32)
        if recent.shape[0] < self.seq_len:
            pad = np.zeros(
                (self.seq_len - recent.shape[0], len(self.feature_columns)), dtype=np.float32
            )
            recent = np.vstack([pad, recent])
        scaled = self.feature_scaler.transform(recent).astype(np.float32)
        tensor = torch.tensor(scaled, dtype=torch.float32).unsqueeze(0)
        self.model.eval()
        with torch.no_grad():
            peak_raw, income_raw, eng_raw, profile_raw = self.model(tensor)
        raw_vec = np.array(
            [peak_raw.item(), income_raw.item(), eng_raw.item()] + profile_raw.cpu().numpy()[0].tolist(),
            dtype=np.float32,
        )
        denorm = self.target_scaler.inverse_transform(raw_vec.reshape(1, -1))[0]
        result: Dict[str, float] = {}
        for i, col in enumerate(self.target_columns):
            result[col] = float(max(0.0, denorm[i]))
        return result

    def predict_from_dataframe(self, df: pd.DataFrame) -> Tuple[float, float]:
        r = self._predict_all(df)
        return r["peak_viewers"], r["gift_income"]

    def predict_engagement(self, df: pd.DataFrame) -> float:
        r = self._predict_all(df)
        return r["engagement_rate"]

    def predict_audience_profile(self, df: pd.DataFrame) -> AudienceProfile:
        r = self._predict_all(df)
        male_pct = float(np.clip(r["male_pct"], 0.0, 1.0))
        ages = np.array([r["age_18_24"], r["age_25_34"], r["age_35_44"], r["age_45_plus"]], dtype=np.float64)
        ages = np.clip(ages, 0.0, None)
        age_sum = ages.sum()
        if age_sum > 0:
            ages = ages / age_sum
        else:
            ages = np.array([0.35, 0.35, 0.20, 0.10])
        return AudienceProfile(
            male_pct=male_pct,
            female_pct=1.0 - male_pct,
            age_18_24=float(ages[0]),
            age_25_34=float(ages[1]),
            age_35_44=float(ages[2]),
            age_45_plus=float(ages[3]),
        )

    def simulate_engagement_change(
        self,
        df: pd.DataFrame,
        feature_name: str,
        new_value: float,
    ) -> Dict[str, float]:
        df = df.sort_values("date").reset_index(drop=True)
        if feature_name not in self.feature_columns:
            raise ValueError(f"未知特征：{feature_name}")
        modified = df.copy()
        idx = modified.index[-1]
        modified.at[idx, feature_name] = new_value
        base_df = df
        base_eng = self.predict_engagement(base_df)
        new_eng = self.predict_engagement(modified)
        base_peak, base_income = self.predict_from_dataframe(base_df)
        new_peak, new_income = self.predict_from_dataframe(modified)
        return {
            "feature": feature_name,
            "original_value": float(df[feature_name].iloc[-1]),
            "new_value": float(new_value),
            "base_engagement": base_eng,
            "new_engagement": new_eng,
            "engagement_delta": new_eng - base_eng,
            "engagement_pct_change": (new_eng - base_eng) / max(base_eng, 1e-6) * 100,
            "base_peak": base_peak,
            "new_peak": new_peak,
            "base_income": base_income,
            "new_income": new_income,
        }


def _extract_feature_importance(
    model: MultiTaskLSTM,
    loader: DataLoader,
    feature_columns: List[str],
) -> List[float]:
    model.eval()
    n_features = len(feature_columns)
    grad_accum = np.zeros(n_features, dtype=np.float64)
    n_samples = 0
    for batch_x, _batch_y in loader:
        batch_x = batch_x.clone().detach().requires_grad_(True)
        peak_out, income_out, eng_out, _prof_out = model(batch_x)
        loss = peak_out.mean() + income_out.mean() + eng_out.mean()
        loss.backward()
        if batch_x.grad is not None:
            g = batch_x.grad.detach().cpu().numpy()
            g = np.abs(g).mean(axis=(0, 1))
            grad_accum += g * batch_x.shape[0]
            n_samples += batch_x.shape[0]
    if n_samples == 0:
        return [0.0] * n_features
    importance = grad_accum / n_samples
    total = importance.sum()
    if total > 0:
        importance = importance / total
    return [float(v) for v in importance]


def train_lstm(
    df: pd.DataFrame,
    seq_len: int = 7,
    hidden_dim: int = 64,
    num_layers: int = 2,
    epochs: int = 80,
    batch_size: int = 8,
    learning_rate: float = 1e-3,
    seed: int = 42,
) -> TrainedModel:
    torch.manual_seed(seed)
    np.random.seed(seed)

    df = df.sort_values("date").reset_index(drop=True)
    feature_scaler = MinMaxScaler(feature_range=(0, 1))
    target_scaler = MinMaxScaler(feature_range=(0, 1))

    scaled_features = feature_scaler.fit_transform(
        df[FEATURE_COLUMNS].values.astype(np.float32)
    ).astype(np.float32)
    scaled_targets = target_scaler.fit_transform(
        df[ALL_TARGETS].values.astype(np.float32)
    ).astype(np.float32)

    X_list: List[np.ndarray] = []
    y_list: List[np.ndarray] = []
    for i in range(seq_len, len(df)):
        X_list.append(scaled_features[i - seq_len : i])
        y_list.append(scaled_targets[i])
    if not X_list:
        raise ValueError("数据量不足以构造序列，请增加历史记录条数（至少需要 seq_len + 1 条）。")

    X = torch.tensor(np.stack(X_list), dtype=torch.float32)
    y = torch.tensor(np.stack(y_list), dtype=torch.float32)

    dataset = SequenceDataset(X, y)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = MultiTaskLSTM(
        input_dim=len(FEATURE_COLUMNS),
        hidden_dim=hidden_dim,
        num_layers=num_layers,
        profile_dim=len(PROFILE_TARGETS),
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fn = nn.MSELoss()

    loss_history: List[float] = []
    peak_loss_history: List[float] = []
    income_loss_history: List[float] = []
    engagement_loss_history: List[float] = []
    profile_loss_history: List[float] = []

    model.train()
    for _ in range(epochs):
        epoch_total = 0.0
        epoch_peak = 0.0
        epoch_income = 0.0
        epoch_eng = 0.0
        epoch_prof = 0.0
        n_batches = 0
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            peak_pred, income_pred, eng_pred, prof_pred = model(batch_x)
            peak_loss = loss_fn(peak_pred, batch_y[:, 0])
            income_loss = loss_fn(income_pred, batch_y[:, 1])
            eng_loss = loss_fn(eng_pred, batch_y[:, 2])
            prof_loss = loss_fn(prof_pred, batch_y[:, 3:])
            total_loss = peak_loss + income_loss + eng_loss + prof_loss
            total_loss.backward()
            optimizer.step()
            epoch_total += float(total_loss.item())
            epoch_peak += float(peak_loss.item())
            epoch_income += float(income_loss.item())
            epoch_eng += float(eng_loss.item())
            epoch_prof += float(prof_loss.item())
            n_batches += 1
        n = max(1, n_batches)
        loss_history.append(epoch_total / n)
        peak_loss_history.append(epoch_peak / n)
        income_loss_history.append(epoch_income / n)
        engagement_loss_history.append(epoch_eng / n)
        profile_loss_history.append(epoch_prof / n)

    feature_importance = _extract_feature_importance(model, loader, FEATURE_COLUMNS)

    return TrainedModel(
        model=model,
        feature_scaler=feature_scaler,
        target_scaler=target_scaler,
        feature_columns=FEATURE_COLUMNS,
        target_columns=ALL_TARGETS,
        seq_len=seq_len,
        loss_history=loss_history,
        peak_loss_history=peak_loss_history,
        income_loss_history=income_loss_history,
        engagement_loss_history=engagement_loss_history,
        profile_loss_history=profile_loss_history,
        feature_importance=feature_importance,
    )
