import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import cv2


class AODNet(nn.Module):
    def __init__(self):
        super(AODNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 3, kernel_size=1, stride=1, padding=0)
        self.conv2 = nn.Conv2d(3, 3, kernel_size=1, stride=1, padding=0)
        self.conv3 = nn.Conv2d(6, 3, kernel_size=1, stride=1, padding=0)
        self.conv4 = nn.Conv2d(6, 3, kernel_size=1, stride=1, padding=0)
        self.conv5 = nn.Conv2d(12, 3, kernel_size=1, stride=1, padding=0)
        self.relu = nn.ReLU(inplace=True)
        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.normal_(m.weight, mean=0.0, std=0.02)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0.0)

    def forward(self, x):
        x1 = self.relu(self.conv1(x))
        x2 = self.relu(self.conv2(x1))
        concat1 = torch.cat((x1, x2), 1)
        x3 = self.relu(self.conv3(concat1))
        concat2 = torch.cat((x2, x3), 1)
        x4 = self.relu(self.conv4(concat2))
        concat3 = torch.cat((x1, x2, x3, x4), 1)
        x5 = self.relu(self.conv5(concat3))
        output = x5 * x - x5 + 1.0
        return output


class AODNetDehazer:
    def __init__(self, model_path=None, device=None, dehaze_strength=1.0):
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = AODNet().to(self.device)
        self.dehaze_strength = dehaze_strength
        if model_path:
            self.load_model(model_path)
        else:
            print("Warning: No model weights loaded. Using random initialization.")
            print("Please train the model or load pre-trained weights.")

    def load_model(self, model_path):
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()
        print(f"Model loaded from {model_path}")

    def set_dehaze_strength(self, strength):
        self.dehaze_strength = np.clip(strength, 0.0, 2.0)

    def _preprocess(self, img):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if len(img.shape) == 3 else img
        img_float = img_rgb.astype(np.float32) / 255.0
        tensor = torch.from_numpy(img_float.transpose(2, 0, 1)).unsqueeze(0)
        return tensor.to(self.device)

    def _postprocess(self, tensor):
        output = tensor.squeeze(0).cpu().detach().numpy()
        output = output.transpose(1, 2, 0)
        output = np.clip(output, 0, 1)
        output = (output * 255).astype(np.uint8)
        return cv2.cvtColor(output, cv2.COLOR_RGB2BGR)

    def dehaze(self, img):
        self.model.eval()
        with torch.no_grad():
            input_tensor = self._preprocess(img)
            output_tensor = self.model(input_tensor)
            if self.dehaze_strength != 1.0:
                alpha = self.dehaze_strength
                output_tensor = input_tensor * (1 - alpha) + output_tensor * alpha
            dehazed = self._postprocess(output_tensor)
        return dehazed


def create_demo_aod_model(save_path='aod_net_demo.pth'):
    model = AODNet()
    torch.save(model.state_dict(), save_path)
    print(f"Demo model saved to {save_path}")
    return save_path


if __name__ == '__main__':
    create_demo_aod_model()
