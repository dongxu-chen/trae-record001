import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    
    BERT_MODEL_NAME: str = os.getenv("BERT_MODEL_NAME", "bert-base-chinese")
    
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    DISCLOSURE_TEXT: str = """
    【免责声明】
    本系统提供的医疗信息仅供参考和教育目的，不能替代专业医生的诊断和治疗建议。
    如有健康问题，请及时咨询专业医疗人员。
    本系统不对信息的准确性、完整性或可靠性做任何保证。
    使用本系统产生的任何后果，本系统不承担任何责任。
    """

settings = Settings()
