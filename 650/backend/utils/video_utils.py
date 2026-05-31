from typing import List, Optional, Tuple

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont


def preprocess_frame(
    frame: np.ndarray,
    target_size: Tuple[int, int],
    mean: Tuple[float, float, float],
    std: Tuple[float, float, float]
) -> torch.Tensor:
    if not isinstance(frame, np.ndarray):
        raise TypeError("frame must be a numpy.ndarray")
    
    if len(frame.shape) != 3 or frame.shape[2] != 3:
        raise ValueError("frame must be a 3-channel BGR image with shape (H, W, 3)")
    
    try:
        resized = cv2.resize(frame, target_size, interpolation=cv2.INTER_LINEAR)
        
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        normalized = rgb.astype(np.float32) / 255.0
        
        mean_arr = np.array(mean, dtype=np.float32).reshape(1, 1, 3)
        std_arr = np.array(std, dtype=np.float32).reshape(1, 1, 3)
        normalized = (normalized - mean_arr) / std_arr
        
        tensor = torch.from_numpy(normalized).permute(2, 0, 1)
        
        return tensor
    except Exception as e:
        raise RuntimeError(f"Frame preprocessing failed: {str(e)}") from e


def assemble_clip(
    frames: List[torch.Tensor],
    num_frames: int,
    sampling_rate: int
) -> torch.Tensor:
    if not frames:
        raise ValueError("frames list cannot be empty")
    
    if not all(isinstance(f, torch.Tensor) for f in frames):
        raise TypeError("All elements in frames must be torch.Tensor")
    
    if num_frames <= 0:
        raise ValueError("num_frames must be a positive integer")
    
    if sampling_rate <= 0:
        raise ValueError("sampling_rate must be a positive integer")
    
    try:
        total_needed = num_frames * sampling_rate
        frame_count = len(frames)
        
        if frame_count < total_needed:
            pad_count = total_needed - frame_count
            last_frame = frames[-1]
            padded_frames = frames + [last_frame.clone() for _ in range(pad_count)]
        else:
            padded_frames = frames[:total_needed]
        
        sampled_indices = list(range(0, total_needed, sampling_rate))
        sampled_frames = [padded_frames[i] for i in sampled_indices]
        
        clip = torch.stack(sampled_frames, dim=0)
        
        clip = clip.permute(1, 0, 2, 3)
        
        return clip.unsqueeze(0)
    except Exception as e:
        raise RuntimeError(f"Clip assembly failed: {str(e)}") from e


def tensor_to_numpy(tensor: torch.Tensor) -> np.ndarray:
    if not isinstance(tensor, torch.Tensor):
        raise TypeError("tensor must be a torch.Tensor")
    
    try:
        if tensor.requires_grad:
            tensor = tensor.detach()
        
        if tensor.is_cuda:
            tensor = tensor.cpu()
        
        arr = tensor.numpy()
        
        if arr.ndim == 4:
            arr = arr.squeeze(0)
        
        if arr.ndim == 3 and arr.shape[0] in (1, 3):
            arr = arr.transpose(1, 2, 0)
        
        if arr.ndim == 3 and arr.shape[2] == 3:
            if arr.max() <= 1.0:
                arr = arr * 255.0
            arr = arr.clip(0, 255).astype(np.uint8)
            arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        
        return arr
    except Exception as e:
        raise RuntimeError(f"Tensor to numpy conversion failed: {str(e)}") from e


def draw_action_label(
    frame: np.ndarray,
    action: str,
    confidence: float,
    position: Optional[Tuple[int, int]] = None,
    font_size: int = 20,
    color: Optional[Tuple[int, int, int]] = None
) -> np.ndarray:
    if not isinstance(frame, np.ndarray):
        raise TypeError("frame must be a numpy.ndarray")
    
    if len(frame.shape) != 3 or frame.shape[2] != 3:
        raise ValueError("frame must be a 3-channel BGR image with shape (H, W, 3)")
    
    try:
        frame_copy = frame.copy()
        
        h, w = frame_copy.shape[:2]
        
        if position is None:
            position = (20, 30)
        
        if color is None:
            color = (0, 255, 0) if confidence >= 0.7 else (0, 165, 255) if confidence >= 0.5 else (0, 0, 255)
        
        label = f"{action}: {confidence:.2f}"
        
        try:
            pil_image = Image.fromarray(cv2.cvtColor(frame_copy, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_image)
            
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except (IOError, OSError):
                font = ImageFont.load_default()
            
            bbox = draw.textbbox(position, label, font=font)
            padding = 5
            draw.rectangle(
                [
                    bbox[0] - padding,
                    bbox[1] - padding,
                    bbox[2] + padding,
                    bbox[3] + padding
                ],
                fill=(0, 0, 0, 180)
            )
            draw.text(position, label, font=font, fill=(color[2], color[1], color[0]))
            
            frame_copy = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        except Exception:
            cv2.putText(
                frame_copy,
                label,
                position,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
                cv2.LINE_AA
            )
        
        return frame_copy
    except Exception as e:
        raise RuntimeError(f"Drawing action label failed: {str(e)}") from e
