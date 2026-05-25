import numpy as np

STANDARD_WAVELENGTHS = {
    't': 1.014,  # Mercury
    's': 0.852,  # Cesium
    'A': 0.768,  # Potassium
    'r': 0.707,  # Helium
    'C': 0.656,  # Hydrogen
    "C'": 0.644, # Cadmium
    'He-Ne': 0.633, # He-Ne Laser
    'D': 0.589,  # Sodium
    'd': 0.587,  # Helium
    'e': 0.546,  # Mercury
    "F'": 0.480, # Cadmium
    'F': 0.486,  # Hydrogen
    'g': 0.436,  # Mercury
    'h': 0.405,  # Mercury
    'i': 0.365,  # Mercury
}

WAVELENGTH_COLORS = {
    0.365: '#8B00FF',
    0.405: '#7B00FF',
    0.436: '#6A00FF',
    0.486: '#0000FF',
    0.480: '#0011FF',
    0.546: '#00AA00',
    0.587: '#00FF00',
    0.589: '#00FF00',
    0.633: '#FF3300',
    0.644: '#FF4400',
    0.656: '#FF0000',
    0.707: '#FF4500',
    0.768: '#FF6600',
    0.852: '#FF8800',
    1.014: '#FFAA00',
}

WAVELENGTH_NAMES = {
    0.365: 'i (365nm)',
    0.405: 'h (405nm)',
    0.436: 'g (436nm)',
    0.486: 'F (486nm)',
    0.480: "F' (480nm)",
    0.546: 'e (546nm)',
    0.587: 'd (587nm)',
    0.589: 'D (589nm)',
    0.633: 'He-Ne (633nm)',
    0.644: "C' (644nm)",
    0.656: 'C (656nm)',
    0.707: 'r (707nm)',
    0.768: 'A (768nm)',
    0.852: 's (852nm)',
    1.014: 't (1014nm)',
}

DEFAULT_WAVELENGTHS_VISIBLE = [0.436, 0.486, 0.546, 0.587, 0.633, 0.656, 0.707]
DEFAULT_WAVELENGTHS_ABERRATION = [0.486, 0.587, 0.656]
DEFAULT_WAVELENGTHS_FULL = sorted(STANDARD_WAVELENGTHS.values())

GLASS_CATALOG = {
    'BK7': {
        'B1': 1.03961212, 'B2': 0.231792344, 'B3': 1.01046945,
        'C1': 0.00600069867, 'C2': 0.0200179144, 'C3': 103.560653,
        'nd': 1.5168, 'Vd': 64.17
    },
    'SF11': {
        'B1': 1.73848403, 'B2': 0.311168974, 'B3': 1.17490871,
        'C1': 0.0136068604, 'C2': 0.0615960463, 'C3': 121.922711,
        'nd': 1.78472, 'Vd': 25.76
    },
    'F2': {
        'B1': 1.34533359, 'B2': 0.209073176, 'B3': 0.937357162,
        'C1': 0.00997743871, 'C2': 0.0470450767, 'C3': 111.886764,
        'nd': 1.62004, 'Vd': 36.37
    },
    'BAK1': {
        'B1': 1.12030807, 'B2': 0.309538294, 'B3': 0.881180415,
        'C1': 0.00585778594, 'C2': 0.0211683244, 'C3': 108.115723,
        'nd': 1.57250, 'Vd': 53.38
    },
    'air': {
        'B1': 0, 'B2': 0, 'B3': 0,
        'C1': 1, 'C2': 1, 'C3': 1,
        'nd': 1.0, 'Vd': 0
    }
}

def sellmeier_equation(glass_type, wavelength_um):
    if glass_type not in GLASS_CATALOG:
        raise ValueError(f"Unknown glass type: {glass_type}")
    g = GLASS_CATALOG[glass_type]
    if glass_type == 'air':
        return 1.0
    wl2 = wavelength_um ** 2
    n_sq = 1 + g['B1'] * wl2 / (wl2 - g['C1']) + \
               g['B2'] * wl2 / (wl2 - g['C2']) + \
               g['B3'] * wl2 / (wl2 - g['C3'])
    return np.sqrt(n_sq)

def refractive_index(glass_type, wavelength_um=0.587):
    if glass_type == 'air':
        return np.ones_like(wavelength_um) if hasattr(wavelength_um, '__len__') else 1.0
    return sellmeier_equation(glass_type, wavelength_um)

def focal_length_to_power(f):
    return 1.0 / f

def power_to_focal_length(P):
    return 1.0 / P
