import cv2
import numpy as np
import torch
from PIL import Image
import matplotlib.pyplot as plt


def load_image(image_path, size=None, normalize=True):
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Cannot load image from {image_path}")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    if size is not None:
        if isinstance(size, int):
            h, w = img.shape[:2]
            if h > w:
                new_h, new_w = size * h // w, size
            else:
                new_h, new_w = size, size * w // h
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    
    if normalize:
        img = img.astype(np.float32) / 255.0
    
    return img


def save_image(image, save_path, normalize=True):
    if isinstance(image, torch.Tensor):
        image = tensor2img(image)
    
    if normalize:
        image = (image * 255).astype(np.uint8)
    
    if len(image.shape) == 3 and image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    
    cv2.imwrite(save_path, image)


def tensor2img(tensor, normalize=True):
    tensor = tensor.detach().cpu()
    if tensor.dim() == 4:
        tensor = tensor.squeeze(0)
    
    img = tensor.permute(1, 2, 0).numpy()
    
    if normalize:
        img = (img - img.min()) / (img.max() - img.min() + 1e-8)
    
    return np.clip(img, 0, 1)


def img2tensor(img, device='cpu'):
    if isinstance(img, str):
        img = load_image(img, normalize=True)
    
    tensor = torch.from_numpy(img).permute(2, 0, 1).float()
    return tensor.unsqueeze(0).to(device)


def mask2tensor(mask, device='cpu'):
    if len(mask.shape) == 2:
        mask = mask[:, :, np.newaxis]
    tensor = torch.from_numpy(mask).permute(2, 0, 1).float()
    return tensor.unsqueeze(0).to(device)


def visualize_results(original, mask, result, figsize=(15, 5), save_path=None):
    fig, axes = plt.subplots(1, 3, figsize=figsize)
    
    if isinstance(original, torch.Tensor):
        original = tensor2img(original)
    if isinstance(mask, torch.Tensor):
        mask = tensor2img(mask)
        if mask.shape[2] == 1:
            mask = mask.repeat(3, axis=2)
    if isinstance(result, torch.Tensor):
        result = tensor2img(result)
    
    axes[0].imshow(original)
    axes[0].set_title('Original Image')
    axes[0].axis('off')
    
    masked_img = original * (1 - mask) + mask
    axes[1].imshow(masked_img)
    axes[1].set_title('Masked Image')
    axes[1].axis('off')
    
    axes[2].imshow(result)
    axes[2].set_title('Inpainted Result')
    axes[2].axis('off')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


def create_directory(path):
    import os
    os.makedirs(path, exist_ok=True)


def get_image_list(directory, extensions=('.jpg', '.jpeg', '.png', '.bmp')):
    import os
    image_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(extensions):
                image_list.append(os.path.join(root, file))
    return sorted(image_list)


def poisson_blend(inpainted, original, mask, method='mixed', feather_radius=5):
    if isinstance(inpainted, torch.Tensor):
        inpainted = tensor2img(inpainted)
    if isinstance(original, torch.Tensor):
        original = tensor2img(original)
    if isinstance(mask, torch.Tensor):
        mask = tensor2img(mask)
    
    if mask.ndim == 3 and mask.shape[2] == 1:
        mask_2d = (mask[:, :, 0] * 255).astype(np.uint8)
    elif mask.ndim == 2:
        mask_2d = (mask * 255).astype(np.uint8)
    else:
        mask_2d = (mask[:, :, 0] * 255).astype(np.uint8)
    
    src = (inpainted * 255).astype(np.uint8)
    dst = (original * 255).astype(np.uint8)
    
    contours, _ = cv2.findContours(mask_2d.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return inpainted
    
    largest_contour = max(contours, key=cv2.contourArea)
    
    if cv2.contourArea(largest_contour) < 4:
        return inpainted
    
    M = cv2.moments(largest_contour)
    if M['m00'] == 0:
        return inpainted
    
    center_x = int(M['m10'] / M['m00'])
    center_y = int(M['m01'] / M['m00'])
    center = (center_x, center_y)
    
    if method == 'seamless_normal':
        blended = cv2.seamlessClone(src, dst, mask_2d, center, cv2.NORMAL_CLONE)
    elif method == 'seamless_mixed':
        blended = cv2.seamlessClone(src, dst, mask_2d, center, cv2.MIXED_CLONE)
    elif method == 'feathered':
        blended = _feather_blend(inpainted, original, mask, feather_radius)
    elif method == 'gradient':
        blended = _gradient_blend(inpainted, original, mask)
    elif method == 'multi_pass':
        blended = _multi_pass_blend(src, dst, mask_2d, center)
    else:
        blended = cv2.seamlessClone(src, dst, mask_2d, center, cv2.MIXED_CLONE)
    
    result = blended.astype(np.float32) / 255.0
    result = np.clip(result, 0, 1)
    
    return result


def _feather_blend(inpainted, original, mask, feather_radius=5):
    if mask.ndim == 2:
        mask_3d = mask[:, :, np.newaxis]
    elif mask.ndim == 3 and mask.shape[2] == 1:
        mask_3d = mask
    else:
        mask_3d = mask[:, :, :1]
    
    mask_uint8 = (mask_3d[:, :, 0] * 255).astype(np.uint8)
    
    kernel_size = feather_radius * 2 + 1
    blurred_mask = cv2.GaussianBlur(mask_uint8, (kernel_size, kernel_size), 0)
    alpha = blurred_mask.astype(np.float32) / 255.0
    alpha = alpha[:, :, np.newaxis]
    
    edge_region = cv2.Canny(mask_uint8, 50, 150)
    edge_dilated = cv2.dilate(edge_region, 
                               cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (feather_radius * 2 + 1, feather_radius * 2 + 1)))
    transition_weight = edge_dilated.astype(np.float32) / 255.0
    transition_weight = cv2.GaussianBlur(transition_weight, (kernel_size, kernel_size), 0)
    transition_weight = transition_weight[:, :, np.newaxis]
    
    blend_weight = alpha * (1.0 - transition_weight * 0.3)
    blend_weight = np.clip(blend_weight, 0, 1)
    
    blended = inpainted * blend_weight + original * (1 - blend_weight)
    
    return (blended * 255).astype(np.uint8)


