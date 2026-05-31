import os
from typing import List

class Settings:
    PROJECT_NAME: str = "法律文书相似案例检索系统"
    VERSION: str = "2.0.0"
    
    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "localhost")
    ELASTICSEARCH_PORT: int = int(os.getenv("ELASTICSEARCH_PORT", 9200))
    ELASTICSEARCH_INDEX: str = "legal_cases"
    
    BERT_MODEL_NAME: str = "paraphrase-multilingual-MiniLM-L12-v2"
    MAX_SEQ_LENGTH: int = 512
    
    TOP_K_SIMILAR_CASES: int = 10
    SIMILARITY_THRESHOLD: float = 0.6
    
    LEGAL_ENTITY_TYPES: List[str] = [
        "原告", "被告", "第三人", "律师", "法官",
        "合同", "协议", "借条", "欠条", "判决书",
        "金额", "日期", "地点", "证据", "法条",
        "罪名", "法院", "诉讼请求", "量刑建议",
    ]
    
    SENTENCING_FACTOR_TYPES: List[str] = [
        "犯罪情节", "主观恶性", "社会危害", "悔罪表现",
        "累犯前科", "从重情节", "从轻情节", "量刑幅度", "损害结果",
    ]
    
    LAW_SYNC_INTERVAL_DAYS: int = 7

    @property
    def LAW_ARTICLES(self) -> dict:
        try:
            from law_sync_service import law_sync_service
            return law_sync_service.get_laws_for_knowledge_graph()
        except:
            pass
        return {
            "民法典-第一百四十三条": "具备下列条件的民事法律行为有效：（一）行为人具有相应的民事行为能力；（二）意思表示真实；（三）不违反法律、行政法规的强制性规定，不违背公序良俗。",
            "民法典-第五百零二条": "依法成立的合同，自成立时生效，但是法律另有规定或者当事人另有约定的除外。",
            "民法典-第五百七十七条": "当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。",
            "民法典-第六百六十七条": "借款合同是借款人向贷款人借款，到期返还借款并支付利息的合同。",
            "民法典-第六百八十条": "禁止高利放贷，借款的利率不得违反国家有关规定。",
            "民事诉讼法-第六十七条": "当事人对自己提出的主张，有责任提供证据。",
            "民事诉讼法-第一百二十二条": "起诉必须符合下列条件：（一）原告是与本案有直接利害关系的公民、法人和其他组织；（二）有明确的被告；（三）有具体的诉讼请求和事实、理由；（四）属于人民法院受理民事诉讼的范围和受诉人民法院管辖。",
        }

settings = Settings()
