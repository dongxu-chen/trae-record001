import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Tuple, Dict, Optional


class MotionEstimation(nn.Module):
    def __init__(self, in_channels: int = 6, base_channels: int = 64):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, base_channels, kernel_size=5, stride=2, padding=2)
        self.conv2 = nn.Conv2d(base_channels, base_channels, kernel_size=3, stride=1, padding=1)
        self.conv3 = nn.Conv2d(base_channels, base_channels, kernel_size=5, stride=2, padding=2)
        self.conv4 = nn.Conv2d(base_channels, base_channels, kernel_size=3, stride=1, padding=1)
        self.conv5 = nn.Conv2d(base_channels, base_channels // 2, kernel_size=3, stride=1, padding=1)
        self.conv6 = nn.Conv2d(base_channels // 2, 2, kernel_size=3, stride=1, padding=1)
        self.lrelu = nn.LeakyReLU(0.1, inplace=True)

    def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor:
        x = torch.cat([x1, x2], dim=1)
        x = self.lrelu(self.conv1(x))
        x = self.lrelu(self.conv2(x))
        x = self.lrelu(self.conv3(x))
        x = self.lrelu(self.conv4(x))
        x = self.lrelu(self.conv5(x))
        flow = self.conv6(x)
        return flow


class MotionCompensation(nn.Module):
    def __init__(self):
        super().__init__()

    def warp(self, x: torch.Tensor, flow: torch.Tensor) -> torch.Tensor:
        B, C, H, W = x.size()
        flow = F.interpolate(flow, size=(H, W), mode='bilinear', align_corners=False)

        grid_y, grid_x = torch.meshgrid(
            torch.arange(H, device=x.device, dtype=x.dtype),
            torch.arange(W, device=x.device, dtype=x.dtype),
            indexing='ij'
        )
        grid = torch.stack((grid_x, grid_y), dim=0)
        grid = grid.unsqueeze(0).repeat(B, 1, 1, 1)

        vgrid = grid + flow
        vgrid_x = 2.0 * vgrid[:, 0, :, :] / max(W - 1, 1) - 1.0
        vgrid_y = 2.0 * vgrid[:, 1, :, :] / max(H - 1, 1) - 1.0
        vgrid_scaled = torch.stack((vgrid_x, vgrid_y), dim=3)

        output = F.grid_sample(x, vgrid_scaled, mode='bilinear', padding_mode='border', align_corners=False)
        return output

    def forward(self, x: torch.Tensor, flow: torch.Tensor) -> torch.Tensor:
        return self.warp(x, flow)


class TemporalAlignmentModule(nn.Module):
    def __init__(self, channels: int = 64, num_frames: int = 3):
        super().__init__()
        self.channels = channels
        self.num_frames = num_frames

        self.flow_confidence = nn.Sequential(
            nn.Conv2d(3, channels // 2, kernel_size=3, stride=1, padding=1),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(channels // 2, channels // 4, kernel_size=3, stride=1, padding=1),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(channels // 4, 2, kernel_size=3, stride=1, padding=1),
            nn.Sigmoid()
        )

        self.feature_aligner = nn.Sequential(
            nn.Conv2d(channels * num_frames, channels * 2, kernel_size=3, stride=1, padding=1),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(channels * 2, channels, kernel_size=3, stride=1, padding=1),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(channels, channels, kernel_size=3, stride=1, padding=1),
        )

        self.blur_removal = nn.Sequential(
            nn.Conv2d(9, channels, kernel_size=3, stride=1, padding=1),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(channels, channels // 2, kernel_size=3, stride=1, padding=1),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(channels // 2, 3, kernel_size=3, stride=1, padding=1),
            nn.Tanh()
        )

    def calculate_flow_confidence(self, prev_flow: torch.Tensor,
                                   next_flow: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        flow_diff = torch.abs(prev_flow - next_flow)
        flow_mag = torch.sqrt(prev_flow[:, 0:1] ** 2 + prev_flow[:, 1:2] ** 2) + \
                   torch.sqrt(next_flow[:, 0:1] ** 2 + next_flow[:, 1:2] ** 2)

        confidence_input = torch.cat([flow_diff, flow_mag], dim=1)
        confidence = self.flow_confidence(confidence_input)

        conf_prev = confidence[:, 0:1]
        conf_next = confidence[:, 1:2]

        return conf_prev, conf_next

    def align_features(self, prev_feat: torch.Tensor, curr_feat: torch.Tensor,
                        next_feat: torch.Tensor) -> torch.Tensor:
        combined = torch.cat([prev_feat, curr_feat, next_feat], dim=1)
        aligned = self.feature_aligner(combined)
        return aligned + curr_feat

    def remove_blur(self, aligned_frame: torch.Tensor, prev_frame: torch.Tensor,
                    next_frame: torch.Tensor) -> torch.Tensor:
        combined = torch.cat([aligned_frame, prev_frame, next_frame], dim=1)
        residual = self.blur_removal(combined)
        return torch.clamp(aligned_frame + residual, 0, 1)

    def forward(self, prev_warped: torch.Tensor, next_warped: torch.Tensor,
                prev_flow: torch.Tensor, next_flow: torch.Tensor,
                prev_feat: torch.Tensor, curr_feat: torch.Tensor,
                next_feat: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        conf_prev, conf_next = self.calculate_flow_confidence(prev_flow, next_flow)

        aligned_feat = self.align_features(prev_feat, curr_feat, next_feat)

        _, _, H, W = prev_warped.size()
        conf_prev = F.interpolate(conf_prev, size=(H, W), mode='bilinear', align_corners=False)
        conf_next = F.interpolate(conf_next, size=(H, W), mode='bilinear', align_corners=False)

        conf_sum = conf_prev + conf_next + 1e-6
        aligned_frame = (conf_prev * prev_warped + conf_next * next_warped) / conf_sum

        deblurred = self.remove_blur(aligned_frame, prev_warped, next_warped)

        return deblurred, aligned_feat


class ResidualBlock(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, stride=1, padding=1)
        self.lrelu = nn.LeakyReLU(0.1, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.lrelu(self.conv1(x))
        out = self.conv2(out)
        out += residual
        return out


class MultiScaleFeatureFusion(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, use_temporal_alignment: bool = True):
        super().__init__()
        self.use_temporal_alignment = use_temporal_alignment
        ch1 = out_channels // 3
        ch2 = out_channels // 3
        ch3 = out_channels - ch1 - ch2

        self.conv1x1 = nn.Conv2d(in_channels, ch1, kernel_size=1, stride=1, padding=0)
        self.conv3x3 = nn.Conv2d(in_channels, ch2, kernel_size=3, stride=1, padding=1)
        self.conv5x5 = nn.Conv2d(in_channels, ch3, kernel_size=5, stride=1, padding=2)

        self.temporal_att = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(out_channels, out_channels // 8, kernel_size=1),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(out_channels // 8, out_channels, kernel_size=1),
            nn.Sigmoid()
        ) if use_temporal_alignment else None

        self.lrelu = nn.LeakyReLU(0.1, inplace=True)

    def forward(self, x: torch.Tensor, prev_feat: torch.Tensor = None,
                next_feat: torch.Tensor = None) -> torch.Tensor:
        feat1 = self.lrelu(self.conv1x1(x))
        feat2 = self.lrelu(self.conv3x3(x))
        feat3 = self.lrelu(self.conv5x5(x))

        fused = torch.cat([feat1, feat2, feat3], dim=1)

        if self.use_temporal_alignment and prev_feat is not None and next_feat is not None:
            temporal_diff = torch.abs(prev_feat - next_feat)
            att_input = fused + temporal_diff
            att = self.temporal_att(att_input)
            fused = fused * att + fused

        return fused


class FeatureExtractor(nn.Module):
    def __init__(self, in_channels: int = 3, base_channels: int = 64):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, base_channels, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv2d(base_channels, base_channels, kernel_size=3, stride=1, padding=1)
        self.conv3 = nn.Conv2d(base_channels, base_channels, kernel_size=3, stride=1, padding=1)
        self.lrelu = nn.LeakyReLU(0.1, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.lrelu(self.conv1(x))
        x = self.lrelu(self.conv2(x))
        x = self.conv3(x)
        return x


class FrameInterpolation(nn.Module):
    def __init__(self, in_channels: int = 9, base_channels: int = 64,
                 use_temporal_alignment: bool = True):
        super().__init__()
        self.use_temporal_alignment = use_temporal_alignment

        self.feature_extractor = FeatureExtractor(in_channels=3, base_channels=base_channels)

        self.conv_in = nn.Conv2d(in_channels, base_channels, kernel_size=3, stride=1, padding=1)
        self.msff = MultiScaleFeatureFusion(base_channels, base_channels, use_temporal_alignment)
        self.res_blocks = nn.Sequential(*[ResidualBlock(base_channels) for _ in range(3)])
        self.conv_out = nn.Conv2d(base_channels, 3, kernel_size=3, stride=1, padding=1)

        if use_temporal_alignment:
            self.temporal_alignment = TemporalAlignmentModule(channels=base_channels, num_frames=3)

        self.lrelu = nn.LeakyReLU(0.1, inplace=True)

    def forward(self, prev_frame: torch.Tensor, next_frame: torch.Tensor,
                prev_warped: torch.Tensor, next_warped: torch.Tensor,
                prev_flow: torch.Tensor = None, next_flow: torch.Tensor = None) -> torch.Tensor:
        prev_feat = self.feature_extractor(prev_frame)
        next_feat = self.feature_extractor(next_frame)

        x = torch.cat([prev_frame, next_frame, prev_warped, next_warped,
                       torch.abs(prev_warped - next_warped)], dim=1)
        x = self.lrelu(self.conv_in(x))

        if self.use_temporal_alignment and prev_flow is not None and next_flow is not None:
            avg_frame = (prev_warped + next_warped) / 2
            avg_feat = self.feature_extractor(avg_frame)

            deblurred, aligned_feat = self.temporal_alignment(
                prev_warped, next_warped, prev_flow, next_flow,
                prev_feat, avg_feat, next_feat
            )

            x = self.msff(x, prev_feat, next_feat)
            x = x + aligned_feat
        else:
            x = self.msff(x)

        x = self.res_blocks(x)
        residual = self.conv_out(x)

        if self.use_temporal_alignment and prev_flow is not None:
            base_frame = deblurred
        else:
            base_frame = (prev_warped + next_warped) / 2

        interpolated = base_frame + residual
        return torch.clamp(interpolated, 0, 1)


class SuperResolution(nn.Module):
    def __init__(self, in_channels: int = 3, base_channels: int = 64,
                 num_res_blocks: int = 6, scale_factor: int = 2,
                 use_temporal_alignment: bool = True):
        super().__init__()
        self.scale_factor = scale_factor
        self.use_temporal_alignment = use_temporal_alignment

        self.conv_in = nn.Conv2d(in_channels, base_channels, kernel_size=3, stride=1, padding=1)
        self.msff1 = MultiScaleFeatureFusion(base_channels, base_channels, use_temporal_alignment)
        self.res_blocks = nn.Sequential(*[ResidualBlock(base_channels) for _ in range(num_res_blocks)])
        self.msff2 = MultiScaleFeatureFusion(base_channels, base_channels, use_temporal_alignment)

        up_modules = []
        for _ in range(scale_factor // 2 if scale_factor > 1 else 0):
            up_modules.extend([
                nn.Conv2d(base_channels, base_channels * 4, kernel_size=3, stride=1, padding=1),
                nn.PixelShuffle(2),
                nn.LeakyReLU(0.1, inplace=True)
            ])
        self.upsample = nn.Sequential(*up_modules)

        self.conv_out = nn.Conv2d(base_channels, 3, kernel_size=3, stride=1, padding=1)
        self.lrelu = nn.LeakyReLU(0.1, inplace=True)

    def forward(self, x: torch.Tensor, prev_feat: torch.Tensor = None,
                next_feat: torch.Tensor = None) -> torch.Tensor:
        x_input = x
        x = self.lrelu(self.conv_in(x))
        x = self.msff1(x, prev_feat, next_feat)
        x = self.res_blocks(x)
        x = self.msff2(x, prev_feat, next_feat)
        x = self.upsample(x)
        x = self.conv_out(x)

        if self.scale_factor == 1:
            return x

        x_bicubic = F.interpolate(x_input, scale_factor=self.scale_factor,
                                  mode='bicubic', align_corners=False)
        return torch.clamp(x + x_bicubic, 0, 1)


class QualityScaleBalancer(nn.Module):
    def __init__(self, base_channels: int = 64):
        super().__init__()
        self.gate = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(base_channels * 2, base_channels),
            nn.ReLU(inplace=True),
            nn.Linear(base_channels, 2),
            nn.Softmax(dim=1)
        )

    def forward(self, interp_feat: torch.Tensor, sr_feat: torch.Tensor,
                quality_weight: float = 0.5) -> Tuple[torch.Tensor, torch.Tensor]:
        combined = torch.cat([
            interp_feat.mean(dim=[2, 3], keepdim=False),
            sr_feat.mean(dim=[2, 3], keepdim=False)
        ], dim=1)
        gate_values = self.gate(combined)
        alpha = quality_weight * gate_values[:, 0:1].unsqueeze(-1).unsqueeze(-1)
        beta = (1 - quality_weight) * gate_values[:, 1:2].unsqueeze(-1).unsqueeze(-1)
        balanced_interp = interp_feat * (1 + alpha)
        balanced_sr = sr_feat * (1 + beta)
        return balanced_interp, balanced_sr


class LightweightVESPCN(nn.Module):
    def __init__(self, num_channels: int = 3, scale_factor: int = 2,
                 use_temporal_alignment: bool = False):
        super().__init__()
        self.scale_factor = scale_factor
        self.use_temporal_alignment = use_temporal_alignment
        lightweight_ch = 32

        self.motion_estimation = MotionEstimation(in_channels=num_channels * 2,
                                                   base_channels=lightweight_ch)
        self.motion_compensation = MotionCompensation()

        self.interp_conv_in = nn.Conv2d(num_channels * 5, lightweight_ch, 3, 1, 1)
        self.interp_res = nn.Sequential(*[ResidualBlock(lightweight_ch) for _ in range(2)])
        self.interp_conv_out = nn.Conv2d(lightweight_ch, num_channels, 3, 1, 1)

        up_modules = []
        for _ in range(scale_factor // 2 if scale_factor > 1 else 0):
            up_modules.extend([
                nn.Conv2d(lightweight_ch, lightweight_ch * 4, 3, 1, 1),
                nn.PixelShuffle(2),
                nn.LeakyReLU(0.1, inplace=True)
            ])
        self.sr_conv_in = nn.Conv2d(num_channels, lightweight_ch, 3, 1, 1)
        self.sr_res = nn.Sequential(*[ResidualBlock(lightweight_ch) for _ in range(3)])
        self.sr_upsample = nn.Sequential(*up_modules)
        self.sr_conv_out = nn.Conv2d(lightweight_ch, num_channels, 3, 1, 1)

        self.lrelu = nn.LeakyReLU(0.1, inplace=True)

    def interpolate_frame(self, prev_frame: torch.Tensor, next_frame: torch.Tensor) -> torch.Tensor:
        flow = self.motion_estimation(prev_frame, next_frame)
        prev_warped = self.motion_compensation(prev_frame, flow)
        next_warped = self.motion_compensation(next_frame, -flow)

        x = torch.cat([prev_frame, next_frame, prev_warped, next_warped,
                       torch.abs(prev_warped - next_warped)], dim=1)
        x = self.lrelu(self.interp_conv_in(x))
        x = self.interp_res(x)
        residual = self.interp_conv_out(x)
        base = (prev_warped + next_warped) / 2
        return torch.clamp(base + residual, 0, 1)

    def enhance_resolution(self, frame: torch.Tensor) -> torch.Tensor:
        x_input = frame
        x = self.lrelu(self.sr_conv_in(frame))
        x = self.sr_res(x)
        x = self.sr_upsample(x)
        x = self.sr_conv_out(x)

        if self.scale_factor == 1:
            return x

        x_bicubic = F.interpolate(x_input, scale_factor=self.scale_factor,
                                  mode='bicubic', align_corners=False)
        return torch.clamp(x + x_bicubic, 0, 1)

    def forward(self, frames: torch.Tensor) -> List[torch.Tensor]:
        B, T, C, H, W = frames.size()
        enhanced_frames = []

        for i in range(T - 1):
            curr = frames[:, i, :, :, :]
            nxt = frames[:, i + 1, :, :, :]

            enhanced_curr = self.enhance_resolution(curr)
            enhanced_frames.append(enhanced_curr)

            interp = self.interpolate_frame(curr, nxt)
            enhanced_interp = self.enhance_resolution(interp)
            enhanced_frames.append(enhanced_interp)

        last = frames[:, -1, :, :, :]
        enhanced_last = self.enhance_resolution(last)
        enhanced_frames.append(enhanced_last)

        return enhanced_frames

    def process_single_frame(self, frame: torch.Tensor) -> torch.Tensor:
        return self.enhance_resolution(frame)


class VESPCN(nn.Module):
    def __init__(self, num_channels: int = 3, num_frames: int = 3,
                 base_channels: int = 64, num_residual_blocks: int = 6,
                 scale_factor: int = 2, use_temporal_alignment: bool = True,
                 quality_weight: float = 0.5):
        super().__init__()
        self.num_frames = num_frames
        self.scale_factor = scale_factor
        self.use_temporal_alignment = use_temporal_alignment
        self.quality_weight = quality_weight

        self.motion_estimation = MotionEstimation(in_channels=num_channels * 2,
                                                   base_channels=base_channels)
        self.motion_compensation = MotionCompensation()
        self.frame_interpolation = FrameInterpolation(in_channels=num_channels * 5,
                                                       base_channels=base_channels,
                                                       use_temporal_alignment=use_temporal_alignment)
        self.super_resolution = SuperResolution(in_channels=num_channels,
                                                 base_channels=base_channels,
                                                 num_res_blocks=num_residual_blocks,
                                                 scale_factor=scale_factor,
                                                 use_temporal_alignment=use_temporal_alignment)
        self.feature_extractor = FeatureExtractor(in_channels=num_channels,
                                                   base_channels=base_channels)
        self.quality_scale_balancer = QualityScaleBalancer(base_channels=base_channels)

    def set_quality_weight(self, weight: float):
        self.quality_weight = max(0.0, min(1.0, weight))

    def get_quality_weight(self) -> float:
        return self.quality_weight

    def estimate_and_warp(self, frame1: torch.Tensor, frame2: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        flow = self.motion_estimation(frame1, frame2)
        warped = self.motion_compensation(frame1, flow)
        return warped, flow

    def interpolate_frame(self, prev_frame: torch.Tensor, next_frame: torch.Tensor) -> torch.Tensor:
        prev_warped, prev_flow = self.estimate_and_warp(prev_frame, next_frame)
        next_warped, next_flow = self.estimate_and_warp(next_frame, prev_frame)

        if self.use_temporal_alignment:
            interpolated = self.frame_interpolation(
                prev_frame, next_frame, prev_warped, next_warped,
                prev_flow, next_flow
            )
        else:
            interpolated = self.frame_interpolation(
                prev_frame, next_frame, prev_warped, next_warped
            )
        return interpolated

    def enhance_resolution(self, frame: torch.Tensor, prev_feat: torch.Tensor = None,
                           next_feat: torch.Tensor = None) -> torch.Tensor:
        return self.super_resolution(frame, prev_feat, next_feat)

    def forward(self, frames: torch.Tensor) -> List[torch.Tensor]:
        B, T, C, H, W = frames.size()
        assert T >= 2, "Need at least 2 frames for interpolation"

        enhanced_frames = []
        features = []

        for t in range(T):
            feat = self.feature_extractor(frames[:, t, :, :, :])
            features.append(feat)

        for i in range(T - 1):
            curr_frame = frames[:, i, :, :, :]
            next_frame = frames[:, i + 1, :, :, :]

            prev_feat = features[max(0, i - 1)] if i > 0 else features[i]
            curr_feat = features[i]
            next_feat = features[i + 1]

            enhanced_curr = self.enhance_resolution(curr_frame, prev_feat, next_feat)
            enhanced_frames.append(enhanced_curr)

            interpolated = self.interpolate_frame(curr_frame, next_frame)
            interp_feat = self.feature_extractor(interpolated)
            enhanced_interp = self.enhance_resolution(interpolated, curr_feat, next_feat)

            if self.quality_weight != 0.5 and self.training:
                balanced_interp_feat, balanced_sr_feat = self.quality_scale_balancer(
                    interp_feat, self.feature_extractor(enhanced_interp),
                    quality_weight=self.quality_weight
                )

            enhanced_frames.append(enhanced_interp)

        last_frame = frames[:, -1, :, :, :]
        prev_feat_last = features[-2] if T >= 2 else features[-1]
        last_feat = features[-1]
        enhanced_last = self.enhance_resolution(last_frame, prev_feat_last, last_feat)
        enhanced_frames.append(enhanced_last)

        return enhanced_frames

    def forward_with_intermediates(self, frames: torch.Tensor) -> Dict[str, torch.Tensor]:
        B, T, C, H, W = frames.size()
        features = []
        for t in range(T):
            feat = self.feature_extractor(frames[:, t, :, :, :])
            features.append(feat)

        interp_outputs = []
        sr_outputs = []

        for i in range(T - 1):
            curr_frame = frames[:, i, :, :, :]
            next_frame = frames[:, i + 1, :, :, :]

            interpolated = self.interpolate_frame(curr_frame, next_frame)
            interp_outputs.append(interpolated)

            curr_feat = features[i]
            next_feat = features[i + 1]
            enhanced_interp = self.enhance_resolution(interpolated, curr_feat, next_feat)
            sr_outputs.append(enhanced_interp)

        return {
            'interpolated_frames': interp_outputs,
            'sr_frames': sr_outputs,
            'features': features,
        }

    def process_single_frame(self, frame: torch.Tensor) -> torch.Tensor:
        return self.enhance_resolution(frame)

    def get_num_output_frames(self, num_input_frames: int) -> int:
        return num_input_frames * 2 - 1


def create_vespcn_model(scale_factor: int = 2, pretrained: bool = False,
                        weights_path: str = None, device: str = 'cuda',
                        use_temporal_alignment: bool = True,
                        quality_weight: float = 0.5,
                        base_channels: int = 64,
                        num_residual_blocks: int = 6) -> VESPCN:
    if device == 'cuda' and not torch.cuda.is_available():
        device = 'cpu'

    model = VESPCN(scale_factor=scale_factor,
                   use_temporal_alignment=use_temporal_alignment,
                   quality_weight=quality_weight,
                   base_channels=base_channels,
                   num_residual_blocks=num_residual_blocks).to(device)

    if pretrained and weights_path:
        state_dict = torch.load(weights_path, map_location=device)
        model.load_state_dict(state_dict)

    return model


def create_lightweight_model(scale_factor: int = 2, device: str = 'cuda',
                              use_temporal_alignment: bool = False) -> LightweightVESPCN:
    if device == 'cuda' and not torch.cuda.is_available():
        device = 'cpu'

    model = LightweightVESPCN(scale_factor=scale_factor,
                               use_temporal_alignment=use_temporal_alignment).to(device)
    return model


def initialize_weights(m: nn.Module):
    if isinstance(m, nn.Conv2d):
        nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu')
        if m.bias is not None:
            nn.init.constant_(m.bias, 0)
    elif isinstance(m, nn.Linear):
        nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
        if m.bias is not None:
            nn.init.constant_(m.bias, 0)


if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    model = VESPCN(scale_factor=2, use_temporal_alignment=True, quality_weight=0.5).to(device)
    model.apply(initialize_weights)

    batch_size = 1
    num_frames = 3
    height, width = 64, 64

    test_input = torch.randn(batch_size, num_frames, 3, height, width).to(device)

    with torch.no_grad():
        outputs = model(test_input)

    print(f"\nInput shape: {test_input.shape}")
    print(f"Output frames: {len(outputs)}")
    for i, out in enumerate(outputs):
        print(f"  Output frame {i} shape: {out.shape}")

    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\nTrainable params: {num_params:,}")

    lw_model = create_lightweight_model(scale_factor=2, device=str(device))
    lw_model.apply(initialize_weights)
    lw_params = sum(p.numel() for p in lw_model.parameters() if p.requires_grad)
    print(f"Lightweight model params: {lw_params:,}")

    print("\nModel test passed!")
