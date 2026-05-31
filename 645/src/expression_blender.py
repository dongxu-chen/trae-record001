import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class BlendMode(Enum):
    ADDITIVE = 'additive'
    MULTIPLICATIVE = 'multiplicative'
    MAXIMUM = 'maximum'
    MINIMUM = 'minimum'
    AVERAGE = 'average'
    WEIGHTED = 'weighted'


@dataclass
class ExpressionLayer:
    name: str
    weights: Dict[str, float] = field(default_factory=dict)
    influence: float = 1.0
    enabled: bool = True
    blend_mode: BlendMode = BlendMode.ADDITIVE
    
    def apply(self, base_params: Dict[str, float]) -> Dict[str, float]:
        if not self.enabled or self.influence <= 0:
            return base_params.copy()
        
        result = base_params.copy()
        influence = max(0.0, min(1.0, self.influence))
        
        for param_name, weight in self.weights.items():
            if param_name not in result:
                result[param_name] = 0.0
            
            effective_weight = weight * influence
            
            if self.blend_mode == BlendMode.ADDITIVE:
                result[param_name] += effective_weight
            elif self.blend_mode == BlendMode.MULTIPLICATIVE:
                result[param_name] *= (1.0 + effective_weight)
            elif self.blend_mode == BlendMode.MAXIMUM:
                result[param_name] = max(result[param_name], effective_weight)
            elif self.blend_mode == BlendMode.MINIMUM:
                result[param_name] = min(result[param_name], effective_weight)
            elif self.blend_mode == BlendMode.AVERAGE:
                result[param_name] = (result[param_name] + effective_weight) / 2
            elif self.blend_mode == BlendMode.WEIGHTED:
                result[param_name] = result[param_name] * (1 - influence) + effective_weight * influence
        
        return result


@dataclass
class PresetExpression:
    name: str
    description: str
    au_combination: Dict[str, float]
    target_params: Dict[str, float]


class ExpressionLibrary:
    def __init__(self):
        self.presets = self._init_presets()
    
    def _init_presets(self) -> Dict[str, PresetExpression]:
        return {
            'happy': PresetExpression(
                'happy', '开心',
                {'AU6': 0.8, 'AU12': 0.9, 'AU25': 0.3},
                {'smile': 0.9, 'mouth_open': 0.3, 'brow_inner_up': 0.1}
            ),
            'sad': PresetExpression(
                'sad', '悲伤',
                {'AU1': 0.5, 'AU4': 0.6, 'AU15': 0.7},
                {'frown': 0.7, 'mouth_open': 0.2, 'brow_inner_up': 0.5}
            ),
            'angry': PresetExpression(
                'angry', '愤怒',
                {'AU4': 0.9, 'AU5': 0.7, 'AU7': 0.6, 'AU23': 0.5},
                {'frown': 0.5, 'mouth_open': 0.4, 'brow_inner_up': -0.8}
            ),
            'surprised': PresetExpression(
                'surprised', '惊讶',
                {'AU1': 0.8, 'AU2': 0.8, 'AU5': 0.9, 'AU26': 0.8},
                {'mouth_open': 0.8, 'jaw_open': 0.7, 'brow_inner_up': 0.8}
            ),
            'fear': PresetExpression(
                'fear', '恐惧',
                {'AU1': 0.7, 'AU2': 0.7, 'AU4': 0.5, 'AU5': 0.8, 'AU20': 0.6},
                {'mouth_open': 0.6, 'mouth_wide': 0.6, 'brow_inner_up': 0.7}
            ),
            'disgust': PresetExpression(
                'disgust', '厌恶',
                {'AU9': 0.8, 'AU10': 0.7, 'AU17': 0.6, 'AU25': 0.3},
                {'mouth_open': 0.3, 'frown': 0.4, 'brow_inner_up': -0.3}
            ),
            'contempt': PresetExpression(
                'contempt', '轻蔑',
                {'AU12': 0.3, 'AU14': 0.6},
                {'smile': 0.3, 'frown': 0.2}
            ),
            'neutral': PresetExpression(
                'neutral', '中性',
                {},
                {}
            ),
            'excited': PresetExpression(
                'excited', '兴奋',
                {'AU1': 0.6, 'AU2': 0.6, 'AU5': 0.7, 'AU12': 0.8, 'AU25': 0.6},
                {'smile': 0.8, 'mouth_open': 0.6, 'brow_inner_up': 0.6, 'eye_open_left': 0.9}
            ),
            'thinking': PresetExpression(
                'thinking', '思考',
                {'AU4': 0.3, 'AU17': 0.2, 'AU23': 0.3},
                {'frown': 0.3, 'mouth_open': 0.1, 'brow_inner_up': -0.3}
            ),
            'suspicious': PresetExpression(
                'suspicious', '怀疑',
                {'AU4': 0.5, 'AU7': 0.4, 'AU14': 0.2},
                {'frown': 0.4, 'eye_open_left': 0.6}
            ),
            'playful': PresetExpression(
                'playful', '调皮',
                {'AU6': 0.5, 'AU12': 0.6, 'AU14': 0.4},
                {'smile': 0.6, 'eye_open_left': 0.8}
            ),
            'shy': PresetExpression(
                'shy', '害羞',
                {'AU6': 0.4, 'AU12': 0.3, 'AU14': 0.2},
                {'smile': 0.3, 'eye_open_left': 0.6}
            ),
            'kiss': PresetExpression(
                'kiss', '亲吻',
                {'AU18': 0.9, 'AU28': 0.3},
                {'mouth_open': 0.2, 'mouth_narrow': 0.9}
            ),
            'laugh': PresetExpression(
                'laugh', '大笑',
                {'AU6': 0.9, 'AU12': 1.0, 'AU25': 0.8, 'AU26': 0.7},
                {'smile': 1.0, 'mouth_open': 0.8, 'jaw_open': 0.7}
            ),
            'scream': PresetExpression(
                'scream', '尖叫',
                {'AU1': 0.8, 'AU2': 0.8, 'AU4': 0.6, 'AU5': 0.9, 'AU26': 1.0, 'AU27': 0.9},
                {'mouth_open': 1.0, 'jaw_open': 0.9, 'brow_inner_up': 0.8}
            ),
            'whisper': PresetExpression(
                'whisper', '低语',
                {'AU17': 0.4, 'AU23': 0.3, 'AU25': 0.2},
                {'mouth_open': 0.2, 'jaw_open': 0.1}
            ),
        }
    
    def get_preset(self, name: str) -> Optional[PresetExpression]:
        return self.presets.get(name.lower())
    
    def list_presets(self) -> List[str]:
        return list(self.presets.keys())


