import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RESULT_DIR = os.path.join(BASE_DIR, 'results')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

START_DATE = '2018-01-01'
END_DATE = '2023-12-31'

N_GROUPS = 10

REBALANCE_FREQ = 'M'

RISK_FREE_RATE = 0.03

TRADING_DAYS = 252

FACTOR_NORMALIZE = True

HANDLE_SUSPEND = True
HANDLE_DELIST = True

MAX_MISSING_RATIO = 0.3
