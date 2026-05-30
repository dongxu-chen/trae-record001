import cv2
import numpy as np
from config import Config
from utils.helpers import min_max_normalize


def get_transforms(image_size=None, train=False):
    if image_size is None:
        image_size = Config.IMAGE_SIZE
    
    import torch
    from torchvision import transforms
    
    if train:
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    else:
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    return transform


def preprocess_image(image, image_size=None):
    import torch
    
    if image_size is None:
        image_size = Config.IMAGE_SIZE
    
    if len(image.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
    
    original_h, original_w = image.shape[:2]
    
    resized = cv2.resize(image, (image_size, image_size), interpolation=cv2.INTER_LINEAR)
    
    normalized = resized.astype(np.float32) / 255.0
    
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    normalized = (normalized - mean) / std
    
    tensor = torch.from_numpy(normalized).permute(2, 0, 1).float()
    tensor = tensor.unsqueeze(0)
    
    return tensor, (original_h, original_w)


def postprocess_saliency(saliency_tensor, original_size, threshold=None):
    try:
        import torch
        if isinstance(saliency_tensor, torch.Tensor):
            saliency = saliency_tensor.detach().cpu().numpy()
        else:
            saliency = saliency_tensor
    except ImportError:
        saliency = saliency_tensor
    
    if saliency.ndim == 4:
        saliency = saliency.squeeze(0)
    if saliency.ndim == 3:
        saliency = saliency.squeeze(0)
    
    saliency = min_max_normalize(saliency)
    
    original_h, original_w = original_size
    saliency = cv2.resize(saliency, (original_w, original_h), interpolation=cv2.INTER_LINEAR)
    
    saliency = min_max_normalize(saliency)
    
    binary_mask = (saliency > threshold).astype(np.float32)
    
    return saliency, binary_mask


def preprocess_batch(images, image_size=None):
    import torch
    
    if image_size is None:
        image_size = Config.IMAGE_SIZE
    
    batch_tensors = []
    original_sizes = []
    
    for image in images:
        tensor, orig_size = preprocess_image(image, image_size)
        batch_tensors.append(tensor)
        original_sizes.append(orig_size)
    
    batch_tensor = torch.cat(batch_tensors, dim=0)
    
    return batch_tensor, original_sizes


def postprocess_batch(saliency_batch, original_sizes, threshold=None):
    if threshold is None:
        threshold = Config.THRESHOLD
    
    results = []
    
    for i in range(saliency_batch.shape[0]):
        saliency = saliency_batch[i:i+1]
        orig_size = original_sizes[i]
        saliency_map, binary_mask = postprocess_saliency(saliency, orig_size, threshold)
        results.append({
            'saliency_map': saliency_map,
            'binary_mask': binary_mask
        })
    
    return results
