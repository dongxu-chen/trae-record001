import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvBnReLU(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=1, pad=1):
        super().__init__()
        self.conv = nn.Conv2d(
            in_channels, out_channels, kernel_size, stride=stride, padding=pad, bias=False
        )
        self.bn = nn.BatchNorm2d(out_channels)

    def forward(self, x):
        return F.relu(self.bn(self.conv(x)), inplace=True)


class ConvBnReLU3D(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=1, pad=1):
        super().__init__()
        self.conv = nn.Conv3d(
            in_channels, out_channels, kernel_size, stride=stride, padding=pad, bias=False
        )
        self.bn = nn.BatchNorm3d(out_channels)

    def forward(self, x):
        return F.relu(self.bn(self.conv(x)), inplace=True)


class FeatureNet(nn.Module):
    def __init__(self, base_channels=32):
        super().__init__()
        self.conv0 = ConvBnReLU(3, base_channels, 3, 1, 1)
        self.conv1 = ConvBnReLU(base_channels, base_channels, 3, 1, 1)
        self.conv2 = ConvBnReLU(base_channels, base_channels, 3, 2, 1)

        self.conv3 = ConvBnReLU(base_channels, base_channels * 2, 3, 1, 1)
        self.conv4 = ConvBnReLU(base_channels * 2, base_channels * 2, 3, 1, 1)
        self.conv5 = ConvBnReLU(base_channels * 2, base_channels * 2, 3, 2, 1)

        self.conv6 = ConvBnReLU(base_channels * 2, base_channels * 4, 3, 1, 1)
        self.conv7 = ConvBnReLU(base_channels * 4, base_channels * 4, 3, 1, 1)

        self.inner1 = nn.Conv2d(base_channels * 4, base_channels, 1, 1, 0)
        self.inner2 = nn.Conv2d(base_channels * 2, base_channels, 1, 1, 0)
        self.out_conv = ConvBnReLU(base_channels * 3, base_channels, 3, 1, 1)

    def forward(self, x):
        conv0 = self.conv0(x)
        conv1 = self.conv1(conv0)
        conv2 = self.conv2(conv1)

        conv3 = self.conv3(conv2)
        conv4 = self.conv4(conv3)
        conv5 = self.conv5(conv4)

        conv6 = self.conv6(conv5)
        conv7 = self.conv7(conv6)

        feat1 = self.inner1(conv7)
        feat1_up = F.interpolate(feat1, scale_factor=2, mode="bilinear", align_corners=True)
        feat2 = self.inner2(conv5)
        feat_cat = torch.cat([feat1_up, feat2, conv4], dim=1)
        feat_out = self.out_conv(feat_cat)

        return feat_out


class CostVolumeNet(nn.Module):
    def __init__(self, in_channels=32, base_channels=8):
        super().__init__()
        self.conv0 = ConvBnReLU3D(in_channels, base_channels, 3, 1, 1)
        self.conv1 = ConvBnReLU3D(base_channels, base_channels, 3, 2, 1)

        self.conv2 = ConvBnReLU3D(base_channels, base_channels * 2, 3, 1, 1)
        self.conv3 = ConvBnReLU3D(base_channels * 2, base_channels * 2, 3, 2, 1)

        self.conv4 = ConvBnReLU3D(base_channels * 2, base_channels * 4, 3, 1, 1)
        self.conv5 = ConvBnReLU3D(base_channels * 4, base_channels * 4, 3, 2, 1)

        self.conv6 = ConvBnReLU3D(base_channels * 4, base_channels * 8, 3, 1, 1)

        self.inner1 = nn.Conv3d(base_channels * 8, base_channels * 4, 1, 1, 0)
        self.inner2 = nn.Conv3d(base_channels * 4, base_channels * 2, 1, 1, 0)
        self.inner3 = nn.Conv3d(base_channels * 2, base_channels, 1, 1, 0)

        self.out_conv = nn.Conv3d(base_channels, 1, 3, 1, 1, bias=False)

    def forward(self, cost_volume):
        conv0 = self.conv0(cost_volume)
        conv1 = self.conv1(conv0)

        conv2 = self.conv2(conv1)
        conv3 = self.conv3(conv2)

        conv4 = self.conv4(conv3)
        conv5 = self.conv5(conv4)

        conv6 = self.conv6(conv5)

        inner1 = self.inner1(conv6)
        inner1_up = F.interpolate(inner1, scale_factor=2, mode="trilinear", align_corners=True)
        deconv1 = F.relu(inner1_up + conv4, inplace=True)

        inner2 = self.inner2(deconv1)
        inner2_up = F.interpolate(inner2, scale_factor=2, mode="trilinear", align_corners=True)
        deconv2 = F.relu(inner2_up + conv2, inplace=True)

        inner3 = self.inner3(deconv2)
        inner3_up = F.interpolate(inner3, scale_factor=2, mode="trilinear", align_corners=True)
        deconv3 = F.relu(inner3_up + conv0, inplace=True)

        prob_volume_pre = self.out_conv(deconv3)
        prob_volume = prob_volume_pre.squeeze(1)

        return prob_volume


