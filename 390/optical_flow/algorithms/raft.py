import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F


class FeatureEncoder(nn.Module):
    """
    RAFT 特征编码器
    使用 6 层卷积提取 1/8 分辨率特征图
    """

    def __init__(self, in_channels: int = 3, hidden_dim: int = 128, out_dim: int = 256):
        super().__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=7, stride=2, padding=3),
            nn.GroupNorm(8, 64),
            nn.ReLU(inplace=True),
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(64, 96, kernel_size=3, stride=2, padding=1),
            nn.GroupNorm(8, 96),
            nn.ReLU(inplace=True),
        )
        self.conv3 = nn.Sequential(
            nn.Conv2d(96, 128, kernel_size=3, stride=2, padding=1),
            nn.GroupNorm(8, 128),
            nn.ReLU(inplace=True),
        )
        self.conv4 = nn.Sequential(
            nn.Conv2d(128, hidden_dim, kernel_size=3, padding=1),
            nn.GroupNorm(8, hidden_dim),
            nn.ReLU(inplace=True),
        )
        self.conv5 = nn.Sequential(
            nn.Conv2d(hidden_dim, hidden_dim, kernel_size=3, padding=1),
            nn.GroupNorm(8, hidden_dim),
            nn.ReLU(inplace=True),
        )
        self.conv6 = nn.Conv2d(hidden_dim, out_dim, kernel_size=3, padding=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        x = self.conv5(x)
        x = self.conv6(x)
        return x


class ContextEncoder(nn.Module):
    """
    RAFT 上下文编码器
    与特征编码器结构类似, 输出用于 GRU 更新的上下文特征
    """

    def __init__(self, in_channels: int = 3, hidden_dim: int = 128):
        super().__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=7, stride=2, padding=3),
            nn.GroupNorm(8, 64),
            nn.ReLU(inplace=True),
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(64, 96, kernel_size=3, stride=2, padding=1),
            nn.GroupNorm(8, 96),
            nn.ReLU(inplace=True),
        )
        self.conv3 = nn.Sequential(
            nn.Conv2d(96, 128, kernel_size=3, stride=2, padding=1),
            nn.GroupNorm(8, 128),
            nn.ReLU(inplace=True),
        )
        self.conv4 = nn.Sequential(
            nn.Conv2d(128, hidden_dim, kernel_size=3, padding=1),
            nn.GroupNorm(8, hidden_dim),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        return x


class CorrelationLayer:
    """
    相关性体构建层
    计算两个特征图之间的全对相关性 (all-pairs correlation)
    """

    def __init__(self, num_levels: int = 4, radius: int = 4):
        self.num_levels = num_levels
        self.radius = radius

    def __call__(self, fmap1: torch.Tensor, fmap2: torch.Tensor) -> list:
        """
        构建相关性金字塔

        参数:
            fmap1: 第一帧特征图 (B, C, H, W)
            fmap2: 第二帧特征图 (B, C, H, W)

        返回:
            相关性金字塔列表, 每级为 (B, H, W, H, W)
        """
        B, C, H, W = fmap1.shape
        fmap1 = fmap1.view(B, C, H * W)
        fmap2 = fmap2.view(B, C, H * W)

        corr = torch.matmul(fmap1.transpose(1, 2), fmap2)
        corr = corr.view(B, H, W, H, W)
        corr = corr / torch.sqrt(torch.tensor(C, dtype=corr.dtype, device=corr.device))

        corr_pyramid = [corr]
        for _ in range(self.num_levels - 1):
            corr = F.avg_pool3d(
                corr.view(B * H * W, 1, H, W, 1),
                kernel_size=(2, 2, 1),
                stride=(2, 2, 1),
            )
            corr = corr.view(B, H, W, corr.shape[2], corr.shape[3])
            corr_pyramid.append(corr)

        return corr_pyramid

    def sample(self, corr_pyramid: list, coords: torch.Tensor) -> torch.Tensor:
        """
        从相关性金字塔中采样

        参数:
            corr_pyramid: 相关性金字塔
            coords: 采样坐标 (B, 2, H, W)

        返回:
            采样后的相关性特征
        """
        B, _, H, W = coords.shape
        out_pyramid = []

        for i, corr in enumerate(corr_pyramid):
            r = self.radius
            dx = torch.linspace(-r, r, 2 * r + 1)
            dy = torch.linspace(-r, r, 2 * r + 1)
            delta = torch.stack(torch.meshgrid(dy, dx, indexing='ij'), dim=0).to(coords.device)
            delta = delta.view(1, 2, 2 * r + 1, 2 * r + 1)

            center = coords[:, :, None, None, :, :]
            delta_lvl = delta.view(1, 2, 2 * r + 1, 2 * r + 1, 1, 1)
            coords_lvl = center + delta_lvl

            coords_lvl = coords_lvl.permute(0, 4, 5, 2, 3, 1).reshape(B, H, W, -1, 2)
            coords_lvl = coords_lvl.reshape(B * H * W, -1, 2)

            corr_lvl = corr.reshape(B * H * W, corr.shape[3], corr.shape[4])

            x = coords_lvl[..., 0]
            y = coords_lvl[..., 1]
            x0 = torch.floor(x).long()
            x1 = x0 + 1
            y0 = torch.floor(y).long()
            y1 = y0 + 1

            x0 = x0.clamp(0, corr_lvl.shape[2] - 1)
            x1 = x1.clamp(0, corr_lvl.shape[2] - 1)
            y0 = y0.clamp(0, corr_lvl.shape[1] - 1)
            y1 = y1.clamp(0, corr_lvl.shape[1] - 1)

            x0_safe = x0.clamp(0, corr_lvl.shape[2] - 1)
            x1_safe = x1.clamp(0, corr_lvl.shape[2] - 1)
            y0_safe = y0.clamp(0, corr_lvl.shape[1] - 1)
            y1_safe = y1.clamp(0, corr_lvl.shape[1] - 1)

            la = (x1.float() - x) * (y1.float() - y)
            lb = (x1.float() - x) * (y - y0.float())
            lc = (x - x0.float()) * (y1.float() - y)
            ld = (x - x0.float()) * (y - y0.float())

            batch_idx = torch.arange(B * H * W, device=corr.device).view(-1, 1)
            v00 = corr_lvl[batch_idx, y0_safe, x0_safe]
            v01 = corr_lvl[batch_idx, y0_safe, x1_safe]
            v10 = corr_lvl[batch_idx, y1_safe, x0_safe]
            v11 = corr_lvl[batch_idx, y1_safe, x1_safe]

            sampled = la * v00 + lb * v01 + lc * v10 + ld * v11
            sampled = sampled.view(B, H, W, -1)
            sampled = sampled.permute(0, 3, 1, 2)
            out_pyramid.append(sampled)

        return torch.cat(out_pyramid, dim=1)


class ConvGRU(nn.Module):
    """
    卷积 GRU 更新器
    使用卷积替代全连接层, 保持空间结构
    """

    def __init__(self, hidden_dim: int = 128, input_dim: int = 256):
        super().__init__()
        self.conv_z = nn.Conv2d(hidden_dim + input_dim, hidden_dim, kernel_size=3, padding=1)
        self.conv_r = nn.Conv2d(hidden_dim + input_dim, hidden_dim, kernel_size=3, padding=1)
        self.conv_h = nn.Conv2d(hidden_dim + input_dim, hidden_dim, kernel_size=3, padding=1)

    def forward(self, h: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        hx = torch.cat([h, x], dim=1)
        z = torch.sigmoid(self.conv_z(hx))
        r = torch.sigmoid(self.conv_r(hx))
        h_new = torch.tanh(self.conv_h(torch.cat([r * h, x], dim=1)))
        h = (1 - z) * h + z * h_new
        return h


class FlowHead(nn.Module):
    """
    光流预测头
    从 GRU 隐藏状态预测光流增量
    """

    def __init__(self, hidden_dim: int = 128):
        super().__init__()
        self.conv1 = nn.Conv2d(hidden_dim, hidden_dim // 2, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(hidden_dim // 2, 2, kernel_size=3, padding=1)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.conv1(h))
        flow = self.conv2(x)
        return flow


class RAFT(nn.Module):
    """
    RAFT: Recurrent All-Pairs Field Transforms 光流估计

    核心思想:
        1. 提取两帧的特征图
        2. 构建 4D 相关性体
        3. 使用 GRU 迭代更新光流
        4. 从粗到细上采样预测

    参数:
        hidden_dim: GRU 隐藏层维度
        feature_dim: 特征编码器输出维度
        num_iters: GRU 迭代次数
        num_levels: 相关性金字塔层数
        corr_radius: 相关性采样半径
        device: 计算设备
    """

    def __init__(
        self,
        hidden_dim: int = 128,
        feature_dim: int = 256,
        num_iters: int = 12,
        num_levels: int = 4,
        corr_radius: int = 4,
        device: torch.device | str = 'auto',
        fp16: bool = False,
    ):
        super().__init__()

        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        self.fp16 = fp16 and self.device.type == 'cuda'
        self.dtype = torch.float16 if self.fp16 else torch.float32

        self.hidden_dim = hidden_dim
        self.num_iters = num_iters
        self.num_levels = num_levels
        self.corr_radius = corr_radius

        self.feature_encoder = FeatureEncoder(in_channels=3, hidden_dim=hidden_dim, out_dim=feature_dim)
        self.context_encoder = ContextEncoder(in_channels=3, hidden_dim=hidden_dim)

        self.corr_layer = CorrelationLayer(num_levels=num_levels, radius=corr_radius)
        corr_dim = num_levels * (2 * corr_radius + 1) ** 2
        input_dim = hidden_dim + corr_dim + 2

        self.gru = ConvGRU(hidden_dim=hidden_dim, input_dim=input_dim)
        self.flow_head = FlowHead(hidden_dim=hidden_dim)

        self.to(self.device, dtype=self.dtype)

        self.prev_gray = None
        self._trained = False

    def forward(self, frame1: torch.Tensor, frame2: torch.Tensor) -> list:
        """
        前向传播

        参数:
            frame1: 第一帧 (B, 3, H, W), 归一化到 [0, 1]
            frame2: 第二帧 (B, 3, H, W), 归一化到 [0, 1]

        返回:
            光流预测列表, 每个元素为 (B, 2, H, W), 从小到大
        """
        frame1 = frame1.to(self.dtype)
        frame2 = frame2.to(self.dtype)

        fmap1 = self.feature_encoder(frame1)
        fmap2 = self.feature_encoder(frame2)
        cnet = self.context_encoder(frame1)

        if self.fp16:
            fmap1_corr = fmap1.float()
            fmap2_corr = fmap2.float()
            corr_pyramid = self.corr_layer(fmap1_corr, fmap2_corr)
        else:
            corr_pyramid = self.corr_layer(fmap1, fmap2)

        B, _, H, W = fmap1.shape
        coords = torch.meshgrid(
            torch.arange(H, device=self.device, dtype=self.dtype),
            torch.arange(W, device=self.device, dtype=self.dtype),
            indexing='ij',
        )
        coords = torch.stack([coords[1], coords[0]], dim=0).unsqueeze(0).expand(B, -1, -1, -1)

        h = torch.zeros(B, self.hidden_dim, H, W, device=self.device, dtype=self.dtype)
        flow = torch.zeros(B, 2, H, W, device=self.device, dtype=self.dtype)

        flow_predictions = []

        for _ in range(self.num_iters):
            flow = flow.detach()
            coords_sample = coords + flow

            if self.fp16:
                coords_sample_fp32 = coords_sample.float()
                corr_features = self.corr_layer.sample(corr_pyramid, coords_sample_fp32)
                corr_features = corr_features.to(self.dtype)
            else:
                corr_features = self.corr_layer.sample(corr_pyramid, coords_sample)

            gru_input = torch.cat([cnet, corr_features, flow], dim=1)

            h = self.gru(h, gru_input)
            delta_flow = self.flow_head(h)
            flow = flow + delta_flow

            flow_up = F.interpolate(
                flow.float(), scale_factor=8, mode='bilinear', align_corners=False
            )
            flow_up = flow_up * 8.0
            flow_predictions.append(flow_up.to(self.dtype))

        return flow_predictions

    def compute(self, frame: np.ndarray, prev_frame: np.ndarray | None = None) -> np.ndarray:
        """
        计算两帧之间的光流 (推理接口)

        参数:
            frame: 当前帧 (BGR, H, W, 3)
            prev_frame: 上一帧, 若为 None 则使用内部缓存

        返回:
            光流场, 形状为 (H, W, 2), 通道为 (u, v)
        """
        if prev_frame is not None:
            prev = prev_frame
        elif self.prev_gray is not None:
            prev = self.prev_gray
        else:
            self.prev_gray = frame
            h, w = frame.shape[:2]
            return np.zeros((h, w, 2), dtype=np.float32)

        tensor1 = self._preprocess(prev)
        tensor2 = self._preprocess(frame)

        self.eval()
        with torch.no_grad():
            with torch.cuda.amp.autocast(enabled=self.fp16):
                flow_predictions = self.forward(tensor1, tensor2)

        flow_final = flow_predictions[-1][0].float().cpu().numpy()
        flow_final = flow_final.transpose(1, 2, 0)

        self.prev_gray = frame
        return flow_final.astype(np.float32)

    def _preprocess(self, frame: np.ndarray) -> torch.Tensor:
        """
        图像预处理: BGR -> RGB, 归一化, 调整大小到 8 的倍数
        """
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        else:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        h, w = frame.shape[:2]
        h_new = (h // 8) * 8
        w_new = (w // 8) * 8
        if h != h_new or w != w_new:
            frame = cv2.resize(frame, (w_new, h_new))

        frame = frame.astype(np.float32) / 255.0
        tensor = torch.from_numpy(frame).permute(2, 0, 1).unsqueeze(0)
        return tensor.to(self.device)

    def reset(self):
        """重置内部状态"""
        self.prev_gray = None