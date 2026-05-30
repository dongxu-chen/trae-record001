import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class PartialConv2d(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride=1,
                 padding=0, dilation=1, groups=1, bias=True):
        super().__init__()
        
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size,
                              stride, padding, dilation, groups, bias)
        self.mask_conv = nn.Conv2d(1, 1, kernel_size, stride, padding,
                                   dilation, groups, bias=False)
        
        self.weight_mask = torch.ones(1, 1, kernel_size, kernel_size)
        self.mask_conv.weight.data = self.weight_mask
        self.mask_conv.weight.requires_grad = False
        
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.stride = stride
        self.padding = padding
        
    def forward(self, x, mask):
        if mask.shape[1] != 1:
            mask = mask[:, :1, :, :]
        
        with torch.no_grad():
            mask_ratio = self.in_channels / (self.mask_conv(mask) + 1e-8)
            new_mask = torch.where(self.mask_conv(mask) > 0, 
                                   torch.ones_like(self.mask_conv(mask)),
                                   torch.zeros_like(self.mask_conv(mask)))
        
        x = self.conv(x * mask)
        x = x * mask_ratio
        
        return x, new_mask


class PartialConvBlock(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=1,
                 padding=1, activation='relu', batch_norm=True):
        super().__init__()
        
        self.pconv = PartialConv2d(in_channels, out_channels, kernel_size,
                                   stride, padding)
        self.batch_norm = batch_norm
        self.activation = activation
        
        if batch_norm:
            self.bn = nn.BatchNorm2d(out_channels)
        
        if activation == 'relu':
            self.act = nn.ReLU(inplace=True)
        elif activation == 'leaky_relu':
            self.act = nn.LeakyReLU(0.2, inplace=True)
        elif activation == 'sigmoid':
            self.act = nn.Sigmoid()
        elif activation == 'tanh':
            self.act = nn.Tanh()
        
    def forward(self, x, mask):
        x, mask = self.pconv(x, mask)
        
        if hasattr(self, 'bn'):
            x = self.bn(x)
        
        if hasattr(self, 'act'):
            x = self.act(x)
        
        return x, mask


class PartialConvUNet(nn.Module):
    def __init__(self, input_channels=3, encoder_filters=[64, 128, 256, 512, 512, 512, 512, 512],
                 decoder_filters=[512, 512, 512, 512, 256, 128, 64, 32]):
        super().__init__()
        
        self.input_channels = input_channels
        self.encoder_filters = encoder_filters
        self.decoder_filters = decoder_filters
        
        self.encoders = nn.ModuleList()
        prev_channels = input_channels
        
        for i, out_channels in enumerate(encoder_filters):
            if i == 0:
                self.encoders.append(
                    PartialConvBlock(prev_channels, out_channels, 7, 2, 3, 
                                     activation='relu', batch_norm=False)
                )
            elif i == len(encoder_filters) - 1:
                self.encoders.append(
                    PartialConvBlock(prev_channels, out_channels, 3, 2, 1,
                                     activation='relu', batch_norm=True)
                )
            else:
                self.encoders.append(
                    PartialConvBlock(prev_channels, out_channels, 3, 2, 1,
                                     activation='relu', batch_norm=True)
                )
            prev_channels = out_channels
        
        self.decoders = nn.ModuleList()
        self.skip_connections = nn.ModuleList()
        
        for i, out_channels in enumerate(decoder_filters):
            if i > 0:
                skip_channels = encoder_filters[-(i+1)]
                self.skip_connections.append(
                    PartialConvBlock(skip_channels, skip_channels, 3, 1, 1,
                                     activation='relu', batch_norm=True)
                )
            
            if i > 0:
                in_channels = prev_channels + encoder_filters[-(i+1)]
            else:
                in_channels = prev_channels
            
            self.decoders.append(
                PartialConvBlock(in_channels, out_channels, 3, 1, 1,
                                 activation='leaky_relu', batch_norm=True)
            )
            prev_channels = out_channels
        
        self.final = nn.Conv2d(prev_channels, input_channels, 3, 1, 1)
        
        self._init_weights()
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
    
    def forward(self, x, mask):
        x = x * (1 - mask) + mask
        
        skips = []
        masks = []
        
        for encoder in self.encoders:
            x, mask = encoder(x, mask)
            skips.append(x)
            masks.append(mask)
        
        for i, decoder in enumerate(self.decoders):
            if i > 0:
                skip = skips[-(i+1)]
                skip_mask = masks[-(i+1)]
                
                skip, skip_mask = self.skip_connections[i-1](skip, skip_mask)
                
                x = F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=True)
                mask = F.interpolate(mask, scale_factor=2, mode='nearest')
                
                x = torch.cat([x, skip], dim=1)
                mask = torch.cat([mask, skip_mask], dim=1)[:, :1, :, :]
            
            x, mask = decoder(x, mask)
        
        if x.shape[2:] != skips[0].shape[2:]:
            x = F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=True)
        
        x = self.final(x)
        x = torch.sigmoid(x)
        
        return x


