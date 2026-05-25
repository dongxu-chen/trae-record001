import logging
import logging.handlers
import yaml
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_logger(name: str) -> logging.Logger:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "config", "config.yaml"
    )
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    log_config = config["logging"]
    
    logger = logging.getLogger(name)
    logger.setLevel(log_config["level"])
    
    if not logger.handlers:
        formatter = logging.Formatter(log_config["format"])
        
        os.makedirs(os.path.dirname(log_config["file_path"]), exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_config["file_path"],
            maxBytes=log_config["max_bytes"],
            backupCount=log_config["backup_count"]
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger
