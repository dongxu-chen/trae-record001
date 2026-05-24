import numpy as np

STABILITY_CLASSES = ['A', 'B', 'C', 'D', 'E', 'F']

STABILITY_DESCRIPTIONS = {
    'A': '极不稳定',
    'B': '中等不稳定',
    'C': '弱不稳定',
    'D': '中性',
    'E': '弱稳定',
    'F': '中等稳定'
}

def get_sigma_coefficients(stability_class):
    coeffs = {
        'A': {'sigma_y': [0.22, 0.0001, -0.5],
              'sigma_z': [0.20, 0.0001, 0.0]},
        'B': {'sigma_y': [0.16, 0.0001, -0.5],
              'sigma_z': [0.12, 0.0001, 0.0]},
        'C': {'sigma_y': [0.11, 0.0001, -0.5],
              'sigma_z': [0.08, 0.0001, 0.0]},
        'D': {'sigma_y': [0.08, 0.0001, -0.5],
              'sigma_z': [0.06, 0.0001, 0.0]},
        'E': {'sigma_y': [0.06, 0.0001, -0.5],
              'sigma_z': [0.03, 0.0001, 0.0]},
        'F': {'sigma_y': [0.04, 0.0001, -0.5],
              'sigma_z': [0.016, 0.0001, 0.0]}
    }
    return coeffs[stability_class]

def calculate_sigma_y(x, stability_class):
    x = np.asarray(x, dtype=float)
    coeffs = get_sigma_coefficients(stability_class)
    a, b, c = coeffs['sigma_y']
    sigma_y = a * x / (1 + b * x) ** c
    return sigma_y

def calculate_sigma_z(x, stability_class):
    x = np.asarray(x, dtype=float)
    coeffs = get_sigma_coefficients(stability_class)
    a, b, c = coeffs['sigma_z']
    sigma_z = a * x / (1 + b * x) ** c
    return sigma_z

def get_mixing_layer_height(stability_class, default=1000.0):
    heights = {
        'A': 1500.0,
        'B': 1200.0,
        'C': 1000.0,
        'D': 800.0,
        'E': 600.0,
        'F': 400.0
    }
    return heights.get(stability_class, default)
