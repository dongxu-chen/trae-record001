import os
import json
from pathlib import Path
from typing import Dict, Tuple


BASE_DIR = Path(__file__).parent

RATING_CONFIG_FILE = BASE_DIR / "model" / "saved_models" / "rating_thresholds.json"

NEO4J_CONFIG = {
    "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    "user": os.getenv("NEO4J_USER", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", "password"),
    "database": os.getenv("NEO4J_DATABASE", "neo4j"),
}

MODEL_PATH = BASE_DIR / "model" / "saved_models"
MODEL_PATH.mkdir(parents=True, exist_ok=True)

XGB_MODEL_FILE = MODEL_PATH / "xgb_credit_model.json"
SCALER_FILE = MODEL_PATH / "scaler.pkl"
FEATURE_NAMES_FILE = MODEL_PATH / "feature_names.json"
SHAP_EXPLAINER_FILE = MODEL_PATH / "shap_explainer.pkl"

CREDIT_SCORE_MIN = 0
CREDIT_SCORE_MAX = 1000

DEFAULT_RATING_THRESHOLDS = {
    "AAA": (900, 1000),
    "AA": (800, 900),
    "A": (700, 800),
    "BBB": (600, 700),
    "BB": (500, 600),
    "B": (400, 500),
    "CCC": (300, 400),
    "CC": (200, 300),
    "C": (100, 200),
    "D": (0, 100),
}


def save_rating_thresholds(thresholds: Dict[str, Tuple[float, float]]) -> None:
    serializable = {k: [v[0], v[1]] for k, v in thresholds.items()}
    with open(RATING_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)


