import sys
print('Python version:', sys.version)

try:
    import numpy as np
    print('numpy OK:', np.__version__)
except ImportError as e:
    print('numpy MISSING:', e)

try:
    import torch
    print('torch OK:', torch.__version__)
    print('CUDA available:', torch.cuda.is_available())
except ImportError as e:
    print('torch MISSING:', e)

try:
    import sklearn
    print('sklearn OK:', sklearn.__version__)
except ImportError as e:
    print('sklearn MISSING:', e)

try:
    import scipy
    print('scipy OK:', scipy.__version__)
except ImportError as e:
    print('scipy MISSING:', e)

try:
    import matplotlib
    print('matplotlib OK:', matplotlib.__version__)
except ImportError as e:
    print('matplotlib MISSING:', e)

try:
    import seaborn
    print('seaborn OK:', seaborn.__version__)
except ImportError as e:
    print('seaborn MISSING:', e)

try:
    import spectral
    print('spectral OK:', spectral.__version__)
except ImportError as e:
    print('spectral MISSING:', e)

print('\nTesting imports from modules...')
try:
    from data_loader import load_indian_pines, create_data_loaders, apply_pca, create_patches
    print('data_loader imports OK')
except Exception as e:
    print('data_loader imports FAILED:', e)

try:
    from model import CNN3D, CNN3D_Light
    print('model imports OK')
except Exception as e:
    print('model imports FAILED:', e)

try:
    from augmentation import get_train_transforms, RandomFlip, RandomRotate
    print('augmentation imports OK')
except Exception as e:
    print('augmentation imports FAILED:', e)

try:
    from train import train_model, evaluate_model, print_metrics
    print('train imports OK')
except Exception as e:
    print('train imports FAILED:', e)

try:
    from visualization import plot_confusion_matrix, plot_training_history
    print('visualization imports OK')
except Exception as e:
    print('visualization imports FAILED:', e)

print('\nAll checks complete!')
