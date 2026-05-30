ENTITY_TYPES = {
    "Disease": "疾病",
    "Symptom": "症状",
    "Drug": "药物",
    "Department": "科室",
    "Doctor": "医生",
    "Hospital": "医院",
    "Treatment": "治疗方法",
    "Examination": "检查项目"
}

RELATION_TYPES = {
    "HAS_SYMPTOM": "有症状",
    "USES_DRUG": "使用药物",
    "BELONGS_TO_DEPARTMENT": "属于科室",
    "TREATS_DISEASE": "治疗疾病",
    "WORKS_IN": "就职于",
    "NEEDS_EXAMINATION": "需要检查",
    "HAS_TREATMENT": "有治疗方法",
    "HAS_COMPLICATION": "有并发症"
}

INTENT_TYPES = [
    "disease_symptom",
    "disease_drug",
    "disease_department",
    "disease_treatment",
    "disease_examination",
    "drug_disease",
    "symptom_disease",
    "department_disease",
    "doctor_disease",
    "multi_hop",
    "fuzzy_query"
]

RELATION_INTENT_MAP = {
    "disease_symptom": {"relation": "HAS_SYMPTOM", "direction": "out", "target": "Disease", "source": "Disease"},
    "disease_drug": {"relation": "USES_DRUG", "direction": "out", "target": "Drug", "source": "Disease"},
    "disease_department": {"relation": "BELONGS_TO_DEPARTMENT", "direction": "out", "target": "Department", "source": "Disease"},
    "disease_treatment": {"relation": "HAS_TREATMENT", "direction": "out", "target": "Treatment", "source": "Disease"},
    "disease_examination": {"relation": "NEEDS_EXAMINATION", "direction": "out", "target": "Examination", "source": "Disease"},
    "drug_disease": {"relation": "USES_DRUG", "direction": "in", "target": "Disease", "source": "Drug"},
    "symptom_disease": {"relation": "HAS_SYMPTOM", "direction": "in", "target": "Disease", "source": "Symptom"},
    "department_disease": {"relation": "BELONGS_TO_DEPARTMENT", "direction": "in", "target": "Disease", "source": "Department"},
    "doctor_disease": {"relation": "TREATS_DISEASE", "direction": "in", "target": "Disease", "source": "Doctor"}
}

ENTITY_SYNONYMS = {
    "感冒": ["感冒", "伤风", "上呼吸道感染", "感冒病"],
    "发烧": ["发烧", "发热", "高烧", "低烧"],
    "咳嗽": ["咳嗽", "干咳", "咳痰"],
    "头痛": ["头痛", "头疼", "头部疼痛"],
    "阿莫西林": ["阿莫西林", "阿莫仙", "阿莫灵"],
    "布洛芬": ["布洛芬", "芬必得", "美林"]
}
