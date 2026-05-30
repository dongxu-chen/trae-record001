import torch
import torch.nn as nn
import torch.nn.functional as F
import cv2
import numpy as np
from PIL import Image
from torchvision import transforms
from adain_model import calc_mean_std, adaptive_instance_normalization
from style_decomposer import StyleDecomposer, DiffusionStyleDecomposer
from clip_model import CLIPEncoder


class HighFrequencyEnhancer:
    def __init__(self, device='cpu'):
        self.device = device

    def _build_laplacian_pyramid(self, img, levels=3):
        pyramid = []
        current = img.clone()
        for _ in range(levels):
            down = F.avg_pool2d(current, kernel_size=2, stride=2)
            up = F.interpolate(down, size=current.shape[2:], mode='bilinear', align_corners=False)
            laplacian = current - up
            pyramid.append(laplacian)
            current = down
        pyramid.append(current)
        return pyramid

    def _reconstruct_from_pyramid(self, pyramid):
        current = pyramid[-1]
        for i in range(len(pyramid) - 2, -1, -1):
            up = F.interpolate(current, size=pyramid[i].shape[2:], mode='bilinear', align_corners=False)
            current = up + pyramid[i]
        return current

    def enhance_tensor(self, stylized_tensor, style_tensor, strength=1.0, levels=3):
        stylized_pyr = self._build_laplacian_pyramid(stylized_tensor, levels)
        style_pyr = self._build_laplacian_pyramid(style_tensor, levels)

        enhanced_pyr = []
        for i in range(min(len(stylized_pyr), len(style_pyr)) - 1):
            stylized_hf = stylized_pyr[i]
            style_hf = style_pyr[i]
            enhanced_hf = stylized_hf + strength * style_hf
            enhanced_pyr.append(enhanced_hf)
        enhanced_pyr.append(stylized_pyr[-1])

        return self._reconstruct_from_pyramid(enhanced_pyr)

    def enhance_numpy(self, stylized_img, style_img, strength=0.5, levels=3):
        h, w = stylized_img.shape[:2]
        style_resized = cv2.resize(style_img, (w, h))

        stylized_lp = self._build_laplacian_pyramid_np(stylized_img, levels)
        style_lp = self._build_laplacian_pyramid_np(style_resized, levels)

        enhanced_lp = []
        for i in range(min(len(stylized_lp), len(style_lp)) - 1):
            enhanced_hf = stylized_lp[i].astype(np.float32) + strength * style_lp[i].astype(np.float32)
            enhanced_lp.append(enhanced_hf)
        enhanced_lp.append(stylized_lp[-1])

        result = self._reconstruct_from_pyramid_np(enhanced_lp)
        return np.clip(result, 0, 255).astype(np.uint8)

    def _build_laplacian_pyramid_np(self, img, levels=3):
        pyramid = []
        current = img.astype(np.float32)
        for _ in range(levels):
            h, w = current.shape[:2]
            down = cv2.pyrDown(current)
            up = cv2.pyrUp(down, dstsize=(w, h))
            laplacian = current - up
            pyramid.append(laplacian)
            current = down
        pyramid.append(current)
        return pyramid

    def _reconstruct_from_pyramid_np(self, pyramid):
        current = pyramid[-1]
        for i in range(len(pyramid) - 2, -1, -1):
            h, w = pyramid[i].shape[:2]
            up = cv2.pyrUp(current, dstsize=(w, h))
            current = up + pyramid[i]
        return current

    def unsharp_mask(self, img, sigma=1.0, strength=1.0):
        blurred = cv2.GaussianBlur(img, (0, 0), sigma)
        high_freq = cv2.addWeighted(img, 1 + strength, blurred, -strength, 0)
        return np.clip(high_freq, 0, 255).astype(np.uint8)

    def texture_enhance(self, stylized_img, style_img, strength=0.5):
        h, w = stylized_img.shape[:2]
        style_resized = cv2.resize(style_img, (w, h))

        style_gray = cv2.cvtColor(style_resized, cv2.COLOR_BGR2GRAY).astype(np.float32)
        blurred = cv2.GaussianBlur(style_gray, (0, 0), 2.0)
        texture_mask = np.abs(style_gray - blurred)
        texture_mask = texture_mask / (texture_mask.max() + 1e-6)
        texture_mask = np.stack([texture_mask] * 3, axis=-1)

        stylized_float = stylized_img.astype(np.float32)
        enhanced = cv2.detailEnhance(stylized_img, sigma_s=10, sigma_r=0.15)

        result = stylized_float * (1 - strength * texture_mask) + enhanced.astype(np.float32) * (strength * texture_mask)
        return np.clip(result, 0, 255).astype(np.uint8)