def _gradient_blend(inpainted, original, mask):
    src = (inpainted * 255).astype(np.float32)
    dst = (original * 255).astype(np.float32)
    
    if mask.ndim == 2:
        mask_f = mask.astype(np.float32)
    else:
        mask_f = mask[:, :, 0].astype(np.float32)
    
    kernel_size = 7
    blurred_mask = cv2.GaussianBlur(mask_f, (kernel_size, kernel_size), 0)
    
    border_width = 10
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (border_width * 2 + 1, border_width * 2 + 1))
    mask_uint8 = (mask_f * 255).astype(np.uint8)
    border_mask = cv2.dilate(mask_uint8, kernel_dilate) - mask_uint8
    border_mask = border_mask.astype(np.float32) / 255.0
    border_mask = cv2.GaussianBlur(border_mask, (kernel_size, kernel_size), 0)
    border_mask = np.clip(border_mask, 0, 1)
    
    if border_mask.ndim == 2:
        border_mask = border_mask[:, :, np.newaxis]
    
    grad_x_src = cv2.Sobel(src, cv2.CV_32F, 1, 0, ksize=3)
    grad_y_src = cv2.Sobel(src, cv2.CV_32F, 0, 1, ksize=3)
    grad_x_dst = cv2.Sobel(dst, cv2.CV_32F, 1, 0, ksize=3)
    grad_y_dst = cv2.Sobel(dst, cv2.CV_32F, 0, 1, ksize=3)
    
    blended_grad_x = grad_x_src * border_mask + grad_x_dst * (1 - border_mask)
    blended_grad_y = grad_y_src * border_mask + grad_y_dst * (1 - border_mask)
    
    result = dst.copy()
    
    if mask_f.ndim == 2:
        mask_3d = mask_f[:, :, np.newaxis]
    else:
        mask_3d = mask_f
    
    result = src * mask_3d + dst * (1 - mask_3d)
    
    laplacian_src = cv2.Laplacian(src, cv2.CV_32F)
    laplacian_dst = cv2.Laplacian(dst, cv2.CV_32F)
    blended_laplacian = laplacian_src * border_mask + laplacian_dst * (1 - border_mask)
    
    correction = blended_laplacian - (laplacian_src * mask_3d + laplacian_dst * (1 - mask_3d))
    result = result + correction * 0.3
    
    return np.clip(result, 0, 255).astype(np.uint8)


def _multi_pass_blend(src, dst, mask_2d, center):
    result = src.copy()
    
    for i in range(3):
        erode_size = (i + 1) * 3 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_size, erode_size))
        eroded_mask = cv2.erode(mask_2d, kernel, iterations=1)
        
        contours, _ = cv2.findContours(eroded_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            break
        
        largest_contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest_contour) < 4:
            break
        
        M = cv2.moments(largest_contour)
        if M['m00'] == 0:
            break
        
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        
        blend_strength = 0.3 + 0.2 * i
        try:
            blended = cv2.seamlessClone(result, dst, eroded_mask, (cx, cy), cv2.MIXED_CLONE)
            alpha = blend_strength
            result = (result.astype(np.float32) * (1 - alpha) + blended.astype(np.float32) * alpha).astype(np.uint8)
        except cv2.error:
            break
    
    return result


def estimate_gpu_memory_per_image(height, width, channels=3, model_name='partialconv'):
    base_mem = height * width * channels * 4
    mask_mem = height * width * 4
    
    if model_name == 'partialconv':
        model_params_mem = 50 * 1024 * 1024
        activation_mem = height * width * 512 * 4 * 8
    elif model_name == 'edgeconnect':
        model_params_mem = 40 * 1024 * 1024
        activation_mem = height * width * 256 * 4 * 8
    else:
        model_params_mem = 50 * 1024 * 1024
        activation_mem = height * width * 512 * 4 * 8
    
    total = base_mem + mask_mem + activation_mem
    
    overhead = 256 * 1024 * 1024
    
    return total + overhead


def get_available_gpu_memory(device='cuda'):
    if not torch.cuda.is_available():
        return 0
    
    if isinstance(device, str):
        device_id = 0 if device == 'cuda' else int(device.split(':')[-1])
    else:
        device_id = device.index if hasattr(device, 'index') else 0
    
    torch.cuda.synchronize(device_id)
    total_mem = torch.cuda.get_device_properties(device_id).total_memory
    allocated_mem = torch.cuda.memory_allocated(device_id)
    reserved_mem = torch.cuda.memory_reserved(device_id)
    
    available = total_mem - allocated_mem - reserved_mem
    
    return max(available - 256 * 1024 * 1024, 0)


def compute_optimal_batch_size(height, width, device='cuda', model_name='partialconv',
                                safety_factor=0.8):
    if not torch.cuda.is_available():
        return 1
    
    available_mem = get_available_gpu_memory(device)
    per_image_mem = estimate_gpu_memory_per_image(height, width, model_name=model_name)
    
    if per_image_mem == 0:
        return 1
    
    batch_size = int(available_mem * safety_factor / per_image_mem)
    batch_size = max(1, min(batch_size, 32))
    
    return batch_size
