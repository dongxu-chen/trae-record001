import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///shorturl.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SHORT_CODE_LENGTH = 8
    DEFAULT_EXPIRY_DAYS = 30
    MAX_EXPIRY_DAYS = 365
    CLEANUP_INTERVAL_HOURS = 24
    MAX_SHORT_CODE_ATTEMPTS = 20


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SHORT_CODE_LENGTH = 8


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
