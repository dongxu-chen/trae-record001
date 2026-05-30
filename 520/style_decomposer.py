import torch
import torch.nn as nn
import torch.nn.functional as F
import cv2
import numpy as np
from PIL import Image
from torchvision import transforms
from adain_model import AdaINModel, calc_mean_std, adaptive_instance_normalization


class StructurePreservingLoss(nn.Module):
    def __init__(self, device='cpu'):
        super().__init__()
        self.device = device
        self.sobel_x = nn.Conv2d(1, 1, 3, padding=1, bias=False).to(device)
        self.sobel_y = nn.Conv2d(1, 1, 3, padding=1, bias=False).to(device)
        sobel_x = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32).view(1, 1, 3, 3)
        sobel_y = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=torch.float32).view(1, 1, 3, 3)
        self.sobel_x.weight.data = sobel_x
        self.sobel_y.weight.data = sobel_y
        self.sobel_x.weight.requires_grad = False
        self.sobel_y.weight.requires_grad = False
        self.mse = nn.MSELoss()

    def _to_gray(self, x):
        if x.size(1) == 3:
            gray = 0.299 * x[:, 0:1] + 0.587 * x[:, 1:2] + 0.114 * x[:, 2:3]
        else:
            gray = x
        return gray

    def _compute_edges(self, x):
        gray = self._to_gray(x)
        edge_x = self.sobel_x(gray)
        edge_y = self.sobel_y(gray)
        edges = torch.sqrt(edge_x ** 2 + edge_y ** 2 + 1e-6)
        return edges

    def _compute_gradient(self, x):
        dx = x[:, :, :, 1:] - x[:, :, :, :-1]
        dy = x[:, :, 1:, :] - x[:, :, :-1, :]
        return dx, dy

    def forward(self, original, decomposed_content, weight_edge=1.0, weight_grad=0.5, weight_feat=0.5):
        edge_orig = self._compute_edges(original)
        edge_decomp = self._compute_edges(decomposed_content)
        edge_loss = self.mse(edge_decomp, edge_orig)

        dx_orig, dy_orig = self._compute_gradient(original)
        dx_decomp, dy_decomp = self._compute_gradient(decomposed_content)
        grad_loss = self.mse(dx_decomp, dx_orig) + self.mse(dy_decomp, dy_orig)

        feat_loss = self.mse(decomposed_content, original)

        total = weight_edge * edge_loss + weight_grad * grad_loss + weight_feat * feat_loss
        return total, {
            'edge_loss': edge_loss.item(),
            'grad_loss': grad_loss.item(),
            'feat_loss': feat_loss.item()
        }


