import numpy as np
import cv2
import time
from typing import Optional, Tuple, List
from dataclasses import dataclass, field

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class DLConfig:
    use_gpu: bool = True
    model_type: str = "unet_refine"
    in_channels: int = 3
    base_channels: int = 16
    num_levels: int = 4
    dropout: float = 0.2
    weight_weak_texture: float = 2.0
    edge_weight: float = 1.5
    sr_scale: int = 4
    sr_channels: int = 32
    sr_blocks: int = 6


class ConvBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.conv(x)


class DownBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.down = nn.Sequential(
            nn.MaxPool2d(2),
            ConvBlock(in_ch, out_ch),
        )

    def forward(self, x):
        return self.down(x)


class UpBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=True)
        self.conv = ConvBlock(in_ch, out_ch)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]
        x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2, diffY // 2, diffY - diffY // 2])
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class UNetDispRefine(nn.Module):
    def __init__(self, config: DLConfig):
        super().__init__()
        self.config = config
        ch = config.base_channels
        self.inc = ConvBlock(6, ch)
        self.down1 = DownBlock(ch, ch * 2)
        self.down2 = DownBlock(ch * 2, ch * 4)
        self.down3 = DownBlock(ch * 4, ch * 8)
        self.up1 = UpBlock(ch * 12, ch * 4)
        self.up2 = UpBlock(ch * 6, ch * 2)
        self.up3 = UpBlock(ch * 3, ch)
        self.outc = nn.Sequential(
            nn.Conv2d(ch, 1, 3, padding=1),
            nn.Tanh(),
        )
        self.conf_head = nn.Sequential(
            nn.Conv2d(ch, 1, 3, padding=1),
            nn.Sigmoid(),
        )

    def forward(self, img_l, img_r, disp_init):
        h, w = img_l.shape[2], img_l.shape[3]
        disp_ = disp_init.unsqueeze(1) / 100.0
        x = torch.cat([img_l, img_r, disp_], dim=1)
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x = self.up1(x4, x3)
        x = self.up2(x, x2)
        x = self.up3(x, x1)
        disp_residual = self.outc(x) * 10.0
        confidence = self.conf_head(x)
        disp_refined = disp_init.unsqueeze(1) + disp_residual
        return disp_refined.squeeze(1), confidence.squeeze(1)


