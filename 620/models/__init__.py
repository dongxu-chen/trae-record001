from .edsr import create_edsr, EDSR
from .rcan import create_rcan, RCAN


def get_model(model_name, scale=4, **kwargs):
    model_name = model_name.lower()
    if model_name == 'edsr':
        return create_edsr(scale=scale, **kwargs)
    elif model_name == 'rcan':
        return create_rcan(scale=scale, **kwargs)
    else:
        raise ValueError(f"Unknown model: {model_name}. Available: edsr, rcan")


def load_pretrained_weights(model, weight_path, device):
    try:
        checkpoint = torch.load(weight_path, map_location=device)
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
        elif isinstance(checkpoint, dict) and 'params' in checkpoint:
            state_dict = checkpoint['params']
        else:
            state_dict = checkpoint
        
        model_state = model.state_dict()
        pretrained_state = {k: v for k, v in state_dict.items() if k in model_state and v.shape == model_state[k].shape}
        
        if len(pretrained_state) == 0:
            print("Warning: No matching keys found in pretrained weights. Using random init.")
            return model
        
        model_state.update(pretrained_state)
        model.load_state_dict(model_state)
        print(f"Loaded {len(pretrained_state)}/{len(model_state)} pretrained parameters.")
    except Exception as e:
        print(f"Warning: Failed to load pretrained weights: {e}")
        print("Using random initialization.")
    return model


import torch
