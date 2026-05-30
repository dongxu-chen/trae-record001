import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import cv2


class ChannelAttention(nn.Module):
    def __init__(self, in_channels, reduction=16):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        mid = max(in_channels // reduction, 8)
        self.fc = nn.Sequential(
            nn.Conv2d(in_channels, mid, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(mid, in_channels, 1, bias=False),
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = self.fc(self.avg_pool(x))
        max_out = self.fc(self.max_pool(x))
        return x * self.sigmoid(avg_out + max_out)


class SpatialAttention(nn.Module):
    def __init__(self, kernel_size=7):
        super().__init__()
        padding = kernel_size // 2
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=padding, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        attn = self.sigmoid(self.conv(torch.cat([avg_out, max_out], dim=1)))
        return x * attn


class CBAM(nn.Module):
    def __init__(self, in_channels, reduction=16):
        super().__init__()
        self.ca = ChannelAttention(in_channels, reduction)
        self.sa = SpatialAttention()

    def forward(self, x):
        x = self.ca(x)
        x = self.sa(x)
        return x


class DoubleConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.net(x)


class FocusFusionNet(nn.Module):
    def __init__(self, in_channels=3, base_channels=64):
        super().__init__()
        self.enc1 = DoubleConv(in_channels * 2, base_channels)
        self.enc2 = DoubleConv(base_channels, base_channels * 2)
        self.enc3 = DoubleConv(base_channels * 2, base_channels * 4)

        self.cbam1 = CBAM(base_channels)
        self.cbam2 = CBAM(base_channels * 2)
        self.cbam3 = CBAM(base_channels * 4)

        self.pool = nn.MaxPool2d(2)
        self.up3 = nn.ConvTranspose2d(base_channels * 4, base_channels * 2, 2, stride=2)
        self.up2 = nn.ConvTranspose2d(base_channels * 2, base_channels, 2, stride=2)

        self.dec3 = DoubleConv(base_channels * 4, base_channels * 2)
        self.dec2 = DoubleConv(base_channels * 2, base_channels)
        self.dec1 = DoubleConv(base_channels, base_channels)

        self.out_conv = nn.Sequential(
            nn.Conv2d(base_channels, in_channels, 1),
            nn.Sigmoid(),
        )

        self.bottleneck = DoubleConv(base_channels * 4, base_channels * 4)

    def forward(self, img_a, img_b):
        x = torch.cat([img_a, img_b], dim=1)

        e1 = self.enc1(x)
        e1 = self.cbam1(e1)

        e2 = self.enc2(self.pool(e1))
        e2 = self.cbam2(e2)

        e3 = self.enc3(self.pool(e2))
        e3 = self.cbam3(e3)

        b = self.bottleneck(self.pool(e3))

        d3 = self.up3(b)
        d3 = self._pad_cat(d3, e3)
        d3 = self.dec3(d3)

        d2 = self.up2(d3)
        d2 = self._pad_cat(d2, e2)
        d2 = self.dec2(d2)

        d1 = self._pad_cat(d2, e1)
        d1 = self.dec1(d1)

        weight = self.out_conv(d1)
        fused = weight * img_a + (1 - weight) * img_b
        return fused, weight

    @staticmethod
    def _pad_cat(x, skip):
        dy = skip.size(2) - x.size(2)
        dx = skip.size(3) - x.size(3)
        x = F.pad(x, [dx // 2, dx - dx // 2, dy // 2, dy - dy // 2])
        return torch.cat([x, skip], dim=1)


class DLFusion:
    def __init__(self, device=None):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        self.model = FocusFusionNet().to(self.device)
        self.model.eval()
        self._init_weights()

    def _init_weights(self):
        for m in self.model.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def _preprocess(self, image):
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        img = image.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        return torch.from_numpy(img).unsqueeze(0).to(self.device)

    def _postprocess(self, tensor):
        img = tensor.squeeze(0).cpu().detach().numpy()
        img = np.transpose(img, (1, 2, 0))
        img = np.clip(img * 255, 0, 255).astype(np.uint8)
        return img

    def fuse_pair(self, img_a, img_b):
        tensor_a = self._preprocess(img_a)
        tensor_b = self._preprocess(img_b)
        with torch.no_grad():
            fused, weight_map = self.model(tensor_a, tensor_b)
        result = self._postprocess(fused)
        weight = self._postprocess(weight_map)
        return result, weight

    def fuse(self, images):
        if len(images) < 2:
            raise ValueError("Need at least 2 images for fusion")
        result = images[0]
        for i in range(1, len(images)):
            result, _ = self.fuse_pair(result, images[i])
        return result

    def get_weight_map(self, img_a, img_b):
        tensor_a = self._preprocess(img_a)
        tensor_b = self._preprocess(img_b)
        with torch.no_grad():
            _, weight_map = self.model(tensor_a, tensor_b)
        return self._postprocess(weight_map)

    def train_on_pair(self, img_a, img_b, focus_map_a, focus_map_b, epochs=10, lr=1e-3):
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        tensor_a = self._preprocess(img_a)
        tensor_b = self._preprocess(img_b)
        gt_a = self._preprocess(focus_map_a)
        gt_b = self._preprocess(focus_map_b)

        for epoch in range(epochs):
            optimizer.zero_grad()
            fused, weight = self.model(tensor_a, tensor_b)
            loss_recon = F.mse_loss(fused, gt_a * tensor_a + gt_b * tensor_b)
            loss = loss_recon
            loss.backward()
            optimizer.step()

        self.model.eval()
        return loss.item()
