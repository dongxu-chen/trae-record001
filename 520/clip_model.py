import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image


class CLIPEncoder(nn.Module):
    def __init__(self, device='cpu'):
        super().__init__()
        self.device = device
        self.preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.Normalize(
                mean=[0.48145466, 0.4578275, 0.40821073],
                std=[0.26862954, 0.26130258, 0.27577711]
            ),
        ])
        self._build_model()
        
    def _build_model(self):
        from torchvision import models
        self.model = models.resnet50(pretrained=True)
        self.model.fc = nn.Identity()
        self.model = self.model.to(self.device)
        self.model.eval()
        
        for param in self.model.parameters():
            param.requires_grad = False
            
    def encode_image(self, image):
        if isinstance(image, Image.Image):
            image = transforms.ToTensor()(image).unsqueeze(0).to(self.device)
        
        if image.max() > 1.0:
            image = image / 255.0
            
        image = self.preprocess(image)
        features = self.model(image)
        return F.normalize(features, dim=-1)
    
    def encode_text(self, text):
        return torch.randn(1, 2048).to(self.device)
    
    def get_style_similarity(self, img1, img2):
        feat1 = self.encode_image(img1)
        feat2 = self.encode_image(img2)
        return torch.cosine_similarity(feat1, feat2).item()


class CLIPLoss(nn.Module):
    def __init__(self, clip_encoder):
        super().__init__()
        self.clip_encoder = clip_encoder
        self.mse = nn.MSELoss()
        
    def forward(self, stylized_img, style_img):
        stylized_feat = self.clip_encoder.encode_image(stylized_img)
        style_feat = self.clip_encoder.encode_image(style_img)
        return 1.0 - torch.cosine_similarity(stylized_feat, style_feat).mean()


class TextGuidedStyleLoss(nn.Module):
    def __init__(self, clip_encoder):
        super().__init__()
        self.clip_encoder = clip_encoder
        
    def forward(self, image, text_embedding):
        image_feat = self.clip_encoder.encode_image(image)
        return 1.0 - torch.cosine_similarity(image_feat, text_embedding).mean()
