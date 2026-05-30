import json
import os
from typing import Dict, Any, List, Optional
from tone_mapping import ToneMappingOperator


class PresetManager:
    def __init__(self, preset_file: str = "presets.json"):
        self.preset_file = preset_file
        self.presets: Dict[str, Dict[str, Any]] = {}
        self._load_presets()

    def _load_presets(self):
        if os.path.exists(self.preset_file):
            try:
                with open(self.preset_file, 'r', encoding='utf-8') as f:
                    self.presets = json.load(f)
            except Exception as e:
                print(f"Error loading presets: {e}")
                self.presets = {}
        else:
            self._create_default_presets()
            self._save_presets()

    def _save_presets(self):
        try:
            with open(self.preset_file, 'w', encoding='utf-8') as f:
                json.dump(self.presets, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving presets: {e}")

    def _create_default_presets(self):
        self.presets = {
            "Reinhard - Default": {
                "operator": ToneMappingOperator.REINHARD.value,
                "params": {
                    'intensity': 0.0,
                    'light_adapt': 1.0,
                    'color_adapt': 0.0,
                    'gamma': 2.2
                }
            },
            "Reinhard - Bright": {
                "operator": ToneMappingOperator.REINHARD.value,
                "params": {
                    'intensity': 1.0,
                    'light_adapt': 0.8,
                    'color_adapt': 0.3,
                    'gamma': 2.2
                }
            },
            "Reinhard - Warm": {
                "operator": ToneMappingOperator.REINHARD.value,
                "params": {
                    'intensity': 0.5,
                    'light_adapt': 0.6,
                    'color_adapt': 0.8,
                    'gamma': 2.2
                }
            },
            "Filmic - Default": {
                "operator": ToneMappingOperator.FILMIC.value,
                "params": {
                    'contrast': 1.0,
                    'shoulder': 0.5,
                    'linear': 0.1,
                    'linear_angle': 0.1,
                    'toe': 0.01,
                    'toe_num_a': 0.55,
                    'toe_num_b': 0.01,
                    'toe_den_a': 0.4,
                    'toe_den_b': 0.02,
                    'gamma': 2.2
                }
            },
            "Filmic - High Contrast": {
                "operator": ToneMappingOperator.FILMIC.value,
                "params": {
                    'contrast': 1.5,
                    'shoulder': 0.4,
                    'linear': 0.15,
                    'linear_angle': 0.15,
                    'toe': 0.005,
                    'toe_num_a': 0.6,
                    'toe_num_b': 0.005,
                    'toe_den_a': 0.3,
                    'toe_den_b': 0.01,
                    'gamma': 2.2
                }
            },
            "ACES - Default": {
                "operator": ToneMappingOperator.ACES.value,
                "params": {
                    'exposure': 1.0,
                    'saturation': 1.0,
                    'gamma': 2.2
                }
            },
            "ACES - Bright": {
                "operator": ToneMappingOperator.ACES.value,
                "params": {
                    'exposure': 1.5,
                    'saturation': 1.1,
                    'gamma': 2.2
                }
            },
            "ACES - Cinematic": {
                "operator": ToneMappingOperator.ACES.value,
                "params": {
                    'exposure': 0.8,
                    'saturation': 0.9,
                    'gamma': 2.4
                }
            }
        }

    def save_preset(self, name: str, operator: ToneMappingOperator, params: Dict[str, float]) -> bool:
        if not name:
            return False
        self.presets[name] = {
            "operator": operator.value,
            "params": params.copy()
        }
        self._save_presets()
        return True

    def load_preset(self, name: str) -> Optional[Dict[str, Any]]:
        preset = self.presets.get(name)
        if preset:
            return {
                "operator": ToneMappingOperator(preset["operator"]),
                "params": preset["params"].copy()
            }
        return None

    def delete_preset(self, name: str) -> bool:
        if name in self.presets:
            del self.presets[name]
            self._save_presets()
            return True
        return False

    def get_preset_names(self) -> List[str]:
        return sorted(list(self.presets.keys()))

    def get_presets_by_operator(self, operator: ToneMappingOperator) -> List[str]:
        return [
            name for name, preset in self.presets.items()
            if preset["operator"] == operator.value
        ]

    def export_presets(self, filepath: str) -> bool:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.presets, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting presets: {e}")
            return False

    def import_presets(self, filepath: str, merge: bool = True) -> bool:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                imported = json.load(f)
            if merge:
                self.presets.update(imported)
            else:
                self.presets = imported
            self._save_presets()
            return True
        except Exception as e:
            print(f"Error importing presets: {e}")
            return False
