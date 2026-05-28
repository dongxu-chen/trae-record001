import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Tuple, Optional


def initialize_weights(net):
    for m in net.modules():
        if isinstance(m, nn.Conv2d):
            nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.BatchNorm2d):
            nn.init.ones_(m.weight)
            nn.init.zeros_(m.bias)


class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, stride, padding=1)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        if stride != 1 or in_channels != out_channels:
            self.downsample = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1, stride),
                nn.BatchNorm2d(out_channels)
            )
        else:
            self.downsample = None
    
    def forward(self, x):
        identity = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        
        if self.downsample is not None:
            identity = self.downsample(x)
        
        out += identity
        out = self.relu(out)
        return out


class FeatureExtractor(nn.Module):
    def __init__(self, output_dim=256, small=False):
        super().__init__()
        self.small = small
        
        if small:
            self.layer1 = nn.Sequential(
                nn.Conv2d(3, 32, 7, 2, padding=3),
                nn.BatchNorm2d(32),
                nn.ReLU(inplace=True)
            )
            self.layer2 = ResidualBlock(32, 64, stride=2)
            self.layer3 = ResidualBlock(64, 96, stride=2)
            self.layer4 = ResidualBlock(96, 128, stride=1)
            self.conv_out = nn.Conv2d(128, output_dim, 3, padding=1)
        else:
            self.layer1 = nn.Sequential(
                nn.Conv2d(3, 64, 7, 2, padding=3),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True)
            )
            self.layer2 = ResidualBlock(64, 128, stride=2)
            self.layer3 = ResidualBlock(128, 256, stride=2)
            self.layer4 = ResidualBlock(256, 256, stride=1)
            self.conv_out = nn.Conv2d(256, output_dim, 3, padding=1)
    
    def forward(self, x):
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.conv_out(x)
        return x


class ContextExtractor(nn.Module):
    def __init__(self, hidden_dim=128, context_dim=128, small=False):
        super().__init__()
        self.small = small
        
        if small:
            self.layer1 = nn.Sequential(
                nn.Conv2d(3, 32, 7, 2, padding=3),
                nn.BatchNorm2d(32),
                nn.ReLU(inplace=True)
            )
            self.layer2 = ResidualBlock(32, 64, stride=2)
            self.layer3 = ResidualBlock(64, 96, stride=2)
            self.layer4 = ResidualBlock(96, 128, stride=1)
            self.conv_hidden = nn.Conv2d(128, hidden_dim, 3, padding=1)
            self.conv_context = nn.Conv2d(128, context_dim, 3, padding=1)
        else:
            self.layer1 = nn.Sequential(
                nn.Conv2d(3, 64, 7, 2, padding=3),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True)
            )
            self.layer2 = ResidualBlock(64, 128, stride=2)
            self.layer3 = ResidualBlock(128, 256, stride=2)
            self.layer4 = ResidualBlock(256, 256, stride=1)
            self.conv_hidden = nn.Conv2d(256, hidden_dim, 3, padding=1)
            self.conv_context = nn.Conv2d(256, context_dim, 3, padding=1)
    
    def forward(self, x):
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        h = torch.tanh(self.conv_hidden(x))
        c = self.conv_context(x)
        return h, c