class DepthRefineNet(nn.Module):
    def __init__(self, in_channels=32):
        super().__init__()
        self.conv0 = ConvBnReLU(in_channels + 1, in_channels, 3, 1, 1)
        self.conv1 = ConvBnReLU(in_channels, in_channels, 3, 1, 1)
        self.conv2 = ConvBnReLU(in_channels, in_channels, 3, 1, 1)
        self.out_conv = nn.Conv2d(in_channels, 1, 3, 1, 1)

    def forward(self, feat, depth_init):
        concat = torch.cat([feat, depth_init.unsqueeze(1)], dim=1)
        out = self.conv0(concat)
        out = self.conv1(out)
        out = self.conv2(out)
        residual = self.out_conv(out)
        depth_refined = depth_init + residual.squeeze(1)
        return depth_refined


class MVSNet(nn.Module):
    def __init__(
        self,
        feat_channels=32,
        cost_volume_channels=8,
        refine=True,
    ):
        super().__init__()
        self.feat_channels = feat_channels
        self.refine = refine

        self.feature_net = FeatureNet(base_channels=feat_channels)
        self.cost_volume_net = CostVolumeNet(
            in_channels=feat_channels, base_channels=cost_volume_channels
        )

        if self.refine:
            self.refine_net = DepthRefineNet(in_channels=feat_channels)

    def build_cost_volume(
        self, ref_feat, src_feats, ref_proj, src_projs, depth_values
    ):
        B, C, H, W = ref_feat.shape
        num_depth = depth_values.shape[1]

        ref_proj_ext = ref_proj[:, :3, :]
        src_proj_exts = [sp[:, :3, :] for sp in src_projs]

        ref_proj_inv = torch.inverse(ref_proj_ext)

        cost_volume = ref_feat.new_zeros(B, C, num_depth, H, W)

        for d in range(num_depth):
            depth_val = depth_values[:, d]
            depth_scaled = depth_val.view(B, 1, 1, 1).repeat(1, 1, H, W)
            pts_grid = self.depth_to_grid(depth_scaled, ref_proj_inv, ref_proj_ext, H, W)

            for src_idx, (src_feat, src_proj_ext) in enumerate(
                zip(src_feats, src_proj_exts)
            ):
                warped_proj = src_proj_ext @ ref_proj_inv
                warped_grid = self.warp_grid(pts_grid, warped_proj, H, W)
                warped_feat = F.grid_sample(
                    src_feat, warped_grid, mode="bilinear", padding_mode="zeros", align_corners=True
                )
                cost_volume[:, :, d, :, :] += warped_feat

        num_src = len(src_feats)
        if num_src > 0:
            cost_volume = cost_volume / num_src

        volume_sq = torch.mean(cost_volume ** 2, dim=1, keepdim=True)
        ref_sq = ref_feat.unsqueeze(2) ** 2
        variance = volume_sq - 2 * cost_volume + ref_sq
        variance = torch.clamp(variance, min=1e-7)

        return variance

    def depth_to_grid(self, depth, ref_proj_inv, ref_proj_ext, H, W):
        B = depth.shape[0]
        y, x = torch.meshgrid(
            torch.arange(0, H, device=depth.device, dtype=torch.float32),
            torch.arange(0, W, device=depth.device, dtype=torch.float32),
            indexing="ij",
        )
        ones = torch.ones_like(x)
        pix_coords = torch.stack([x, y, ones], dim=0).unsqueeze(0).repeat(B, 1, 1, 1)
        pix_coords[:, 0] = pix_coords[:, 0] / (W - 1) * 2 - 1
        pix_coords[:, 1] = pix_coords[:, 1] / (H - 1) * 2 - 1

        depth_expanded = depth.squeeze(1)
        pts_homo = torch.cat([pix_coords, depth_expanded.unsqueeze(1)], dim=1)
        pts_homo_flat = pts_homo.view(B, 4, -1)

        ref_proj_inv_flat = ref_proj_inv.unsqueeze(-1)
        pts_cam = ref_proj_inv @ pts_homo_flat

        pts_cam_homo = torch.cat(
            [pts_cam[:, :3], torch.ones(B, 1, pts_cam.shape[2], device=pts_cam.device)],
            dim=1,
        )
        pts_cam_homo = pts_cam_homo.view(B, 4, H, W)

        grid = pts_cam_homo[:, :2] / (pts_cam_homo[:, 2:3] + 1e-8)
        grid[:, 0] = grid[:, 0] / (W - 1) * 2 - 1
        grid[:, 1] = grid[:, 1] / (H - 1) * 2 - 1

        return grid.permute(0, 2, 3, 1)

    def warp_grid(self, pts_grid, warped_proj, H, W):
        B = pts_grid.shape[0]
        grid_flat = pts_grid.permute(0, 3, 1, 2).reshape(B, 2, -1)

        ones = torch.ones(B, 1, grid_flat.shape[2], device=grid_flat.device)
        grid_homo = torch.cat([grid_flat, ones], dim=1)

        warped = warped_proj[:, :2, :] @ grid_homo
        warped_norm = warped / (warped[:, 2:3, :] + 1e-8)
        warped_norm[:, 0] = warped_norm[:, 0] / (W - 1) * 2 - 1
        warped_norm[:, 1] = warped_norm[:, 1] / (H - 1) * 2 - 1

        return warped_norm.permute(0, 2, 1).view(B, H, W, 2)

    def forward(self, ref_img, src_imgs, ref_proj, src_projs, depth_values):
        B = ref_img.shape[0]

        ref_feat = self.feature_net(ref_img)
        src_feats = [self.feature_net(src) for src in src_imgs]

        cost_volume = self.build_cost_volume(
            ref_feat, src_feats, ref_proj, src_projs, depth_values
        )

        prob_volume = self.cost_volume_net(cost_volume)

        prob_volume_softmax = F.softmax(prob_volume, dim=1)
        depth_index = torch.arange(
            0, prob_volume_softmax.shape[1],
            device=prob_volume_softmax.device, dtype=torch.float32
        )
        depth_est = torch.sum(
            prob_volume_softmax * depth_index.view(1, -1, 1, 1), dim=1
        )

        depth_values_mid = (depth_values[:, 1:] + depth_values[:, :-1]) / 2
        depth_values_mid = torch.cat(
            [2 * depth_values[:, :1] - depth_values_mid[:, :1], depth_values_mid], dim=1
        )

        interval_scale = (depth_values[:, 1:] - depth_values[:, :-1]).mean(dim=1, keepdim=True)
        depth_est_scaled = depth_values[:, 0:1].unsqueeze(-1) + depth_est * interval_scale.unsqueeze(-1)
        depth_est_scaled = depth_est_scaled.squeeze(2)

        if self.refine:
            depth_est_refined = self.refine_net(ref_feat, depth_est_scaled)
            return depth_est_refined, prob_volume_softmax
        else:
            return depth_est_scaled, prob_volume_softmax
