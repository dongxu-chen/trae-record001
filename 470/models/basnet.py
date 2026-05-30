import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, dilation=1):
        super(ResidualBlock, self).__init__()
        
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, 
                               stride=stride, padding=dilation, dilation=dilation, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3,
                               stride=1, padding=dilation, dilation=dilation, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )
        else:
            self.shortcut = nn.Identity()
    
    def forward(self, x):
        identity = self.shortcut(x)
        
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        
        out = self.conv2(out)
        out = self.bn2(out)
        
        out += identity
        out = self.relu(out)
        
        return out


class ConvBNReLU(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=1, padding=1):
        super(ConvBNReLU, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=False)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
    
    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))


class DeconvBNReLU(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=4, stride=2, padding=1):
        super(DeconvBNReLU, self).__init__()
        self.deconv = nn.ConvTranspose2d(in_channels, out_channels, kernel_size, stride, padding, bias=False)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
    
    def forward(self, x):
        return self.relu(self.bn(self.deconv(x)))


class BASNet(nn.Module):
    def __init__(self, n_channels=3, n_classes=1):
        super(BASNet, self).__init__()
        
        self.encoder1 = nn.Sequential(
            ConvBNReLU(n_channels, 64, 3, 1, 1),
            ConvBNReLU(64, 64, 3, 1, 1)
        )
        self.pool1 = nn.MaxPool2d(2, 2, ceil_mode=True)
        
        self.encoder2 = nn.Sequential(
            ResidualBlock(64, 128, stride=1),
            ResidualBlock(128, 128, stride=1)
        )
        self.pool2 = nn.MaxPool2d(2, 2, ceil_mode=True)
        
        self.encoder3 = nn.Sequential(
            ResidualBlock(128, 256, stride=1),
            ResidualBlock(256, 256, stride=1),
            ResidualBlock(256, 256, stride=1)
        )
        self.pool3 = nn.MaxPool2d(2, 2, ceil_mode=True)
        
        self.encoder4 = nn.Sequential(
            ResidualBlock(256, 512, stride=1),
            ResidualBlock(512, 512, stride=1),
            ResidualBlock(512, 512, stride=1)
        )
        self.pool4 = nn.MaxPool2d(2, 2, ceil_mode=True)
        
        self.encoder5 = nn.Sequential(
            ResidualBlock(512, 512, stride=1, dilation=2),
            ResidualBlock(512, 512, stride=1, dilation=2),
            ResidualBlock(512, 512, stride=1, dilation=2)
        )
        
        self.encoder6 = nn.Sequential(
            ResidualBlock(512, 512, stride=1, dilation=4),
            ResidualBlock(512, 512, stride=1, dilation=4)
        )
        
        self.decoder5 = nn.Sequential(
            DeconvBNReLU(1024, 512, 4, 2, 1),
            ConvBNReLU(512, 512, 3, 1, 1),
            ConvBNReLU(512, 512, 3, 1, 1)
        )
        
        self.decoder4 = nn.Sequential(
            DeconvBNReLU(1024, 256, 4, 2, 1),
            ConvBNReLU(256, 256, 3, 1, 1),
            ConvBNReLU(256, 256, 3, 1, 1)
        )
        
        self.decoder3 = nn.Sequential(
            DeconvBNReLU(512, 128, 4, 2, 1),
            ConvBNReLU(128, 128, 3, 1, 1),
            ConvBNReLU(128, 128, 3, 1, 1)
        )
        
        self.decoder2 = nn.Sequential(
            DeconvBNReLU(256, 64, 4, 2, 1),
            ConvBNReLU(64, 64, 3, 1, 1),
            ConvBNReLU(64, 64, 3, 1, 1)
        )
        
        self.decoder1 = nn.Sequential(
            DeconvBNReLU(128, 64, 4, 2, 1),
            ConvBNReLU(64, 64, 3, 1, 1),
            ConvBNReLU(64, 64, 3, 1, 1)
        )
        
        self.out_conv1 = nn.Conv2d(64, n_classes, kernel_size=3, padding=1)
        self.out_conv2 = nn.Conv2d(64, n_classes, kernel_size=3, padding=1)
        self.out_conv3 = nn.Conv2d(128, n_classes, kernel_size=3, padding=1)
        self.out_conv4 = nn.Conv2d(256, n_classes, kernel_size=3, padding=1)
        self.out_conv5 = nn.Conv2d(512, n_classes, kernel_size=3, padding=1)
        self.out_conv6 = nn.Conv2d(512, n_classes, kernel_size=3, padding=1)
        
        self._init_weights()
    
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
        
        e1 = self.encoder1(x)
        e1p = self.pool1(e1)
        
        e2 = self.encoder2(e1p)
        e2p = self.pool2(e2)
        
        e3 = self.encoder3(e2p)
        e3p = self.pool3(e3)
        
        e4 = self.encoder4(e3p)
        e4p = self.pool4(e4)
        
        e5 = self.encoder5(e4p)
        e6 = self.encoder6(e5)
        
        d5 = self.decoder5(torch.cat([e5, e6], dim=1))
        d4 = self.decoder4(torch.cat([d5, e4], dim=1))
        d3 = self.decoder3(torch.cat([d4, e3], dim=1))
        d2 = self.decoder2(torch.cat([d3, e2], dim=1))
        d1 = self.decoder1(torch.cat([d2, e1], dim=1))
        
        out1 = torch.sigmoid(self.out_conv1(d1))
        out2 = torch.sigmoid(self.out_conv2(d2))
        out3 = torch.sigmoid(self.out_conv3(d3))
        out4 = torch.sigmoid(self.out_conv4(d4))
        out5 = torch.sigmoid(self.out_conv5(d5))
        out6 = torch.sigmoid(self.out_conv6(e6))
        
        out2 = F.interpolate(out2, size=(h, w), mode='bilinear', align_corners=True)
        out3 = F.interpolate(out3, size=(h, w), mode='bilinear', align_corners=True)
        out4 = F.interpolate(out4, size=(h, w), mode='bilinear', align_corners=True)
        out5 = F.interpolate(out5, size=(h, w), mode='bilinear', align_corners=True)
        out6 = F.interpolate(out6, size=(h, w), mode='bilinear', align_corners=True)
        
        if self.training:
            return out1, out2, out3, out4, out5, out6
        else:
            return out1
    
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