class CorrelationPyramid:
    def __init__(self, num_levels=4, radius=4):
        self.num_levels = num_levels
        self.radius = radius
    
    def build(self, fmap1, fmap2):
        batch, dim, h1, w1 = fmap1.shape
        batch, dim, h2, w2 = fmap2.shape
        
        fmap1 = fmap1.view(batch, dim, h1 * w1)
        fmap2 = fmap2.view(batch, dim, h2 * w2)
        
        corr = torch.matmul(fmap1.transpose(1, 2), fmap2)
        corr = corr.view(batch, h1, w1, h2, w2)
        corr = corr / torch.sqrt(torch.tensor(dim, dtype=torch.float32))
        
        pyramid = []
        for i in range(self.num_levels):
            if i == 0:
                pyramid.append(corr.reshape(batch, h1, w1, h2, w2))
            else:
                scale_factor = 1.0 / (2 ** i)
                new_h2 = max(1, int(h2 * scale_factor))
                new_w2 = max(1, int(w2 * scale_factor))
                if corr.shape[-1] >= 2 and corr.shape[-2] >= 2:
                    corr_pool = F.avg_pool3d(corr.reshape(batch, h1, w1, corr.shape[-2], corr.shape[-1]), 
                                            kernel_size=(1, 2, 2), stride=(1, 2, 2))
                    pyramid.append(corr_pool)
                else:
                    break
        return pyramid
    
    def lookup(self, pyramid, coords):
        r = self.radius
        batch, _, h, w = coords.shape
        
        out_pyramid = []
        for i, corr in enumerate(pyramid):
            scale = 2 ** i
            coords_i = coords / scale
            
            dx = torch.linspace(-r, r, 2 * r + 1, device=coords.device)
            dy = torch.linspace(-r, r, 2 * r + 1, device=coords.device)
            delta = torch.stack(torch.meshgrid(dy, dx, indexing='ij'), dim=-1)
            
            delta = delta.view(1, 2 * r + 1, 2 * r + 1, 2)
            
            coords_i = coords_i.permute(0, 2, 3, 1).unsqueeze(3).unsqueeze(3)
            coords_i = coords_i + delta.unsqueeze(0).unsqueeze(0)
            
            batch_i, h_i, w_i, _, _, _ = coords_i.shape
            coords_i = coords_i.reshape(batch_i, h_i, w_i, -1, 2)
            
            corr_volume = self.bilinear_sampler(corr, coords_i)
            out_pyramid.append(corr_volume)
        
        out = torch.cat(out_pyramid, dim=-1)
        out = out.permute(0, 3, 1, 2).contiguous().float()
        return out
    
    @staticmethod
    def bilinear_sampler(img, coords):
        B, H, W, _, _ = img.shape
        B, H, W, N, _ = coords.shape
        
        coords = coords.reshape(B, H * W, N, 2)
        x = coords[..., 0]
        y = coords[..., 1]
        
        x0 = torch.floor(x).long()
        x1 = x0 + 1
        y0 = torch.floor(y).long()
        y1 = y0 + 1
        
        _, ph, pw, ih, iw = img.shape
        x0 = torch.clamp(x0, 0, iw - 1)
        x1 = torch.clamp(x1, 0, iw - 1)
        y0 = torch.clamp(y0, 0, ih - 1)
        y1 = torch.clamp(y1, 0, ih - 1)
        
        Ia = img[:, 0, 0, y0, x0]
        Ib = img[:, 0, 0, y1, x0]
        Ic = img[:, 0, 0, y0, x1]
        Id = img[:, 0, 0, y1, x1]
        
        Ia = Ia.reshape(B, H, W, N)
        Ib = Ib.reshape(B, H, W, N)
        Ic = Ic.reshape(B, H, W, N)
        Id = Id.reshape(B, H, W, N)
        
        x = x.reshape(B, H, W, N)
        y = y.reshape(B, H, W, N)
        
        x0_f = x0.reshape(B, H, W, N).float()
        x1_f = x1.reshape(B, H, W, N).float()
        y0_f = y0.reshape(B, H, W, N).float()
        y1_f = y1.reshape(B, H, W, N).float()
        
        wa = (x1_f - x) * (y1_f - y)
        wb = (x1_f - x) * (y - y0_f)
        wc = (x - x0_f) * (y1_f - y)
        wd = (x - x0_f) * (y - y0_f)
        
        out = wa * Ia + wb * Ib + wc * Ic + wd * Id
        return out


class ConvGRU(nn.Module):
    def __init__(self, hidden_dim, input_dim, kernel_size=3):
        super().__init__()
        padding = kernel_size // 2
        self.conv_zr = nn.Conv2d(hidden_dim + input_dim, 2 * hidden_dim, kernel_size, padding=padding)
        self.conv_h = nn.Conv2d(hidden_dim + input_dim, hidden_dim, kernel_size, padding=padding)
    
    def forward(self, h, x):
        hx = torch.cat([h, x], dim=1)
        zr = torch.sigmoid(self.conv_zr(hx))
        z, r = torch.chunk(zr, 2, dim=1)
        h_new = torch.tanh(self.conv_h(torch.cat([r * h, x], dim=1)))
        h_new = (1 - z) * h + z * h_new
        return h_new


class FlowHead(nn.Module):
    def __init__(self, input_dim=128, hidden_dim=256):
        super().__init__()
        self.conv1 = nn.Conv2d(input_dim, hidden_dim, 3, padding=1)
        self.conv2 = nn.Conv2d(hidden_dim, 2, 3, padding=1)
        self.relu = nn.ReLU(inplace=True)
    
    def forward(self, x):
        return self.conv2(self.relu(self.conv1(x)))


class UpdateBlock(nn.Module):
    def __init__(self, hidden_dim=128, context_dim=128, corr_dim=324, small=False):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.context_dim = context_dim
        
        self.encoder = nn.Sequential(
            nn.Conv2d(2 + corr_dim, hidden_dim, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden_dim, hidden_dim, 3, padding=1),
            nn.ReLU(inplace=True)
        )
        
        self.gru = ConvGRU(hidden_dim, context_dim + hidden_dim)
        
        self.flow_head = FlowHead(hidden_dim, hidden_dim)
        
        self.mask = nn.Sequential(
            nn.Conv2d(hidden_dim, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 8 * 8 * 9, 3, padding=1)
        )
    
    def forward(self, net, inp, corr, flow):
        motion_features = self.encoder(torch.cat([flow, corr], dim=1))
        inp_cat = torch.cat([inp, motion_features], dim=1)
        net = self.gru(net, inp_cat)
        delta_flow = self.flow_head(net)
        mask = 0.25 * self.mask(net)
        return net, mask, delta_flow