class StyleDecomposer(nn.Module):
    def __init__(self, device='cpu'):
        super().__init__()
        self.device = device
        self.adain = AdaINModel().to(device)
        self.structure_loss = StructurePreservingLoss(device)
        self.transform = transforms.Compose([
            transforms.Resize((512, 512)),
            transforms.ToTensor(),
        ])

    def preprocess(self, image):
        if isinstance(image, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        elif isinstance(image, Image.Image):
            pass
        else:
            raise ValueError("Unsupported image type")
        return self.transform(image).unsqueeze(0).to(self.device)

    def postprocess(self, tensor):
        tensor = tensor.clamp(0, 1)
        img = tensor.squeeze(0).cpu().permute(1, 2, 0).numpy()
        img = (img * 255).astype(np.uint8)
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    def extract_content(self, image):
        img_tensor = self.preprocess(image)
        content_feats = self.adain.encode_content(img_tensor)
        content_only = self.adain.decode(content_feats[-1])
        return self.postprocess(content_only), content_feats

    def extract_style(self, image):
        img_tensor = self.preprocess(image)
        style_feats = self.adain.encode_style(img_tensor)
        return style_feats

    def extract_style_map(self, image):
        img_tensor = self.preprocess(image)
        style_feats = self.adain.encode_style(img_tensor)

        content_feats = style_feats[-1].clone()
        b, c, h, w = content_feats.shape
        content_mean, content_std = calc_mean_std(content_feats)
        normalized_content = (content_feats - content_mean) / content_std

        white_noise = torch.randn_like(content_feats) * content_std + content_mean
        style_recon = self.adain.decode(white_noise)
        return self.postprocess(style_recon), style_feats

    def decompose(self, image, preserve_structure=True, structure_weight=0.3, num_refine=3, lr=0.01):
        img_tensor = self.preprocess(image)
        content_feats = self.adain.encode_content(img_tensor)
        style_feats = self.adain.encode_style(img_tensor)

        if preserve_structure:
            refined_feats = content_feats[-1].clone().detach().requires_grad_(True)
            optimizer = torch.optim.Adam([refined_feats], lr=lr)

            for step in range(num_refine):
                optimizer.zero_grad()
                decoded = self.adain.decode(refined_feats)
                struct_loss, loss_dict = self.structure_loss(img_tensor, decoded)
                total_loss = structure_weight * struct_loss
                total_loss.backward()
                optimizer.step()

            content_feats_list = list(content_feats)
            content_feats_list[-1] = refined_feats.detach()
            content_feats = content_feats_list
            content_img = self.postprocess(self.adain.decode(refined_feats.detach()))
        else:
            content_img = self.postprocess(self.adain.decode(content_feats[-1]))

        style_map = self.postprocess(self.adain.decode(style_feats[-1]))

        return {
            'content': content_img,
            'style_map': style_map,
            'content_feats': content_feats,
            'style_feats': style_feats
        }

    def reconstruct_from_features(self, content_feats, style_feats, alpha=1.0):
        t = self.adain.style_transfer(content_feats[-1], style_feats, alpha)
        recon = self.adain.decode(t)
        return self.postprocess(recon)

    def reconstruct(self, content_img, style_img, alpha=1.0):
        content_tensor = self.preprocess(content_img)
        style_tensor = self.preprocess(style_img)

        content_feats = self.adain.encode_content(content_tensor)
        style_feats = self.adain.encode_style(style_tensor)

        return self.reconstruct_from_features(content_feats, style_feats, alpha)


class DiffusionStyleDecomposer(nn.Module):
    def __init__(self, device='cpu', num_steps=50):
        super().__init__()
        self.device = device
        self.num_steps = num_steps
        self.beta = torch.linspace(1e-4, 0.02, num_steps).to(device)
        self.alpha = 1 - self.beta
        self.alpha_bar = torch.cumprod(self.alpha, dim=0)
        self.structure_loss = StructurePreservingLoss(device)
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
        ])

    def preprocess(self, image):
        if isinstance(image, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        return self.transform(image).unsqueeze(0).to(self.device)

    def postprocess(self, tensor):
        tensor = tensor.clamp(0, 1)
        img = tensor.squeeze(0).cpu().permute(1, 2, 0).numpy()
        img = (img * 255).astype(np.uint8)
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    def q_sample(self, x0, t, noise=None):
        if noise is None:
            noise = torch.randn_like(x0)
        alpha_bar_t = self.alpha_bar[t].view(-1, 1, 1, 1)
        return torch.sqrt(alpha_bar_t) * x0 + torch.sqrt(1 - alpha_bar_t) * noise

    def extract_content_diffusion(self, image, content_step=20, preserve_structure=True, structure_weight=0.3):
        x0 = self.preprocess(image)
        t = torch.tensor([content_step], device=self.device)
        noisy_content = self.q_sample(x0, t)

        if preserve_structure:
            refined = noisy_content.clone().detach().requires_grad_(True)
            optimizer = torch.optim.Adam([refined], lr=0.01)
            for _ in range(3):
                optimizer.zero_grad()
                struct_loss, _ = self.structure_loss(x0, refined)
                total_loss = structure_weight * struct_loss
                total_loss.backward()
                optimizer.step()
            noisy_content = refined.detach()

        return self.postprocess(noisy_content), noisy_content

    def extract_style_diffusion(self, image, style_start_step=30):
        x0 = self.preprocess(image)
        style_features = []
        for t in range(style_start_step, self.num_steps, 10):
            t_tensor = torch.tensor([t], device=self.device)
            noisy = self.q_sample(x0, t_tensor)
            style_features.append(noisy)
        return style_features

    def decompose(self, image, preserve_structure=True, structure_weight=0.3):
        content_img, content_feat = self.extract_content_diffusion(
            image, preserve_structure=preserve_structure, structure_weight=structure_weight
        )
        style_feats = self.extract_style_diffusion(image)
        return {
            'content': content_img,
            'content_feat': content_feat,
            'style_feats': style_feats
        }

    def reconstruct(self, content_img, style_img, alpha=1.0):
        content_tensor = self.preprocess(content_img)
        style_tensor = self.preprocess(style_img)

        mixed = alpha * style_tensor + (1 - alpha) * content_tensor
        return self.postprocess(mixed)