class StyleMixer(nn.Module):
    def __init__(self, device='cpu'):
        super().__init__()
        self.device = device
        self.adain_decomposer = StyleDecomposer(device)
        self.diffusion_decomposer = DiffusionStyleDecomposer(device)
        self.clip_encoder = CLIPEncoder(device)
        self.hf_enhancer = HighFrequencyEnhancer(device)
        self.transform = transforms.Compose([
            transforms.Resize((512, 512)),
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

    def style_swap(self, content_img, style_img, alpha=1.0, method='adain',
                   hf_enhance=True, hf_strength=0.5):
        if method == 'adain':
            result = self.adain_decomposer.reconstruct(content_img, style_img, alpha)
        elif method == 'diffusion':
            result = self.diffusion_decomposer.reconstruct(content_img, style_img, alpha)
        else:
            raise ValueError(f"Unknown method: {method}")

        if hf_enhance and method == 'adain':
            result = self.hf_enhancer.enhance_numpy(result, style_img, strength=hf_strength)
            result = self.hf_enhancer.unsharp_mask(result, sigma=1.0, strength=hf_strength * 0.3)

        return result

    def style_mix_feature_level(self, content_img, style_imgs, weights=None, alpha=1.0):
        if weights is None:
            weights = [1.0 / len(style_imgs)] * len(style_imgs)
        content_tensor = self.preprocess(content_img)
        content_feats = self.adain_decomposer.adain.encode_content(content_tensor)

        all_style_feats = []
        for style_img in style_imgs:
            style_tensor = self.preprocess(style_img)
            style_feats = self.adain_decomposer.adain.encode_style(style_tensor)
            all_style_feats.append(style_feats)

        mixed_style_feats = []
        for i in range(5):
            mixed_feat = None
            for style_feats, weight in zip(all_style_feats, weights):
                if mixed_feat is None:
                    mixed_feat = weight * style_feats[i]
                else:
                    mixed_feat += weight * style_feats[i]
            mixed_style_feats.append(mixed_feat)

        result = self.adain_decomposer.reconstruct_from_features(
            content_feats, mixed_style_feats, alpha
        )
        return result

    def style_mix_pixel_level(self, content_img, style_imgs, weights=None, alpha=1.0):
        if weights is None:
            weights = [1.0 / len(style_imgs)] * len(style_imgs)
        result = None
        for style_img, weight in zip(style_imgs, weights):
            stylized = self.adain_decomposer.reconstruct(content_img, style_img, alpha)
            if result is None:
                result = stylized.astype(np.float64) * weight
            else:
                result += stylized.astype(np.float64) * weight
        return np.clip(result, 0, 255).astype(np.uint8)

    def style_mix_dual(self, content_img, style_imgs, weights=None, alpha=1.0,
                       feature_ratio=0.7, hf_enhance=True, hf_strength=0.5):
        if weights is None:
            weights = [1.0 / len(style_imgs)] * len(style_imgs)
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        feat_result = self.style_mix_feature_level(content_img, style_imgs, weights, alpha)
        pix_result = self.style_mix_pixel_level(content_img, style_imgs, weights, alpha)

        result = cv2.addWeighted(feat_result, feature_ratio, pix_result, 1 - feature_ratio, 0)

        if hf_enhance and len(style_imgs) > 0:
            primary_style = style_imgs[0]
            result = self.hf_enhancer.enhance_numpy(result, primary_style, strength=hf_strength)
            result = self.hf_enhancer.unsharp_mask(result, sigma=1.0, strength=hf_strength * 0.3)

        return result

    def style_mix(self, content_img, style_imgs, weights=None, alpha=1.0, method='adain',
                  hf_enhance=True, hf_strength=0.5, mix_mode='feature'):
        if weights is None:
            weights = [1.0 / len(style_imgs)] * len(style_imgs)
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        if method == 'adain':
            if mix_mode == 'dual':
                return self.style_mix_dual(content_img, style_imgs, weights, alpha,
                                          feature_ratio=0.7, hf_enhance=hf_enhance, hf_strength=hf_strength)
            elif mix_mode == 'pixel':
                result = self.style_mix_pixel_level(content_img, style_imgs, weights, alpha)
                if hf_enhance and len(style_imgs) > 0:
                    result = self.hf_enhancer.enhance_numpy(result, style_imgs[0], strength=hf_strength)
                    result = self.hf_enhancer.unsharp_mask(result, sigma=1.0, strength=hf_strength * 0.3)
                return result
            else:
                result = self.style_mix_feature_level(content_img, style_imgs, weights, alpha)
                if hf_enhance and len(style_imgs) > 0:
                    result = self.hf_enhancer.enhance_numpy(result, style_imgs[0], strength=hf_strength)
                    result = self.hf_enhancer.unsharp_mask(result, sigma=1.0, strength=hf_strength * 0.3)
                return result
        elif method == 'diffusion':
            result = None
            for style_img, weight in zip(style_imgs, weights):
                mixed = self.diffusion_decomposer.reconstruct(content_img, style_img, alpha * weight)
                if result is None:
                    result = mixed.astype(np.float64) * weight
                else:
                    result += mixed.astype(np.float64) * weight
            result = np.clip(result, 0, 255).astype(np.uint8)
            if hf_enhance and len(style_imgs) > 0:
                result = self.hf_enhancer.unsharp_mask(result, sigma=1.0, strength=hf_strength * 0.3)
            return result
        else:
            raise ValueError(f"Unknown method: {method}")

    def multi_keyframe_interpolation(self, content_img, style_keyframes, num_frames_per_seg=10,
                                     alpha=1.0, hf_enhance=True, hf_strength=0.5):
        all_frames = []
        n = len(style_keyframes)
        for seg in range(n - 1):
            seg_frames = self.style_interpolation(
                content_img, style_keyframes[seg], style_keyframes[seg + 1],
                interpolation_steps=num_frames_per_seg, alpha=alpha,
                hf_enhance=hf_enhance, hf_strength=hf_strength
            )
            if seg < n - 2:
                seg_frames = seg_frames[:-1]
            all_frames.extend(seg_frames)
        return all_frames

    def style_mix_lowres_preview(self, content_img, style_imgs, weights=None, alpha=1.0,
                                  method='adain', preview_size=128):
        preview_content = cv2.resize(content_img, (preview_size, preview_size))
        preview_styles = [cv2.resize(s, (preview_size, preview_size)) for s in style_imgs]

        result = self.style_mix(preview_content, preview_styles, weights, alpha, method,
                               hf_enhance=False)
        return result

    def blend_styles(self, style_img1, style_img2, blend_ratio=0.5):
        style1_tensor = self.preprocess(style_img1)
        style2_tensor = self.preprocess(style_img2)

        style1_feats = self.adain_decomposer.adain.encode_style(style1_tensor)
        style2_feats = self.adain_decomposer.adain.encode_style(style2_tensor)

        blended_feats = []
        for s1, s2 in zip(style1_feats, style2_feats):
            blended = blend_ratio * s1 + (1 - blend_ratio) * s2
            blended_feats.append(blended)

        return blended_feats

    def style_interpolation(self, content_img, style_img1, style_img2,
                           interpolation_steps=5, alpha=1.0, hf_enhance=True, hf_strength=0.5):
        results = []
        for i in range(interpolation_steps):
            ratio = i / (interpolation_steps - 1) if interpolation_steps > 1 else 0
            blended_feats = self.blend_styles(style_img1, style_img2, ratio)

            content_tensor = self.preprocess(content_img)
            content_feats = self.adain_decomposer.adain.encode_content(content_tensor)

            result = self.adain_decomposer.reconstruct_from_features(
                content_feats, blended_feats, alpha
            )

            if hf_enhance:
                result = self.hf_enhancer.enhance_numpy(result, style_img1, strength=hf_strength * ratio)
                result = self.hf_enhancer.enhance_numpy(result, style_img2, strength=hf_strength * (1 - ratio))

            results.append(result)
        return results

    def adjust_style_intensity(self, content_img, style_img,
                               min_alpha=0.0, max_alpha=1.0, num_steps=5,
                               hf_enhance=True, hf_strength=0.5):
        results = []
        alphas = np.linspace(min_alpha, max_alpha, num_steps)
        for alpha in alphas:
            result = self.style_swap(content_img, style_img, alpha=alpha, method='adain',
                                    hf_enhance=hf_enhance, hf_strength=hf_strength * alpha)
            results.append(result)
        return results, alphas

    def regional_style_transfer(self, content_img, style_img, mask, alpha=1.0, hf_enhance=True, hf_strength=0.5):
        if isinstance(mask, np.ndarray):
            mask = mask.astype(np.float32) / 255.0
            if len(mask.shape) == 3:
                mask = mask[:, :, 0]

        content_tensor = self.preprocess(content_img)
        style_tensor = self.preprocess(style_img)

        stylized = self.style_swap(content_img, style_img, alpha=alpha, method='adain',
                                   hf_enhance=hf_enhance, hf_strength=hf_strength)
        stylized_tensor = self.preprocess(stylized)

        content_resized = cv2.resize(
            cv2.cvtColor(content_img, cv2.COLOR_BGR2RGB) if isinstance(content_img, np.ndarray) else np.array(content_img),
            (512, 512)
        )
        stylized_resized = cv2.resize(stylized, (512, 512))
        mask_resized = cv2.resize(mask, (512, 512))

        if len(mask_resized.shape) == 2:
            mask_resized = mask_resized[:, :, np.newaxis]

        result = stylized_resized * mask_resized + content_resized * (1 - mask_resized)
        return result.astype(np.uint8)

    def clip_guided_style_transfer(self, content_img, style_img,
                                    target_text=None, num_iterations=10, lr=0.01, alpha=1.0):
        content_tensor = self.preprocess(content_img).requires_grad_(True)
        style_tensor = self.preprocess(style_img)

        content_feats = self.adain_decomposer.adain.encode_content(content_tensor)
        style_feats = self.adain_decomposer.adain.encode_style(style_tensor)

        t = self.adain_decomposer.adain.style_transfer(content_feats[-1], style_feats, alpha)
        stylized = self.adain_decomposer.adain.decode(t)

        optimizer = torch.optim.Adam([content_tensor], lr=lr)

        for _ in range(num_iterations):
            optimizer.zero_grad()

            content_feats = self.adain_decomposer.adain.encode_content(content_tensor)
            t = self.adain_decomposer.adain.style_transfer(content_feats[-1], style_feats, alpha)
            stylized = self.adain_decomposer.adain.decode(t)

            if target_text is not None:
                text_emb = self.clip_encoder.encode_text(target_text)
                img_emb = self.clip_encoder.encode_image(stylized)
                clip_loss = 1.0 - torch.cosine_similarity(img_emb, text_emb).mean()
            else:
                style_emb = self.clip_encoder.encode_image(style_tensor)
                img_emb = self.clip_encoder.encode_image(stylized)
                clip_loss = 1.0 - torch.cosine_similarity(img_emb, style_emb).mean()

            clip_loss.backward()
            optimizer.step()

        return self.postprocess(stylized)

    def color_transfer(self, content_img, style_img):
        content_lab = cv2.cvtColor(content_img, cv2.COLOR_BGR2LAB)
        style_lab = cv2.cvtColor(style_img, cv2.COLOR_BGR2LAB)

        content_mean, content_std = cv2.meanStdDev(content_lab)
        style_mean, style_std = cv2.meanStdDev(style_lab)

        result_lab = np.zeros_like(content_lab, dtype=np.float32)
        for i in range(3):
            result_lab[:, :, i] = ((content_lab[:, :, i] - content_mean[i]) *
                                   (style_std[i] / (content_std[i] + 1e-5)) + style_mean[i])

        result_lab = np.clip(result_lab, 0, 255).astype(np.uint8)
        return cv2.cvtColor(result_lab, cv2.COLOR_LAB2BGR)

    def histogram_matching(self, content_img, style_img):
        if len(content_img.shape) == 3:
            result = np.zeros_like(content_img)
            for i in range(3):
                result[:, :, i] = self._match_histogram(
                    content_img[:, :, i], style_img[:, :, i]
                )
            return result
        else:
            return self._match_histogram(content_img, style_img)

    def _match_histogram(self, source, template):
        source_shape = source.shape
        source_flat = source.flatten()
        template_flat = template.flatten()

        source_values, source_indices, source_counts = np.unique(
            source_flat, return_inverse=True, return_counts=True
        )
        template_values, template_counts = np.unique(
            template_flat, return_counts=True
        )

        source_quantiles = np.cumsum(source_counts) / source_flat.size
        template_quantiles = np.cumsum(template_counts) / template_flat.size

        interp_t_values = np.interp(source_quantiles, template_quantiles, template_values)
        return interp_t_values[source_indices].reshape(source_shape).astype(source.dtype)
