from .basnet import BASNet
from .poolnet import PoolNet
from config import Config


MODEL_REGISTRY = {
    'basnet': {
        'class': BASNet,
        'checkpoint': Config.BASNET_CHECKPOINT,
        'description': 'BASNet: Boundary-Aware Salient Object Detection'
    },
    'poolnet': {
        'class': PoolNet,
        'checkpoint': Config.POOLNET_CHECKPOINT,
        'description': 'PoolNet: A Simple Pooling-Based Framework for Salient Object Detection'
    }
}


def get_model(model_name, pretrained=True, device='cpu'):
    model_name = model_name.lower()
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f"Model '{model_name}' not found. Available models: {list(MODEL_REGISTRY.keys())}")
    
    model_info = MODEL_REGISTRY[model_name]
    model = model_info['class']()
    
    if pretrained:
        model.load_checkpoint(model_info['checkpoint'], device)
    
    model = model.to(device)
    model.eval()
    
    return model


def list_models():
    return {name: info['description'] for name, info in MODEL_REGISTRY.items()}
