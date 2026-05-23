import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualDenseBlock(nn.Module):
    def __init__(self, num_feat=64, num_grow_ch=32):
        super(ResidualDenseBlock, self).__init__()
        self.conv1 = nn.Conv2d(num_feat, num_grow_ch, 3, 1, 1)
        self.conv2 = nn.Conv2d(num_feat + num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv3 = nn.Conv2d(num_feat + 2 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv4 = nn.Conv2d(num_feat + 3 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv5 = nn.Conv2d(num_feat + 4 * num_grow_ch, num_feat, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, num_feat, num_grow_ch=32):
        super(RRDB, self).__init__()
        self.rdb1 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb2 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb3 = ResidualDenseBlock(num_feat, num_grow_ch)

    def forward(self, x):
        out = self.rdb1(x)
        out = self.rdb2(out)
        out = self.rdb3(out)
        return out * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(self, num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4):
        super(RRDBNet, self).__init__()
        self.scale = scale
        
        self.conv_first = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)
        
        self.body = nn.Sequential(*[RRDB(num_feat, num_grow_ch) for _ in range(num_block)])
        
        self.conv_body = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        
        self.conv_up1 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_hr = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)
        
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)
        
        self.pixel_shuffle = nn.PixelShuffle(2)

    def forward(self, x):
        feat = self.conv_first(x)
        body_feat = self.conv_body(self.body(feat))
        feat = feat + body_feat
        
        if self.scale >= 2:
            feat = self.lrelu(self.conv_up1(self.pixel_shuffle(feat)))
        if self.scale >= 4:
            feat = self.lrelu(self.conv_up2(self.pixel_shuffle(feat)))
        
        out = self.conv_last(self.lrelu(self.conv_hr(feat)))
        return torch.clamp(out, 0.0, 1.0)


def rrdbnet_x4(**kwargs):
    return RRDBNet(scale=4, **kwargs)


def rrdbnet_x2(**kwargs):
    return RRDBNet(scale=2, **kwargs)


class SmallRRDBTeacher(nn.Module):
    def __init__(self, scale=4, num_feat=48, num_block=6):
        super(SmallRRDBTeacher, self).__init__()
        self.scale = scale
        
        self.conv_first = nn.Conv2d(3, num_feat, 3, 1, 1)
        
        self.body = nn.Sequential(*[RRDB(num_feat, 24) for _ in range(num_block)])
        
        self.conv_body = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        
        if scale >= 2:
            self.upconv1 = nn.Conv2d(num_feat, num_feat * 4, 3, 1, 1)
            self.pixel_shuffle1 = nn.PixelShuffle(2)
        if scale >= 4:
            self.upconv2 = nn.Conv2d(num_feat, num_feat * 4, 3, 1, 1)
            self.pixel_shuffle2 = nn.PixelShuffle(2)
        
        self.conv_hr = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_last = nn.Conv2d(num_feat, 3, 3, 1, 1)
        
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        feat = self.conv_first(x)
        body_feat = self.conv_body(self.body(feat))
        feat = feat + body_feat
        
        if self.scale >= 2:
            feat = self.lrelu(self.pixel_shuffle1(self.upconv1(feat)))
        if self.scale >= 4:
            feat = self.lrelu(self.pixel_shuffle2(self.upconv2(feat)))
        
        out = self.conv_last(self.lrelu(self.conv_hr(feat)))
        return torch.clamp(out, 0.0, 1.0)


def small_teacher_x4(**kwargs):
    return SmallRRDBTeacher(scale=4, num_feat=48, num_block=6, **kwargs)


def small_teacher_x2(**kwargs):
    return SmallRRDBTeacher(scale=2, num_feat=48, num_block=6, **kwargs)


if __name__ == '__main__':
    model = SmallRRDBTeacher(scale=4, num_feat=48, num_block=6)
    x = torch.randn(1, 3, 64, 64)
    out = model(x)
    print(f'Teacher model input: {x.shape}')
    print(f'Teacher model output: {out.shape}')
    print(f'Teacher parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M')
