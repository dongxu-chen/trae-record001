import torch

class Config:
    DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    BATCH_SIZE = 8
    LEARNING_RATE = 1e-4
    NUM_EPOCHS = 50
    
    IMAGE_SIZE = (256, 256)
    
    RAIN_INTENSITIES = {
        'light': {'num_streaks': (50, 100), 'length': (20, 40), 'thickness': (1, 2), 'opacity': (0.3, 0.5)},
        'medium': {'num_streaks': (100, 200), 'length': (30, 60), 'thickness': (1, 3), 'opacity': (0.4, 0.6)},
        'heavy': {'num_streaks': (200, 400), 'length': (40, 80), 'thickness': (2, 4), 'opacity': (0.5, 0.8)}
    }
    
    TRAIN_DATA_DIR = 'data/train'
    TEST_DATA_DIR = 'data/test'
    CHECKPOINT_DIR = 'checkpoints'
    RESULT_DIR = 'results'
    
    NUM_RES_BLOCKS = 16
    NUM_CHANNELS = 64
    
    USE_ADVERSARIAL = True
    ADV_LOSS_WEIGHT = 0.001
    PIXEL_LOSS_WEIGHT = 100.0
    EDGE_LOSS_WEIGHT = 0.3
    TV_LOSS_WEIGHT = 0.1
    
    DISCRIMINATOR_TYPE = 'patch'
    GAN_LOSS_TYPE = 'lsgan'
    DISCRIMINATOR_LR = 1e-4
    
    USE_EDGE_LOSS = True
    EDGE_LOSS_TYPE = 'sobel'
    
    OBJECTIVE_WEIGHT = 0.6
    SUBJECTIVE_WEIGHT = 0.4