class ExpressionBlender:
    def __init__(self):
        self.layers: List[ExpressionLayer] = []
        self.library = ExpressionLibrary()
        self.global_params: Dict[str, float] = {}
        
        self.master_gain: float = 1.0
        self.smoothing_factor: float = 0.2
        self.prev_blended_params: Dict[str, float] = {}
        
        self.au_influence: Dict[str, float] = {}
        
        self._init_default_layers()

    def _init_default_layers(self):
        tracking_layer = ExpressionLayer(
            name='facial_tracking',
            weights={},
            influence=1.0,
            blend_mode=BlendMode.WEIGHTED
        )
        self.layers.append(tracking_layer)
        
        emotion_layer = ExpressionLayer(
            name='emotion_preset',
            weights={},
            influence=0.5,
            blend_mode=BlendMode.ADDITIVE
        )
        self.layers.append(emotion_layer)
        
        correction_layer = ExpressionLayer(
            name='correction',
            weights={},
            influence=1.0,
            blend_mode=BlendMode.WEIGHTED
        )
        self.layers.append(correction_layer)

    def add_layer(self, name: str, weights: Dict[str, float], 
                  influence: float = 1.0, 
                  blend_mode: BlendMode = BlendMode.ADDITIVE) -> int:
        layer = ExpressionLayer(
            name=name,
            weights=weights,
            influence=influence,
            blend_mode=blend_mode
        )
        self.layers.append(layer)
        return len(self.layers) - 1

    def remove_layer(self, index: int):
        if 0 < index < len(self.layers):
            del self.layers[index]

    def get_layer(self, name: str) -> Optional[ExpressionLayer]:
        for layer in self.layers:
            if layer.name == name:
                return layer
        return None

    def set_layer_weights(self, layer_name: str, weights: Dict[str, float]):
        layer = self.get_layer(layer_name)
        if layer:
            layer.weights = weights

    def set_layer_influence(self, layer_name: str, influence: float):
        layer = self.get_layer(layer_name)
        if layer:
            layer.influence = max(0.0, min(1.0, influence))

    def set_layer_enabled(self, layer_name: str, enabled: bool):
        layer = self.get_layer(layer_name)
        if layer:
            layer.enabled = enabled

    def apply_preset(self, preset_name: str, influence: float = 1.0):
        preset = self.library.get_preset(preset_name)
        if not preset:
            return False
        
        emotion_layer = self.get_layer('emotion_preset')
        if emotion_layer:
            emotion_layer.weights = preset.target_params.copy()
            emotion_layer.influence = influence
        
        self._update_au_influence(preset.au_combination)
        return True

    def _update_au_influence(self, au_weights: Dict[str, float]):
        for au_id, weight in au_weights.items():
            self.au_influence[au_id] = weight

    def set_tracking_params(self, params: Dict[str, float]):
        tracking_layer = self.get_layer('facial_tracking')
        if tracking_layer:
            tracking_layer.weights = params.copy()

    def blend(self, base_params: Dict[str, float]) -> Dict[str, float]:
        result = base_params.copy()
        
        for layer in self.layers:
            result = layer.apply(result)
        
        for param_name in result:
            result[param_name] *= self.master_gain
            
            if param_name in ['eye_x', 'eye_y', 'brow_inner_up', 'brow_outer_up', 
                             'brow_left_up', 'brow_right_up']:
                result[param_name] = max(-1.0, min(1.0, result[param_name]))
            else:
                result[param_name] = max(0.0, min(1.0, result[param_name]))
        
        if self.prev_blended_params:
            for param_name in result:
                if param_name in self.prev_blended_params:
                    result[param_name] = (
                        (1 - self.smoothing_factor) * self.prev_blended_params[param_name] +
                        self.smoothing_factor * result[param_name]
                    )
        
        self.prev_blended_params = result.copy()
        
        return result

    def blend_with_aus(self, base_params: Dict[str, float], 
                       au_params: Dict[str, float]) -> Dict[str, float]:
        self.set_tracking_params(base_params)
        
        au_modified = base_params.copy()
        
        for au_id, intensity in au_params.items():
            if intensity <= 0:
                continue
                
            target_params = self._au_to_params(au_id, intensity)
            for param_name, value in target_params.items():
                if param_name in au_modified:
                    au_modified[param_name] = max(au_modified[param_name], value)
                else:
                    au_modified[param_name] = value
        
        result = self.blend(au_modified)
        return result

    def _au_to_params(self, au_id: str, intensity: float) -> Dict[str, float]:
        au_mapping = {
            'AU1': {'brow_inner_up': intensity},
            'AU2': {'brow_outer_up': intensity},
            'AU4': {'brow_inner_up': -intensity},
            'AU5': {'eye_open_left': intensity, 'eye_open_right': intensity},
            'AU6': {'smile': intensity * 0.5},
            'AU7': {'blink_left': intensity * 0.3, 'blink_right': intensity * 0.3},
            'AU9': {'frown': intensity * 0.5},
            'AU10': {'mouth_open': intensity * 0.3, 'smile': intensity * 0.2},
            'AU12': {'smile': intensity},
            'AU14': {'smile': intensity * 0.4, 'frown': intensity * 0.1},
            'AU15': {'frown': intensity},
            'AU17': {'mouth_open': intensity * 0.2},
            'AU18': {'mouth_narrow': intensity},
            'AU20': {'mouth_wide': intensity},
            'AU23': {'mouth_open': intensity * 0.1, 'mouth_narrow': intensity * 0.2},
            'AU25': {'mouth_open': intensity},
            'AU26': {'jaw_open': intensity},
            'AU27': {'mouth_open': intensity, 'jaw_open': intensity * 0.8},
            'AU43': {'blink_left': intensity, 'blink_right': intensity},
            'AU45': {'blink_left': intensity, 'blink_right': intensity},
        }
        
        return au_mapping.get(au_id, {})

    def create_custom_expression(self, name: str, params: Dict[str, float], 
                                 influence: float = 1.0) -> int:
        return self.add_layer(name, params, influence, BlendMode.ADDITIVE)

    def reset(self):
        for layer in self.layers:
            if layer.name == 'facial_tracking':
                continue
            layer.weights.clear()
            layer.influence = 0.0
        
        self.au_influence.clear()
        self.prev_blended_params.clear()

    def get_blend_info(self) -> Dict:
        return {
            'master_gain': self.master_gain,
            'layers': [
                {
                    'name': layer.name,
                    'influence': layer.influence,
                    'enabled': layer.enabled,
                    'blend_mode': layer.blend_mode.value,
                    'param_count': len(layer.weights)
                }
                for layer in self.layers
            ],
            'active_aus': {k: v for k, v in self.au_influence.items() if v > 0.1},
            'available_presets': self.library.list_presets()
        }