class RAFT(nn.Module):
    def __init__(self, small=False, dropout=0.0):
        super().__init__()
        self.small = small
        self.dropout = dropout
        
        self.hidden_dim = 96 if small else 128
        self.context_dim = 64 if small else 128
        
        self.feature_extractor = FeatureExtractor(output_dim=256, small=small)
        self.context_extractor = ContextExtractor(hidden_dim=self.hidden_dim, 
                                                 context_dim=self.context_dim, 
                                                 small=small)
        
        self.correlation_pyramid = CorrelationPyramid(num_levels=4, radius=4)
        
        corr_dim = (2 * 4 + 1) ** 2 * 4
        self.update_block = UpdateBlock(hidden_dim=self.hidden_dim, 
                                        context_dim=self.context_dim, 
                                        corr_dim=corr_dim,
                                        small=small)
        
        self.apply(initialize_weights)
    
    def initialize_flow(self, img):
        B, _, H, W = img.shape
        coords0 = self.get_coords(B, H // 8, W // 8, device=img.device)
        coords1 = self.get_coords(B, H // 8, W // 8, device=img.device)
        return coords0, coords1
    
    @staticmethod
    def get_coords(batch, h, w, device):
        y, x = torch.meshgrid(torch.arange(h, device=device), 
                             torch.arange(w, device=device),
                             indexing='ij')
        coords = torch.stack([x, y], dim=0).float()
        coords = coords.unsqueeze(0).expand(batch, -1, -1, -1)
        return coords
    
    def upsample_flow(self, flow, mask):
        N, _, H, W = flow.shape
        mask = mask.view(N, 1, 9, 8, 8, H, W)
        mask = torch.softmax(mask, dim=2)
        
        up_flow = F.unfold(8 * flow, [3, 3], padding=1)
        up_flow = up_flow.view(N, 2, 9, 1, 1, H, W)
        
        up_flow = torch.sum(mask * up_flow, dim=2)
        up_flow = up_flow.permute(0, 1, 4, 2, 5, 3)
        return up_flow.reshape(N, 2, 8 * H, 8 * W)
    
    def forward(self, image1, image2, iters=12, flow_init=None, test_mode=False):
        image1 = 2 * (image1 / 255.0) - 1.0
        image2 = 2 * (image2 / 255.0) - 1.0
        
        fmap1 = self.feature_extractor(image1)
        fmap2 = self.feature_extractor(image2)
        
        net, inp = self.context_extractor(image1)
        net = torch.tanh(net)
        inp = torch.relu(inp)
        
        corr_pyramid = self.correlation_pyramid.build(fmap1, fmap2)
        
        coords0, coords1 = self.initialize_flow(image1)
        
        if flow_init is not None:
            coords1 = coords1 + flow_init
        
        flow_predictions = []
        for itr in range(iters):
            coords1 = coords1.detach()
            flow = coords1 - coords0
            corr = self.correlation_pyramid.lookup(corr_pyramid, coords1)
            net, mask, delta_flow = self.update_block(net, inp, corr, flow)
            coords1 = coords1 + delta_flow
            flow_up = self.upsample_flow(coords1 - coords0, mask)
            flow_predictions.append(flow_up)
        
        if test_mode:
            return coords1 - coords0, flow_up
        
        return flow_predictions
    
    def estimate_flow(self, image1, image2, iters=12):
        self.eval()
        with torch.no_grad():
            _, flow_up = self.forward(image1, image2, iters=iters, test_mode=True)
        return flow_up


def load_raft_model(model_path=None, small=False, device='cuda'):
    model = RAFT(small=small)
    
    if model_path is not None:
        try:
            state_dict = torch.load(model_path, map_location=device)
            if 'model' in state_dict:
                state_dict = state_dict['model']
            
            new_state_dict = {}
            for k, v in state_dict.items():
                if k.startswith('module.'):
                    k = k[7:]
                new_state_dict[k] = v
            
            model.load_state_dict(new_state_dict, strict=False)
            print(f'Loaded RAFT model from {model_path}')
        except Exception as e:
            print(f'Warning: Could not load model from {model_path}: {e}')
            print('Using initialized model weights')
    
    model = model.to(device)
    model.eval()
    return model
