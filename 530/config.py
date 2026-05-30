import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BFM_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'BFM_model_front.mat')
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
CHECKPOINT_DIR = os.path.join(BASE_DIR, 'checkpoints')

IMG_SIZE = 224
SHAPE_DIM = 199
EXP_DIM = 29
TEX_DIM = 199
POSE_DIM = 6
LIGHT_DIM = 27

NUM_LANDMARKS = 68

DEVICE = 'cuda'
BATCH_SIZE = 32
LEARNING_RATE = 1e-4
NUM_EPOCHS = 50

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'models'), exist_ok=True)