def load_rating_thresholds() -> Dict[str, Tuple[float, float]]:
    if RATING_CONFIG_FILE.exists():
        try:
            with open(RATING_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {k: (v[0], v[1]) for k, v in data.items()}
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
    save_rating_thresholds(DEFAULT_RATING_THRESHOLDS)
    return DEFAULT_RATING_THRESHOLDS.copy()


def get_rating_thresholds() -> Dict[str, Tuple[float, float]]:
    return load_rating_thresholds()


def update_rating_threshold(rating: str, lower: float, upper: float) -> Dict[str, Tuple[float, float]]:
    thresholds = load_rating_thresholds()
    thresholds[rating] = (lower, upper)
    save_rating_thresholds(thresholds)
    return thresholds


RISK_LEVELS = {
    "AAA": "极低风险",
    "AA": "很低风险",
    "A": "低风险",
    "BBB": "较低风险",
    "BB": "中等风险",
    "B": "较高风险",
    "CCC": "高风险",
    "CC": "很高风险",
    "C": "极高风险",
    "D": "破产风险",
}

KG_FEATURE_WEIGHTS = {
    "legal_relation_score": 0.15,
    "shareholder_quality_score": 0.10,
    "industry_peer_score": 0.08,
    "supply_chain_stability_score": 0.12,
    "association_risk_score": 0.05,
}

KG_TIME_DECAY = {
    "enabled": True,
    "half_life_days": 365,
    "max_decay_days": 3650,
    "min_weight": 0.1,
    "relation_types": {
        "OWNS": 730,
        "MANAGES": 540,
        "SUPPLIES_TO": 365,
        "HAS_LEGAL_RELATION": 730,
        "BELONGS_TO": 3650,
    },
}

XGB_PARAMS = {
    "n_estimators": 500,
    "max_depth": 8,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "min_child_weight": 5,
    "gamma": 0.1,
    "random_state": 42,
    "objective": "reg:squarederror",
}

INDUSTRY_MONITORING_CONFIG = {
    "default": {
        "score_drop_alert_threshold": 50,
        "score_warning_threshold": 30,
        "negative_event_weight": {
            "lawsuit": 30,
            "executed_person": 80,
            "tax_arrears": 40,
            "abnormal_operation": 60,
            "administrative_penalty": 25,
            "contract_breach": 35,
            "patent_invalidation": 20,
        },
        "check_interval_days": 30,
    },
    "金融业": {
        "score_drop_alert_threshold": 40,
        "score_warning_threshold": 25,
        "negative_event_weight": {
            "lawsuit": 40,
            "executed_person": 100,
            "tax_arrears": 50,
            "abnormal_operation": 80,
            "administrative_penalty": 35,
            "contract_breach": 45,
            "patent_invalidation": 15,
        },
        "check_interval_days": 15,
    },
    "房地产": {
        "score_drop_alert_threshold": 45,
        "score_warning_threshold": 28,
        "negative_event_weight": {
            "lawsuit": 35,
            "executed_person": 90,
            "tax_arrears": 50,
            "abnormal_operation": 70,
            "administrative_penalty": 30,
            "contract_breach": 40,
            "patent_invalidation": 10,
        },
        "check_interval_days": 20,
    },
    "建筑业": {
        "score_drop_alert_threshold": 55,
        "score_warning_threshold": 32,
        "negative_event_weight": {
            "lawsuit": 40,
            "executed_person": 85,
            "tax_arrears": 35,
            "abnormal_operation": 55,
            "administrative_penalty": 30,
            "contract_breach": 45,
            "patent_invalidation": 15,
        },
        "check_interval_days": 25,
    },
    "制造业": {
        "score_drop_alert_threshold": 55,
        "score_warning_threshold": 35,
        "negative_event_weight": {
            "lawsuit": 25,
            "executed_person": 75,
            "tax_arrears": 35,
            "abnormal_operation": 55,
            "administrative_penalty": 22,
            "contract_breach": 30,
            "patent_invalidation": 25,
        },
        "check_interval_days": 30,
    },
    "信息技术": {
        "score_drop_alert_threshold": 50,
        "score_warning_threshold": 30,
        "negative_event_weight": {
            "lawsuit": 28,
            "executed_person": 70,
            "tax_arrears": 38,
            "abnormal_operation": 60,
            "administrative_penalty": 25,
            "contract_breach": 32,
            "patent_invalidation": 30,
        },
        "check_interval_days": 30,
    },
    "生物医药": {
        "score_drop_alert_threshold": 45,
        "score_warning_threshold": 28,
        "negative_event_weight": {
            "lawsuit": 30,
            "executed_person": 80,
            "tax_arrears": 42,
            "abnormal_operation": 65,
            "administrative_penalty": 28,
            "contract_breach": 35,
            "patent_invalidation": 35,
        },
        "check_interval_days": 25,
    },
    "新能源": {
        "score_drop_alert_threshold": 48,
        "score_warning_threshold": 30,
        "negative_event_weight": {
            "lawsuit": 28,
            "executed_person": 75,
            "tax_arrears": 40,
            "abnormal_operation": 60,
            "administrative_penalty": 26,
            "contract_breach": 33,
            "patent_invalidation": 28,
        },
        "check_interval_days": 28,
    },
    "批发零售": {
        "score_drop_alert_threshold": 55,
        "score_warning_threshold": 35,
        "negative_event_weight": {
            "lawsuit": 25,
            "executed_person": 70,
            "tax_arrears": 40,
            "abnormal_operation": 55,
            "administrative_penalty": 20,
            "contract_breach": 35,
            "patent_invalidation": 15,
        },
        "check_interval_days": 30,
    },
    "交通运输": {
        "score_drop_alert_threshold": 55,
        "score_warning_threshold": 35,
        "negative_event_weight": {
            "lawsuit": 28,
            "executed_person": 75,
            "tax_arrears": 35,
            "abnormal_operation": 58,
            "administrative_penalty": 28,
            "contract_breach": 32,
            "patent_invalidation": 15,
        },
        "check_interval_days": 30,
    },
    "文化教育": {
        "score_drop_alert_threshold": 55,
        "score_warning_threshold": 35,
        "negative_event_weight": {
            "lawsuit": 25,
            "executed_person": 70,
            "tax_arrears": 40,
            "abnormal_operation": 55,
            "administrative_penalty": 22,
            "contract_breach": 30,
            "patent_invalidation": 18,
        },
        "check_interval_days": 30,
    },
}

INDUSTRY_RISK_BASELINES = {
    "金融业": {"baseline_score": 650, "volatility": 0.18},
    "房地产": {"baseline_score": 580, "volatility": 0.22},
    "建筑业": {"baseline_score": 550, "volatility": 0.20},
    "制造业": {"baseline_score": 600, "volatility": 0.15},
    "信息技术": {"baseline_score": 620, "volatility": 0.18},
    "生物医药": {"baseline_score": 580, "volatility": 0.25},
    "新能源": {"baseline_score": 590, "volatility": 0.23},
    "批发零售": {"baseline_score": 560, "volatility": 0.16},
    "交通运输": {"baseline_score": 570, "volatility": 0.17},
    "文化教育": {"baseline_score": 580, "volatility": 0.16},
    "default": {"baseline_score": 600, "volatility": 0.18},
}


def get_industry_config(industry: str) -> dict:
    return INDUSTRY_MONITORING_CONFIG.get(industry, INDUSTRY_MONITORING_CONFIG["default"])


def get_industry_baseline(industry: str) -> dict:
    return INDUSTRY_RISK_BASELINES.get(industry, INDUSTRY_RISK_BASELINES["default"])
