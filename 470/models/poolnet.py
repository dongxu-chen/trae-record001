import torch
import torch.nn as nn
import torch.nn.functional as F


class BasicConv2d(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride=1, padding=0, dilation=1):
        super(BasicConv2d, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, dilation, bias=False)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
    
    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))


class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, dilation=1, downsample=None):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, 
                               padding=dilation, dilation=dilation, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1,
                               padding=dilation, dilation=dilation, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.downsample = downsample
    
    def forward(self, x):
        residual = x
        
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        
        out = self.conv2(out)
        out = self.bn2(out)
        
        if self.downsample is not None:
            residual = self.downsample(x)
        
        out += residual
        out = self.relu(out)
        
        return out


class PPM(nn.Module):
    def __init__(self, in_channels, out_channels, sizes=(1, 2, 3, 6)):
        super(PPM, self).__init__()
        self.stages = nn.ModuleList([
            self._make_stage(in_channels, out_channels, size) for size in sizes
        ])
        self.bottleneck = nn.Sequential(
            nn.Conv2d(in_channels + out_channels * len(sizes), out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Dropout2d(p=0.1)
        )
    
    def _make_stage(self, in_channels, out_channels, size):
        return nn.Sequential(
            nn.AdaptiveAvgPool2d(output_size=(size, size)),
            nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
    
    def forward(self, x):
        h, w = x.size()[2:]
        pyramids = [x]
        
        for stage in self.stages:
            feat = stage(x)
            feat = F.interpolate(feat, size=(h, w), mode='bilinear', align_corners=True)
            pyramids.append(feat)
        
        out = torch.cat(pyramids, dim=1)
        out = self.bottleneck(out)
        
        return out


class GGM(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(GGM, self).__init__()
        self.reduce = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
        self.att = nn.Sequential(
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        x = self.reduce(x)
        att = self.att(x)
        return x * att


class PoolNet(nn.Module):
    def __init__(self, n_channels=3, n_classes=1, backbone='resnet50'):
        super(PoolNet, self).__init__()
        
        self.inplanes = 64
        
        self.conv1 = nn.Sequential(
            nn.Conv2d(n_channels, 64, kernel_size=7, stride=2, padding=3, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        
        self.layer1 = self._make_layer(ResidualBlock, 64, 3, stride=1)
        self.layer2 = self._make_layer(ResidualBlock, 128, 4, stride=2)
        self.layer3 = self._make_layer(ResidualBlock, 256, 6, stride=2, dilation=2)
        self.layer4 = self._make_layer(ResidualBlock, 512, 3, stride=1, dilation=4)
        
        self.ppm = PPM(2048, 512)
        
        self.ggm1 = GGM(256, 64)
        self.ggm2 = GGM(512, 128)
        self.ggm3 = GGM(1024, 256)
        self.ggm4 = GGM(2048, 512)
        
        self.decoder4 = self._make_decoder(512, 256)
        self.decoder3 = self._make_decoder(256, 128)
        self.decoder2 = self._make_decoder(128, 64)
        self.decoder1 = self._make_decoder(64, 64)
        
        self.predictor4 = nn.Conv2d(256, n_classes, kernel_size=1)
        self.predictor3 = nn.Conv2d(128, n_classes, kernel_size=1)
        self.predictor2 = nn.Conv2d(64, n_classes, kernel_size=1)
        self.predictor1 = nn.Conv2d(64, n_classes, kernel_size=1)
        
        self._init_weights()
    
    def _make_layer(self, block, planes, blocks, stride=1, dilation=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * 4:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * 4, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * 4)
            )
        
        layers = []
        layers.append(block(self.inplanes, planes * 4, stride, dilation, downsample))
        self.inplanes = planes * 4
        
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes * 4, stride=1, dilation=dilation))
        
        return nn.Sequential(*layers)
    
    def _make_decoder(self, in_channels, out_channels):
        return nn.Sequential(
            BasicConv2d(in_channels, out_channels, kernel_size=3, padding=1),
            BasicConv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.ConvTranspose2d(out_channels, out_channels, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        h, w = x.size()[2:]
        
        x = self.conv1(x)
        x = self.maxpool(x)
        
        l1 = self.layer1(x)
        l2 = self.layer2(l1)
        l3 = self.layer3(l2)
        l4 = self.layer4(l3)
        
        l4_agg = self.ppm(l4)
        
        g1 = self.ggm1(l1)
        g2 = self.ggm2(l2)
        g3 = self.ggm3(l3)
        g4 = self.ggm4(l4)
        
        d4 = self.decoder4(l4_agg + g4)
        d4 = F.interpolate(d4, size=g3.size()[2:], mode='bilinear', align_corners=True)
        d4 = d4 + g3
        
        d3 = self.decoder3(d4)
        d3 = F.interpolate(d3, size=g2.size()[2:], mode='bilinear', align_corners=True)
        d3 = d3 + g2
        
        d2 = self.decoder2(d3)
        d2 = F.interpolate(d2, size=g1.size()[2:], mode='bilinear', align_corners=True)
        d2 = d2 + g1
        
        d1 = self.decoder1(d2)
        d1 = F.interpolate(d1, size=(h, w), mode='bilinear', align_corners=True)
        
        out = torch.sigmoid(self.predictor1(d1))
        
        if self.training:
            out4 = torch.sigmoid(F.interpolate(self.predictor4(d4), size=(h, w), mode='bilinear', align_corners=True))
            out3 = torch.sigmoid(F.interpolate(self.predictor3(d3), size=(h, w), mode='bilinear', align_corners=True))
            out2 = torch.sigmoid(F.interpolate(self.predictor2(d2), size=(h, w), mode='bilinear', align_corners=True))
            return out, out2, out3, out4
        
        return out
    
    def load_checkpoint(self, checkpoint_path, device='cpu'):
        try:
            state_dict = torch.load(checkpoint_path, map_location=device)
            if 'model_state_dict' in state_dict:
                state_dict = state_dict['model_state_dict']
            self.load_state_dict(state_dict, strict=False)
            print(f"Successfully loaded checkpoint from {checkpoint_path}")
        except Exception as e:
            print(f"Warning: Could not load checkpoint: {e}")
            print("Using initialized weights. For better performance, download pretrained weights.")
    
    def export_to_onnx(self, onnx_path, input_size=256, batch_size=1, opset_version=12):
        self.eval()
        
        dummy_input = torch.randn(batch_size, 3, input_size, input_size)
        
        dynamic_axes = {
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
        
        torch.onnx.export(
            self,
            dummy_input,
            onnx_path,
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes=dynamic_axes,
            verbose=False
        )
        
        print(f"Model exported to ONNX: {onnx_path}")
        return onnx_path
    
    def export_to_tensorrt(self, trt_path, input_size=256, max_batch_size=8, 
                           fp16=True, int8=False, calibration_data=None):
        try:
            from .tensorrt_engine import TensorRTBuilder
            
            onnx_path = trt_path.replace('.trt', '.onnx')
            self.export_to_onnx(onnx_path, input_size, batch_size=max_batch_size)
            
            builder = TensorRTBuilder(
                max_batch_size=max_batch_size,
                fp16=fp16,
                int8=int8
            )
            
            if int8 and calibration_data is not None:
                builder.set_calibration_data(calibration_data)
            
            success = builder.build_engine(
                onnx_path,
                trt_path,
                input_shape=(3, input_size, input_size)
            )
            
            return success, trt_path
        except ImportError as e:
            print(f"TensorRT not available: {e}")
            return False, None