class EdgeGenerator(nn.Module):
    def __init__(self, in_channels=2, out_channels=1, ngf=64):
        super().__init__()
        
        self.conv1 = nn.Conv2d(in_channels, ngf, kernel_size=7, stride=1, padding=3)
        self.conv2 = nn.Conv2d(ngf, ngf*2, kernel_size=4, stride=2, padding=1)
        self.conv3 = nn.Conv2d(ngf*2, ngf*4, kernel_size=4, stride=2, padding=1)
        
        self.res1 = nn.Sequential(
            nn.Conv2d(ngf*4, ngf*4, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(ngf*4),
            nn.ReLU(inplace=True),
            nn.Conv2d(ngf*4, ngf*4, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(ngf*4)
        )
        self.res2 = nn.Sequential(
            nn.Conv2d(ngf*4, ngf*4, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(ngf*4),
            nn.ReLU(inplace=True),
            nn.Conv2d(ngf*4, ngf*4, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(ngf*4)
        )
        
        self.deconv1 = nn.ConvTranspose2d(ngf*4, ngf*2, kernel_size=4, stride=2, padding=1)
        self.deconv2 = nn.ConvTranspose2d(ngf*2, ngf, kernel_size=4, stride=2, padding=1)
        
        self.final = nn.Conv2d(ngf, out_channels, kernel_size=7, stride=1, padding=3)
        
        self._init_weights()
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d) or isinstance(m, nn.ConvTranspose2d):
                nn.init.normal_(m.weight, 0.0, 0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, x, mask):
        x = torch.cat([x, mask], dim=1)
        
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        
        residual = F.relu(x + self.res1(x))
        residual = F.relu(residual + self.res2(residual))
        
        x = x + residual
        
        x = F.relu(self.deconv1(x))
        x = F.relu(self.deconv2(x))
        
        x = torch.tanh(self.final(x))
        
        return x


class InpaintingGenerator(nn.Module):
    def __init__(self, in_channels=4, out_channels=3, ngf=64):
        super().__init__()
        
        self.conv1 = nn.Conv2d(in_channels, ngf, kernel_size=7, stride=1, padding=3)
        self.conv2 = nn.Conv2d(ngf, ngf*2, kernel_size=4, stride=2, padding=1)
        self.conv3 = nn.Conv2d(ngf*2, ngf*4, kernel_size=4, stride=2, padding=1)
        
        self.res_blocks = nn.Sequential(
            self._make_resblock(ngf*4),
            self._make_resblock(ngf*4),
            self._make_resblock(ngf*4),
            self._make_resblock(ngf*4),
            self._make_resblock(ngf*4),
            self._make_resblock(ngf*4)
        )
        
        self.deconv1 = nn.ConvTranspose2d(ngf*4, ngf*2, kernel_size=4, stride=2, padding=1)
        self.deconv2 = nn.ConvTranspose2d(ngf*2, ngf, kernel_size=4, stride=2, padding=1)
        
        self.final = nn.Conv2d(ngf, out_channels, kernel_size=7, stride=1, padding=3)
        
        self._init_weights()
    
    def _make_resblock(self, dim):
        return nn.Sequential(
            nn.Conv2d(dim, dim, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(dim),
            nn.ReLU(inplace=True),
            nn.Conv2d(dim, dim, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(dim)
        )
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d) or isinstance(m, nn.ConvTranspose2d):
                nn.init.normal_(m.weight, 0.0, 0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, x, mask, edge):
        x = x * (1 - mask)
        x = torch.cat([x, edge, mask], dim=1)
        
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        
        x = self.res_blocks(x) + x
        
        x = F.relu(self.deconv1(x))
        x = F.relu(self.deconv2(x))
        
        x = torch.sigmoid(self.final(x))
        
        return x


class EdgeConnect(nn.Module):
    def __init__(self, in_channels=3):
        super().__init__()
        
        self.edge_generator = EdgeGenerator(in_channels=2, out_channels=1)
        self.inpainting_generator = InpaintingGenerator(in_channels=5, out_channels=3)
    
    def forward(self, x, mask):
        gray = torch.mean(x, dim=1, keepdim=True)
        gray = gray * (1 - mask)
        
        edge = self.edge_generator(gray, mask)
        edge = edge * mask + gray * (1 - mask)
        
        output = self.inpainting_generator(x, mask, edge)
        
        return output, edge


class DiversePartialConvUNet(nn.Module):
    def __init__(self, input_channels=3, latent_dim=32,
                 encoder_filters=[64, 128, 256, 512, 512],
                 decoder_filters=[512, 256, 128, 64, 32]):
        super().__init__()
        
        self.latent_dim = latent_dim
        self.input_channels = input_channels
        
        self.encoders = nn.ModuleList()
        self.mask_encoders = nn.ModuleList()
        prev_ch = input_channels
        for i, out_ch in enumerate(encoder_filters):
            self.encoders.append(nn.Sequential(
                nn.Conv2d(prev_ch + (1 if i > 0 else 0), out_ch, 4, 2, 1),
                nn.LeakyReLU(0.2, inplace=True),
                nn.BatchNorm2d(out_ch)
            ))
            self.mask_encoders.append(nn.Sequential(
                nn.Conv2d(1 if i == 0 else encoder_filters[i-1], out_ch, 4, 2, 1),
                nn.LeakyReLU(0.2, inplace=True),
                nn.BatchNorm2d(out_ch)
            ))
            prev_ch = out_ch
        
        self.fc_mu = nn.Linear(encoder_filters[-1] * 8 * 8, latent_dim)
        self.fc_logvar = nn.Linear(encoder_filters[-1] * 8 * 8, latent_dim)
        self.fc_decode = nn.Linear(latent_dim, encoder_filters[-1] * 8 * 8)
        
        self.decoders = nn.ModuleList()
        prev_ch = encoder_filters[-1]
        for i, out_ch in enumerate(decoder_filters):
            self.decoders.append(nn.Sequential(
                nn.ConvTranspose2d(prev_ch, out_ch, 4, 2, 1),
                nn.ReLU(inplace=True),
                nn.BatchNorm2d(out_ch)
            ))
            prev_ch = out_ch
        
        self.final = nn.Conv2d(prev_ch, input_channels, 3, 1, 1)
        self._init_weights()
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Conv2d, nn.ConvTranspose2d, nn.Linear)):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
    
    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def encode(self, x, mask):
        h = x * (1 - mask)
        for i, (enc, menc) in enumerate(zip(self.encoders, self.mask_encoders)):
            if i == 0:
                h = enc(h)
            else:
                m_feat = menc(mask if i == 1 else m_feat)
                h = enc(torch.cat([h, m_feat], dim=1))
        return h
    
    def decode(self, z, mask):
        h = self.fc_decode(z)
        h = h.view(z.size(0), -1, 8, 8)
        for dec in self.decoders:
            h = dec(h)
        return torch.sigmoid(self.final(h))
    
    def forward(self, x, mask, num_samples=1):
        if mask.shape[1] != 1:
            mask = mask[:, :1, :, :]
        
        enc_feat = self.encode(x, mask)
        b, c, fh, fw = enc_feat.shape
        enc_flat = enc_feat.view(b, -1)
        
        mu = self.fc_mu(enc_flat)
        logvar = self.fc_logvar(enc_flat)
        
        results = []
        for _ in range(num_samples):
            z = self.reparameterize(mu, logvar)
            out = self.decode(z, mask)
            out = out * mask + x * (1 - mask)
            results.append(out)
        
        if num_samples == 1:
            return results[0], mu, logvar
        return results, mu, logvar


class StochasticInpainter(nn.Module):
    def __init__(self, input_channels=3, noise_dim=64):
        super().__init__()
        
        self.noise_dim = noise_dim
        
        self.down1 = nn.Sequential(
            nn.Conv2d(input_channels + 1, 64, 7, 2, 3),
            nn.ReLU(inplace=True),
            nn.BatchNorm2d(64)
        )
        self.down2 = nn.Sequential(
            nn.Conv2d(64, 128, 4, 2, 1),
            nn.ReLU(inplace=True),
            nn.BatchNorm2d(128)
        )
        self.down3 = nn.Sequential(
            nn.Conv2d(128, 256, 4, 2, 1),
            nn.ReLU(inplace=True),
            nn.BatchNorm2d(256)
        )
        
        self.noise_proj = nn.Linear(noise_dim, 256 * 32 * 32)
        
        self.res_blocks = nn.Sequential(
            self._resblock(512), self._resblock(512),
            self._resblock(512), self._resblock(512)
        )
        
        self.up3 = nn.Sequential(
            nn.ConvTranspose2d(512, 128, 4, 2, 1),
            nn.ReLU(inplace=True),
            nn.BatchNorm2d(128)
        )
        self.up2 = nn.Sequential(
            nn.ConvTranspose2d(256, 64, 4, 2, 1),
            nn.ReLU(inplace=True),
            nn.BatchNorm2d(64)
        )
        self.up1 = nn.Sequential(
            nn.ConvTranspose2d(128, 32, 4, 2, 1),
            nn.ReLU(inplace=True),
            nn.BatchNorm2d(32)
        )
        
        self.final = nn.Conv2d(32, input_channels, 3, 1, 1)
        self._init_weights()
    
    def _resblock(self, dim):
        return nn.Sequential(
            nn.Conv2d(dim, dim, 3, 1, 1),
            nn.BatchNorm2d(dim),
            nn.ReLU(inplace=True),
            nn.Conv2d(dim, dim, 3, 1, 1),
            nn.BatchNorm2d(dim)
        )
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Conv2d, nn.ConvTranspose2d, nn.Linear)):
                nn.init.normal_(m.weight, 0.0, 0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, x, mask, num_samples=1, temperature=1.0):
        if mask.shape[1] != 1:
            mask = mask[:, :1, :, :]
        
        masked_input = torch.cat([x * (1 - mask), mask], dim=1)
        
        results = []
        for _ in range(num_samples):
            noise = torch.randn(x.size(0), self.noise_dim, device=x.device) * temperature
            
            d1 = self.down1(masked_input)
            d2 = self.down2(d1)
            d3 = self.down3(d2)
            
            noise_feat = self.noise_proj(noise).view(x.size(0), 256, 32, 32)
            
            if d3.shape[2:] != noise_feat.shape[2:]:
                noise_feat = F.interpolate(noise_feat, size=d3.shape[2:], mode='bilinear', align_corners=False)
            
            combined = torch.cat([d3, noise_feat], dim=1)
            h = self.res_blocks(combined)
            
            if h.shape[2:] != d2.shape[2:]:
                h = F.interpolate(h, size=d2.shape[2:], mode='bilinear', align_corners=False)
            u3 = self.up3(torch.cat([h, d2], dim=1))
            
            if u3.shape[2:] != d1.shape[2:]:
                u3 = F.interpolate(u3, size=d1.shape[2:], mode='bilinear', align_corners=False)
            u2 = self.up2(torch.cat([u3, d1], dim=1))
            
            u1 = self.up1(u2)
            out = torch.sigmoid(self.final(u1))
            
            out = out * mask + x * (1 - mask)
            results.append(out)
        
        if num_samples == 1:
            return results[0]
        return results


def load_pretrained_model(model_name='partialconv', device='cpu'):
    if model_name == 'partialconv':
        model = PartialConvUNet()
    elif model_name == 'edgeconnect':
        model = EdgeConnect()
    elif model_name == 'diverse_partialconv':
        model = DiversePartialConvUNet()
    elif model_name == 'stochastic':
        model = StochasticInpainter()
    else:
        raise ValueError(f"Unknown model: {model_name}")
    
    model = model.to(device)
    model.eval()
    
    return model
