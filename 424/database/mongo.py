"""
MongoDB连接管理
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from loguru import logger
from config import MONGODB


class MongoDBManager:
    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._connect()

    def _connect(self):
        try:
            if MONGODB.get('username') and MONGODB.get('password'):
                uri = (
                    f"mongodb://{MONGODB['username']}:{MONGODB['password']}"
                    f"@{MONGODB['host']}:{MONGODB['port']}/{MONGODB['database']}"
                )
            else:
                uri = f"mongodb://{MONGODB['host']}:{MONGODB['port']}"

            self._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self._db = self._client[MONGODB['database']]
            self._client.admin.command('ping')
            logger.info(f"MongoDB连接成功: {MONGODB['host']}:{MONGODB['port']}/{MONGODB['database']}")
        except ConnectionFailure as e:
            logger.error(f"MongoDB连接失败: {e}")
            raise

    @property
    def db(self):
        return self._db

    @property
    def client(self):
        return self._client

    def get_collection(self, name):
        return self._db[name]

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB连接已关闭")


def get_db():
    return MongoDBManager().db


def get_collection(name):
    return MongoDBManager().get_collection(name)