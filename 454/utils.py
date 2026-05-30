import os
import yaml
import logging
import math
from typing import Dict, Any, List
import logging.handlers


def calculate_adaptive_embedding_dim(vocab_size: int, min_dim: int = 4, 
                                     max_dim: int = 64, scale_factor: float = 0.25) -> int:
    """
    根据特征基数自适应计算嵌入维度
    公式: embedding_dim = min(max_dim, max(min_dim, int(vocab_size ** scale_factor)))
    
    Args:
        vocab_size: 词汇表大小
        min_dim: 最小嵌入维度
        max_dim: 最大嵌入维度
        scale_factor: 缩放因子
    
    Returns:
        自适应的嵌入维度
    """
    if vocab_size <= 1:
        return min_dim
    dim = int(math.pow(vocab_size, scale_factor))
    return max(min_dim, min(max_dim, dim))


def get_feature_embedding_dims(vocab_sizes: Dict[str, int], 
                                min_dim: int = 4, 
                                max_dim: int = 64,
                                scale_factor: float = 0.25) -> Dict[str, int]:
    """
    为所有特征计算自适应嵌入维度
    
    Args:
        vocab_sizes: 各特征的词汇表大小字典
        min_dim: 最小嵌入维度
        max_dim: 最大嵌入维度
        scale_factor: 缩放因子
    
    Returns:
        各特征的嵌入维度字典
    """
    embedding_dims = {}
    for feat_name, vocab_size in vocab_sizes.items():
        embedding_dims[feat_name] = calculate_adaptive_embedding_dim(
            vocab_size, min_dim, max_dim, scale_factor
        )
    return embedding_dims


def load_config(config_path: str = "configs/config.yaml") -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_feature_config(config_path: str = "configs/feature_config.yaml") -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logger(name: str, config: Dict[str, Any]) -> logging.Logger:
    log_config = config.get("logging", {})
    log_level = log_config.get("level", "INFO")
    log_format = log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log_file = log_config.get("file_path", "./logs/platform.log")

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(log_format)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
