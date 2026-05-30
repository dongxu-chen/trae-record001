from kg.neo4j_client import Neo4jClient


class KnowledgeGraphInitializer:
    def __init__(self, client: Neo4jClient):
        self.client = client

    def clear_database(self):
        query = "MATCH (n) DETACH DELETE n"
        self.client.execute_query(query)

    def create_diseases(self):
        diseases = [
            {"name": "感冒", "description": "上呼吸道感染", "category": "呼吸系统疾病", "severity": "轻度"},
            {"name": "肺炎", "description": "肺部感染性疾病", "category": "呼吸系统疾病", "severity": "中度"},
            {"name": "高血压", "description": "血压持续升高", "category": "心血管疾病", "severity": "慢性"},
            {"name": "糖尿病", "description": "血糖代谢异常", "category": "内分泌疾病", "severity": "慢性"},
            {"name": "胃炎", "description": "胃黏膜炎症", "category": "消化系统疾病", "severity": "轻度"},
            {"name": "胃溃疡", "description": "胃黏膜溃疡", "category": "消化系统疾病", "severity": "中度"},
            {"name": "冠心病", "description": "冠状动脉粥样硬化", "category": "心血管疾病", "severity": "严重"},
            {"name": "脑梗塞", "description": "脑血管阻塞", "category": "神经系统疾病", "severity": "严重"}
        ]
        for disease in diseases:
            self.client.create_node("Disease", disease)

    def create_symptoms(self):
        symptoms = [
            {"name": "发烧", "description": "体温升高"},
            {"name": "咳嗽", "description": "呼吸道反射动作"},
            {"name": "头痛", "description": "头部疼痛"},
            {"name": "头晕", "description": "眩晕感"},
            {"name": "腹痛", "description": "腹部疼痛"},
            {"name": "恶心", "description": "胃部不适"},
            {"name": "呕吐", "description": "胃内容物排出"},
            {"name": "胸闷", "description": "胸部压迫感"},
            {"name": "心悸", "description": "心跳加速"},
            {"name": "乏力", "description": "体力下降"},
            {"name": "多饮", "description": "饮水量增加"},
            {"name": "多尿", "description": "尿量增加"},
            {"name": "咳痰", "description": "咳出痰液"},
            {"name": "呼吸困难", "description": "呼吸费力"}
        ]
        for symptom in symptoms:
            self.client.create_node("Symptom", symptom)

    def create_drugs(self):
        drugs = [
            {"name": "阿莫西林", "type": "抗生素", "manufacturer": "华北制药"},
            {"name": "布洛芬", "type": "解热镇痛药", "manufacturer": "中美史克"},
            {"name": "奥美拉唑", "type": "质子泵抑制剂", "manufacturer": "阿斯利康"},
            {"name": "二甲双胍", "type": "降糖药", "manufacturer": "施贵宝"},
            {"name": "硝苯地平", "type": "降压药", "manufacturer": "拜耳"},
            {"name": "阿司匹林", "type": "抗血小板药", "manufacturer": "拜耳"},
            {"name": "头孢拉定", "type": "抗生素", "manufacturer": "白云山"},
            {"name": "氨溴索", "type": "祛痰药", "manufacturer": "勃林格殷格翰"}
        ]
        for drug in drugs:
            self.client.create_node("Drug", drug)

    def create_departments(self):
        departments = [
            {"name": "呼吸内科", "description": "呼吸系统疾病诊疗"},
            {"name": "心血管内科", "description": "心血管疾病诊疗"},
            {"name": "消化内科", "description": "消化系统疾病诊疗"},
            {"name": "内分泌科", "description": "内分泌疾病诊疗"},
            {"name": "神经内科", "description": "神经系统疾病诊疗"},
            {"name": "急诊科", "description": "急诊救治"}
        ]
        for dept in departments:
            self.client.create_node("Department", dept)

    def create_doctors(self):
        doctors = [
            {"name": "张医生", "title": "主任医师", "specialty": "呼吸系统疾病"},
            {"name": "李医生", "title": "副主任医师", "specialty": "心血管疾病"},
            {"name": "王医生", "title": "主治医师", "specialty": "消化系统疾病"},
            {"name": "赵医生", "title": "副主任医师", "specialty": "内分泌疾病"}
        ]
        for doctor in doctors:
            self.client.create_node("Doctor", doctor)

    def create_treatments(self):
        treatments = [
            {"name": "抗生素治疗", "description": "使用抗生素杀灭细菌"},
            {"name": "退热治疗", "description": "降低体温"},
            {"name": "降压治疗", "description": "降低血压"},
            {"name": "降糖治疗", "description": "控制血糖"},
            {"name": "护胃治疗", "description": "保护胃黏膜"},
            {"name": "溶栓治疗", "description": "溶解血栓"},
            {"name": "氧疗", "description": "氧气吸入治疗"}
        ]
        for treatment in treatments:
            self.client.create_node("Treatment", treatment)

    def create_examinations(self):
        examinations = [
            {"name": "血常规", "description": "血液常规检查"},
            {"name": "胸部CT", "description": "胸部计算机断层扫描"},
            {"name": "心电图", "description": "心脏电活动检查"},
            {"name": "血糖检测", "description": "血糖水平检测"},
            {"name": "胃镜", "description": "胃部内窥镜检查"},
            {"name": "头颅CT", "description": "头部计算机断层扫描"}
        ]
        for exam in examinations:
            self.client.create_node("Examination", exam)

    def create_relationships(self):
        disease_symptom = [
            ("感冒", "发烧"), ("感冒", "咳嗽"), ("感冒", "头痛"), ("感冒", "乏力"),
            ("肺炎", "发烧"), ("肺炎", "咳嗽"), ("肺炎", "咳痰"), ("肺炎", "呼吸困难"),
            ("高血压", "头痛"), ("高血压", "头晕"), ("高血压", "心悸"),
            ("糖尿病", "多饮"), ("糖尿病", "多尿"), ("糖尿病", "乏力"),
            ("胃炎", "腹痛"), ("胃炎", "恶心"), ("胃炎", "呕吐"),
            ("胃溃疡", "腹痛"), ("胃溃疡", "恶心"), ("胃溃疡", "呕吐"),
            ("冠心病", "胸闷"), ("冠心病", "心悸"),
            ("脑梗塞", "头痛"), ("脑梗塞", "头晕")
        ]
        for disease, symptom in disease_symptom:
            self.client.create_relationship(
                "Disease", "name", disease,
                "Symptom", "name", symptom,
                "HAS_SYMPTOM"
            )

        disease_drug = [
            ("感冒", "阿莫西林"), ("感冒", "布洛芬"),
            ("肺炎", "阿莫西林"), ("肺炎", "头孢拉定"), ("肺炎", "氨溴索"),
            ("高血压", "硝苯地平"), ("高血压", "阿司匹林"),
            ("糖尿病", "二甲双胍"),
            ("胃炎", "奥美拉唑"),
            ("胃溃疡", "奥美拉唑"),
            ("冠心病", "阿司匹林"), ("冠心病", "硝苯地平"),
            ("脑梗塞", "阿司匹林")
        ]
        for disease, drug in disease_drug:
            self.client.create_relationship(
                "Disease", "name", disease,
                "Drug", "name", drug,
                "USES_DRUG"
            )

        disease_department = [
            ("感冒", "呼吸内科"),
            ("肺炎", "呼吸内科"),
            ("高血压", "心血管内科"),
            ("糖尿病", "内分泌科"),
            ("胃炎", "消化内科"),
            ("胃溃疡", "消化内科"),
            ("冠心病", "心血管内科"),
            ("脑梗塞", "神经内科")
        ]
        for disease, dept in disease_department:
            self.client.create_relationship(
                "Disease", "name", disease,
                "Department", "name", dept,
                "BELONGS_TO_DEPARTMENT"
            )

        disease_treatment = [
            ("感冒", "退热治疗"),
            ("肺炎", "抗生素治疗"), ("肺炎", "氧疗"),
            ("高血压", "降压治疗"),
            ("糖尿病", "降糖治疗"),
            ("胃炎", "护胃治疗"),
            ("胃溃疡", "护胃治疗"),
            ("冠心病", "溶栓治疗")
        ]
        for disease, treatment in disease_treatment:
            self.client.create_relationship(
                "Disease", "name", disease,
                "Treatment", "name", treatment,
                "HAS_TREATMENT"
            )

        disease_examination = [
            ("感冒", "血常规"),
            ("肺炎", "血常规"), ("肺炎", "胸部CT"),
            ("高血压", "心电图"),
            ("糖尿病", "血糖检测"),
            ("胃炎", "胃镜"),
            ("胃溃疡", "胃镜"),
            ("冠心病", "心电图"),
            ("脑梗塞", "头颅CT")
        ]
        for disease, exam in disease_examination:
            self.client.create_relationship(
                "Disease", "name", disease,
                "Examination", "name", exam,
                "NEEDS_EXAMINATION"
            )

        doctor_disease = [
            ("张医生", "感冒"), ("张医生", "肺炎"),
            ("李医生", "高血压"), ("李医生", "冠心病"),
            ("王医生", "胃炎"), ("王医生", "胃溃疡"),
            ("赵医生", "糖尿病")
        ]
        for doctor, disease in doctor_disease:
            self.client.create_relationship(
                "Doctor", "name", doctor,
                "Disease", "name", disease,
                "TREATS_DISEASE"
            )

    def initialize_all(self):
        print("开始初始化知识图谱...")
        self.clear_database()
        print("创建疾病节点...")
        self.create_diseases()
        print("创建症状节点...")
        self.create_symptoms()
        print("创建药物节点...")
        self.create_drugs()
        print("创建科室节点...")
        self.create_departments()
        print("创建医生节点...")
        self.create_doctors()
        print("创建治疗方法节点...")
        self.create_treatments()
        print("创建检查项目节点...")
        self.create_examinations()
        print("创建关系...")
        self.create_relationships()
        print("知识图谱初始化完成！")


if __name__ == "__main__":
    from kg.neo4j_client import neo4j_client
    initializer = KnowledgeGraphInitializer(neo4j_client)
    initializer.initialize_all()