class ResidualBlock(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += residual
        return out


class DepthSuperRes(nn.Module):
    def __init__(self, config: DLConfig):
        super().__init__()
        self.config = config
        ch = config.sr_channels
        scale = config.sr_scale
        self.head = nn.Conv2d(1, ch, 3, padding=1)
        self.residuals = nn.Sequential(*[
            ResidualBlock(ch) for _ in range(config.sr_blocks)
        ])
        self.mid_conv = nn.Conv2d(ch, ch, 3, padding=1)
        self.upsample = nn.Sequential(
            nn.Upsample(scale_factor=scale, mode="bicubic", align_corners=True),
            nn.Conv2d(ch, ch // 2, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(ch // 2, 1, 3, padding=1),
        )

    def forward(self, depth_low, guidance=None):
        x = depth_low.unsqueeze(1)
        feat = self.head(x)
        res = self.residuals(feat)
        feat = self.mid_conv(res) + feat
        depth_hr = self.upsample(feat)
        return depth_hr.squeeze(1)


class DeepSGMRefiner:
    def __init__(self, config: DLConfig, device: str = "auto"):
        self.config = config
        self.device = self._get_device(device) if TORCH_AVAILABLE else "cpu"
        self.model = None
        self.sr_model = None
        if TORCH_AVAILABLE:
            self._init_models()

    def _get_device(self, device: str) -> str:
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            return "cpu"
        return device

    def _init_models(self):
        self.model = UNetDispRefine(self.config).to(self.device)
        self.sr_model = DepthSuperRes(self.config).to(self.device)
        self.model.eval()
        self.sr_model.eval()
        self._init_dummy_weights()

    def _init_dummy_weights(self):
        def init_weights(m):
            if isinstance(m, (nn.Conv2d, nn.Linear)):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
        self.model.apply(init_weights)
        self.sr_model.apply(init_weights)

    @staticmethod
    def _to_tensor(arr: np.ndarray, device: str) -> torch.Tensor:
        t = torch.from_numpy(arr).float().to(device)
        if len(t.shape) == 2:
            t = t.unsqueeze(0).unsqueeze(0)
        elif len(t.shape) == 3:
            t = t.permute(2, 0, 1).unsqueeze(0)
        return t / 255.0 if t.max() > 1.0 else t

    @staticmethod
    def _to_numpy(t: torch.Tensor) -> np.ndarray:
        return t.detach().cpu().numpy()[0]

    def refine_disparity(self, img_l: np.ndarray, img_r: np.ndarray,
                          disp_init: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not TORCH_AVAILABLE or self.model is None:
            return disp_init, np.ones_like(disp_init)
        with torch.no_grad():
            img_l_t = self._to_tensor(img_l, self.device)
            img_r_t = self._to_tensor(img_r, self.device)
            disp_t = torch.from_numpy(disp_init).float().unsqueeze(0).to(self.device)
            disp_ref, conf = self.model(img_l_t, img_r_t, disp_t)
            disp_np = self._to_numpy(disp_ref)
            conf_np = self._to_numpy(conf)
            disp_np[disp_init <= 0] = 0
            return disp_np, conf_np

    def super_resolve_depth(self, depth: np.ndarray, scale: Optional[int] = None) -> np.ndarray:
        if not TORCH_AVAILABLE or self.sr_model is None:
            s = scale or self.config.sr_scale
            return cv2.resize(depth, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
        s = scale or self.config.sr_scale
        with torch.no_grad():
            depth_t = torch.from_numpy(depth).float().unsqueeze(0).unsqueeze(0).to(self.device)
            if s != self.config.sr_scale:
                depth_hr = F.interpolate(depth_t, scale_factor=s,
                                         mode="bicubic", align_corners=True)
            else:
                depth_hr = self.sr_model(depth_t)
            result = depth_hr.detach().cpu().numpy()[0, 0]
            result[result < 0] = 0
            return result


class CUDAStereoSGM:
    def __init__(self, min_disparity: int = 0, num_disparities: int = 64,
                 block_size: int = 5, use_cuda: bool = True):
        self.min_disparity = min_disparity
        self.num_disparities = num_disparities
        self.block_size = block_size
        self.use_cuda = use_cuda and self._check_cuda()
        self.matcher = self._create_matcher()

    @staticmethod
    def _check_cuda() -> bool:
        try:
            return cv2.cuda.getCudaEnabledDeviceCount() > 0
        except Exception:
            return False

    def _create_matcher(self):
        if self.use_cuda:
            try:
                return cv2.cuda.StereoSGBM_create(
                    minDisparity=self.min_disparity,
                    numDisparities=self.num_disparities,
                    blockSize=self.block_size,
                    P1=8 * 3 * self.block_size * self.block_size,
                    P2=32 * 3 * self.block_size * self.block_size,
                )
            except Exception:
                pass
        return cv2.StereoSGBM_create(
            minDisparity=self.min_disparity,
            numDisparities=self.num_disparities,
            blockSize=self.block_size,
            P1=8 * self.block_size * self.block_size,
            P2=32 * self.block_size * self.block_size,
            disp12MaxDiff=1,
            preFilterCap=63,
            uniquenessRatio=10,
            speckleWindowSize=100,
            speckleRange=32,
            mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY,
        )

    @staticmethod
    def _to_gray(img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img

    def compute(self, img_l: np.ndarray, img_r: np.ndarray) -> np.ndarray:
        gray_l = self._to_gray(img_l)
        gray_r = self._to_gray(img_r)
        if self.use_cuda:
            gpu_l = cv2.cuda_GpuMat()
            gpu_r = cv2.cuda_GpuMat()
            gpu_l.upload(gray_l)
            gpu_r.upload(gray_r)
            disp_gpu = self.matcher.compute(gpu_l, gpu_r)
            disp = disp_gpu.download().astype(np.float32) / 16.0
        else:
            disp = self.matcher.compute(gray_l, gray_r).astype(np.float32) / 16.0
        return disp

    def benchmark(self, img_l: np.ndarray, img_r: np.ndarray,
                  iterations: int = 100) -> float:
        for _ in range(5):
            self.compute(img_l, img_r)
        t0 = time.perf_counter()
        for _ in range(iterations):
            self.compute(img_l, img_r)
        elapsed = time.perf_counter() - t0
        return iterations / elapsed


class RealTimeStereo:
    def __init__(self, min_disparity: int = 0, num_disparities: int = 64,
                 block_size: int = 5, target_fps: int = 30):
        self.target_fps = target_fps
        self.cuda_matcher = CUDAStereoSGM(min_disparity, num_disparities, block_size)
        self.use_cuda = self.cuda_matcher.use_cuda
        self.frame_times = []
        self.last_time = time.perf_counter()

    def process_frame(self, img_l: np.ndarray, img_r: np.ndarray) -> dict:
        t0 = time.perf_counter()
        disparity = self.cuda_matcher.compute(img_l, img_r)
        dt = time.perf_counter() - t0
        self.frame_times.append(dt)
        if len(self.frame_times) > 100:
            self.frame_times.pop(0)
        return {
            "disparity": disparity,
            "time_ms": dt * 1000,
            "fps": 1.0 / dt if dt > 0 else 0,
            "avg_fps": len(self.frame_times) / sum(self.frame_times) if self.frame_times else 0,
        }

    def benchmark(self, img_l: np.ndarray, img_r: np.ndarray,
                  seconds: float = 3.0) -> dict:
        for _ in range(5):
            self.cuda_matcher.compute(img_l, img_r)
        count = 0
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < seconds:
            self.cuda_matcher.compute(img_l, img_r)
            count += 1
        elapsed = time.perf_counter() - t0
        return {
            "fps": count / elapsed,
            "frames": count,
            "seconds": elapsed,
            "use_cuda": self.use_cuda,
        }


class WeakTextureEnhancer:
    def __init__(self, gradient_threshold: float = 15.0):
        self.gradient_threshold = gradient_threshold

    def detect_weak_texture(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
        grad = np.sqrt(gx * gx + gy * gy)
        weak_mask = grad < self.gradient_threshold
        return weak_mask.astype(np.float32)

    def enhance(self, img_l: np.ndarray, img_r: np.ndarray,
                disparity: np.ndarray, confidence: Optional[np.ndarray] = None) -> np.ndarray:
        weak_mask = self.detect_weak_texture(img_l)
        result = disparity.copy()
        kernel = np.ones((5, 5), np.uint8)
        dilated_weak = cv2.dilate(weak_mask, kernel, iterations=2) > 0.5
        result[dilated_weak] = cv2.medianBlur(disparity, 5)[dilated_weak]
        if confidence is not None:
            low_conf = confidence < 0.3
            filled = cv2.inpaint(
                result.astype(np.float32),
                low_conf.astype(np.uint8),
                inpaintRadius=5,
                flags=cv2.INPAINT_TELEA,
            )
            result[low_conf] = filled[low_conf]
        return result


class FastBilateralSolver:
    def __init__(self, sigma_spatial: float = 8.0, sigma_range: float = 0.05,
                 iterations: int = 3):
        self.sigma_spatial = sigma_spatial
        self.sigma_range = sigma_range
        self.iterations = iterations

    def solve(self, disparity: np.ndarray, guidance: np.ndarray,
              confidence: Optional[np.ndarray] = None) -> np.ndarray:
        result = disparity.copy()
        if confidence is None:
            confidence = np.ones_like(disparity)
        conf_normalized = confidence / confidence.max() if confidence.max() > 0 else confidence
        valid = disparity > 0
        gray_guide = cv2.cvtColor(guidance, cv2.COLOR_BGR2GRAY) if len(guidance.shape) == 3 else guidance
        for _ in range(self.iterations):
            d_bf = cv2.bilateralFilter(
                result.astype(np.float32),
                d=-1,
                sigmaColor=self.sigma_range * 255,
                sigmaSpace=self.sigma_spatial,
            )
            blend = 0.5 + 0.5 * conf_normalized
            result = result * blend + d_bf * (1 - blend)
            result[~valid] = 0
        return result


class SREnhancer:
    def __init__(self, scale: int = 4, method: str = "hybrid"):
        self.scale = scale
        self.method = method
        self.dl_model = None

    def _espcn_x4(self, depth: np.ndarray) -> np.ndarray:
        h, w = depth.shape
        padded = np.pad(depth, ((2, 2), (2, 2)), mode="reflect")
        result = np.zeros((h * self.scale, w * self.scale), dtype=np.float32)
        for ky in range(self.scale):
            for kx in range(self.scale):
                src = padded[2 + ky : 2 + ky + h, 2 + kx : 2 + kx + w]
                src = cv2.GaussianBlur(src, (3, 3), 0.5)
                result[ky :: self.scale, kx :: self.scale] = src
        return cv2.GaussianBlur(result, (3, 3), 0.5)

    def _guided_upsample(self, depth: np.ndarray, guidance: np.ndarray) -> np.ndarray:
        h, w = depth.shape
        h_hr, w_hr = h * self.scale, w * self.scale
        depth_bicubic = cv2.resize(depth, (w_hr, h_hr), interpolation=cv2.INTER_CUBIC)
        if len(guidance.shape) == 3:
            guide_gray = cv2.cvtColor(guidance, cv2.COLOR_BGR2GRAY)
        else:
            guide_gray = guidance
        guide_hr = cv2.resize(guide_gray, (w_hr, h_hr), interpolation=cv2.INTER_CUBIC)
        guidance_f = guide_hr.astype(np.float32) / 255.0
        depth_f = depth_bicubic.astype(np.float32)
        edge_mask = cv2.Canny(guide_hr, 50, 150) > 0
        result = depth_f.copy()
        for _ in range(5):
            filtered = cv2.bilateralFilter(depth_f, d=9, sigmaColor=2.0, sigmaSpace=10.0)
            result = np.where(edge_mask, filtered, depth_f * 0.8 + filtered * 0.2)
        return result

    def enhance(self, depth: np.ndarray, guidance: Optional[np.ndarray] = None,
                method: Optional[str] = None) -> np.ndarray:
        m = method or self.method
        if m == "bicubic":
            return cv2.resize(depth, None, fx=self.scale, fy=self.scale,
                              interpolation=cv2.INTER_CUBIC)
        elif m == "espcn":
            return self._espcn_x4(depth)
        elif m == "guided" and guidance is not None:
            return self._guided_upsample(depth, guidance)
        else:
            bicubic = cv2.resize(depth, None, fx=self.scale, fy=self.scale,
                                 interpolation=cv2.INTER_CUBIC)
            if guidance is not None:
                guide_hr = cv2.resize(guidance, (bicubic.shape[1], bicubic.shape[0]))
                refined = cv2.bilateralFilter(bicubic.astype(np.float32),
                                              d=9, sigmaColor=3.0, sigmaSpace=15.0)
                edge_mask = cv2.Canny(cv2.cvtColor(guide_hr, cv2.COLOR_BGR2GRAY), 50, 150) > 0
                return np.where(edge_mask, refined, bicubic)
            return bicubic
