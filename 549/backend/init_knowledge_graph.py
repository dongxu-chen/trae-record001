import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from neo4j_db import Neo4jDatabase

def init_medical_knowledge():
    db = Neo4jDatabase()
    db.connect()
    
    print("开始初始化医疗知识图谱...")
    
    db.execute_query("""
    CREATE CONSTRAINT IF NOT EXISTS FOR (d:Disease)
    ASSERT d.name IS UNIQUE
    """)
    
    db.execute_query("""
    CREATE CONSTRAINT IF NOT EXISTS FOR (s:Symptom)
    ASSERT s.name IS UNIQUE
    """)
    
    db.execute_query("""
    CREATE CONSTRAINT IF NOT EXISTS FOR (m:Medicine)
    ASSERT m.name IS UNIQUE
    """)
    
    db.execute_query("""
    CREATE CONSTRAINT IF NOT EXISTS FOR (dep:Department)
    ASSERT dep.name IS UNIQUE
    """)
    
    diseases = [
        {
            "name": "感冒",
            "description": "感冒是一种常见的急性上呼吸道病毒性感染性疾病，多由鼻病毒、副流感病毒、呼吸道合胞病毒等引起。",
            "symptoms": ["发热", "咳嗽", "流鼻涕", "鼻塞", "头痛"],
            "department": "呼吸内科",
            "is_rare": False,
            "source": "《内科学》第9版",
            "paragraphs": [
                {"section": "定义", "text": "感冒是一种常见的急性上呼吸道病毒性感染性疾病，多由鼻病毒、副流感病毒、呼吸道合胞病毒等引起。"},
                {"section": "症状", "text": "主要症状为鼻塞、流鼻涕、打喷嚏、咳嗽、咽痛、发热、头痛等，一般5-7天可痊愈。"},
                {"section": "治疗", "text": "以对症治疗为主，包括休息、多饮水、解热镇痛等。如有细菌感染可使用抗生素。"},
                {"section": "预防", "text": "增强体质、避免受凉、注意个人卫生是预防感冒的关键措施。"}
            ]
        },
        {
            "name": "高血压",
            "description": "高血压是指以体循环动脉血压增高为主要特征，可伴有心、脑、肾等器官的功能或器质性损害的临床综合征。",
            "symptoms": ["头晕", "头痛", "心悸", "胸闷"],
            "department": "心血管内科",
            "is_rare": False,
            "source": "《内科学》第9版",
            "paragraphs": [
                {"section": "定义", "text": "高血压是指以体循环动脉血压增高为主要特征（收缩压≥140mmHg和/或舒张压≥90mmHg），可伴有心、脑、肾等器官的功能或器质性损害的临床综合征。"},
                {"section": "症状", "text": "早期多无症状，常在体检时发现。常见症状有头晕、头痛、心悸、胸闷等。"},
                {"section": "治疗", "text": "包括生活方式干预和药物治疗。常用药物有钙通道阻滞剂、ACEI、ARB等。"},
                {"section": "预防", "text": "控制盐摄入、适量运动、戒烟限酒、保持心理平衡是预防高血压的重要措施。"}
            ]
        },
        {
            "name": "糖尿病",
            "description": "糖尿病是一组以高血糖为特征的代谢性疾病。高血糖则是由于胰岛素分泌缺陷或其生物作用受损，或两者兼有引起。",
            "symptoms": ["多饮", "多尿", "多食", "体重下降"],
            "department": "内分泌科",
            "is_rare": False,
            "source": "《内科学》第9版",
            "paragraphs": [
                {"section": "定义", "text": "糖尿病是一组以高血糖为特征的代谢性疾病。高血糖则是由于胰岛素分泌缺陷或其生物作用受损，或两者兼有引起。"},
                {"section": "症状", "text": "典型症状为多饮、多尿、多食和体重下降，即"三多一少"。"},
                {"section": "治疗", "text": "包括饮食控制、运动疗法、血糖监测、药物治疗和糖尿病教育。"},
                {"section": "预防", "text": "健康饮食、规律运动、保持正常体重、定期检查血糖。"}
            ]
        },
        {
            "name": "胃炎",
            "description": "胃炎是各种原因引起的胃黏膜炎症，为最常见的消化系统疾病之一。",
            "symptoms": ["上腹痛", "腹胀", "恶心", "呕吐", "食欲不振"],
            "department": "消化内科",
            "is_rare": False,
            "source": "《内科学》第9版",
            "paragraphs": [
                {"section": "定义", "text": "胃炎是各种原因引起的胃黏膜炎症，为最常见的消化系统疾病之一。"},
                {"section": "症状", "text": "上腹痛、腹胀、恶心、呕吐、食欲不振等。"},
                {"section": "治疗", "text": "消除病因、对症治疗，可使用质子泵抑制剂等药物。"},
                {"section": "预防", "text": "规律饮食、避免辛辣刺激食物、限酒、注意饮食卫生。"}
            ]
        },
        {
            "name": "肺炎",
            "description": "肺炎是指终末气道、肺泡和肺间质的炎症，可由疾病微生物、理化因素、免疫损伤、过敏及药物所致。",
            "symptoms": ["发热", "咳嗽", "咳痰", "呼吸困难", "胸痛"],
            "department": "呼吸内科",
            "is_rare": False,
            "source": "《内科学》第9版",
            "paragraphs": [
                {"section": "定义", "text": "肺炎是指终末气道、肺泡和肺间质的炎症，可由疾病微生物、理化因素、免疫损伤、过敏及药物所致。"},
                {"section": "症状", "text": "常见症状为发热、咳嗽、咳痰、呼吸困难、胸痛等。"},
                {"section": "治疗", "text": "抗感染治疗是肺炎治疗的关键环节，同时给予对症支持治疗。"},
                {"section": "预防", "text": "增强体质、避免受凉、戒烟、注意室内通风换气。"}
            ]
        },
        {
            "name": "肌萎缩侧索硬化症",
            "description": "肌萎缩侧索硬化症（ALS），俗称渐冻症，是一种累及上、下运动神经元的慢性进行性神经系统变性疾病。",
            "symptoms": ["肌束颤动", "吞咽困难", "构音障碍", "呼吸困难"],
            "department": "神经内科",
            "is_rare": True,
            "source": "《神经病学》第8版",
            "paragraphs": [
                {"section": "定义", "text": "肌萎缩侧索硬化症（ALS），俗称渐冻症，是一种累及上、下运动神经元的慢性进行性神经系统变性疾病。"},
                {"section": "流行病学", "text": "发病率约1.5-2.7/10万，患病率约4-6/10万，多为散发性，约5-10%为家族性。"},
                {"section": "症状", "text": "首发症状常为手指活动不灵、肌束颤动，逐渐发展为肌肉萎缩无力，可累及延髓出现吞咽困难、构音障碍，最终影响呼吸肌导致呼吸困难。"},
                {"section": "诊断", "text": "根据上、下运动神经元同时受累的证据，结合肌电图等辅助检查可确诊。需排除颈椎病、脊髓空洞症等疾病。"},
                {"section": "治疗", "text": "目前无特效治愈方法，利鲁唑可延缓疾病进展。主要采取对症支持治疗，包括呼吸支持、营养管理、康复训练等。"}
            ]
        },
        {
            "name": "系统性红斑狼疮",
            "description": "系统性红斑狼疮（SLE）是一种累及多系统、多器官的自身免疫性疾病，以产生多种自身抗体为特征。",
            "symptoms": ["皮疹", "关节痛", "光敏感", "口腔溃疡"],
            "department": "风湿免疫科",
            "is_rare": True,
            "source": "《内科学》第9版",
            "paragraphs": [
                {"section": "定义", "text": "系统性红斑狼疮（SLE）是一种累及多系统、多器官的自身免疫性疾病，以产生多种自身抗体为特征。"},
                {"section": "流行病学", "text": "好发于育龄女性，男女比例约1:9，发病率约30-70/10万。"},
                {"section": "症状", "text": "临床表现复杂多样，可出现蝶形红斑、关节痛、光敏感、口腔溃疡、脱发、肾脏损害等多系统受累表现。"},
                {"section": "诊断", "text": "根据2019年EULAR/ACR分类标准，结合抗核抗体、抗dsDNA抗体等自身抗体检测可确诊。"},
                {"section": "治疗", "text": "使用糖皮质激素联合免疫抑制剂（如羟氯喹、环磷酰胺、吗替麦考酚酯等）治疗，需长期随访管理。"}
            ]
        },
        {
            "name": "血友病",
            "description": "血友病是一组因遗传性凝血因子缺乏引起的出血性疾病，以关节、肌肉等出血为主要表现。",
            "symptoms": ["关节出血", "肌肉出血", "紫癜", "便血"],
            "department": "血液科",
            "is_rare": True,
            "source": "《血液病学》第2版",
            "paragraphs": [
                {"section": "定义", "text": "血友病是一组因遗传性凝血因子缺乏引起的出血性疾病，包括血友病A（因子VIII缺乏）和血友病B（因子IX缺乏）。"},
                {"section": "流行病学", "text": "血友病A发病率约1/5000男性，血友病B发病率约1/25000男性，为X连锁隐性遗传。"},
                {"section": "症状", "text": "主要表现为关节、肌肉等深部组织出血，反复关节出血可导致血友病性关节病，严重者可致残。"},
                {"section": "诊断", "text": "根据凝血因子活性测定确诊，因子VIII活性降低为血友病A，因子IX活性降低为血友病B。"},
                {"section": "治疗", "text": "替代治疗是主要手段，包括输注凝血因子浓缩制剂。预防性治疗可减少出血事件。"}
            ]
        },
        {
            "name": "帕金森病",
            "description": "帕金森病是一种常见的中老年神经系统变性疾病，以静止性震颤、肌强直、运动迟缓和姿势步态异常为主要特征。",
            "symptoms": ["震颤", "肌强直", "运动迟缓", "姿势不稳"],
            "department": "神经内科",
            "is_rare": True,
            "source": "《神经病学》第8版",
            "paragraphs": [
                {"section": "定义", "text": "帕金森病是一种常见的中老年神经系统变性疾病，以黑质多巴胺能神经元丢失和路易小体形成为病理特征。"},
                {"section": "症状", "text": "核心运动症状为静止性震颤、肌强直、运动迟缓和姿势步态异常。非运动症状包括嗅觉减退、便秘、抑郁、睡眠障碍等。"},
                {"section": "诊断", "text": "根据运动症状特点，结合左旋多巴治疗反应、嗅觉检查等辅助诊断。需排除继发性帕金森综合征。"},
                {"section": "治疗", "text": "药物治疗以左旋多巴为金标准，辅以多巴胺受体激动剂等。药物疗效减退时可考虑脑深部电刺激术。"}
            ]
        },
        {
            "name": "多发性硬化症",
            "description": "多发性硬化症是一种以中枢神经系统白质炎性脱髓鞘病变为特征的自身免疫性疾病。",
            "symptoms": ["视力下降", "肢体无力", "共济失调", "感觉异常"],
            "department": "神经内科",
            "is_rare": True,
            "source": "《神经病学》第8版",
            "paragraphs": [
                {"section": "定义", "text": "多发性硬化症是一种以中枢神经系统白质炎性脱髓鞘病变为特征的自身免疫性疾病，具有时间和空间多发性。"},
                {"section": "流行病学", "text": "好发于青壮年，女性多于男性，发病率随纬度增高而增加。"},
                {"section": "症状", "text": "临床表现多样，常见视力下降、肢体无力、感觉异常、共济失调、膀胱功能障碍等，可缓解复发。"},
                {"section": "诊断", "text": "根据临床发作次数、MRI显示的时间及空间多发脱髓鞘病灶，结合脑脊液寡克隆带检测。"},
                {"section": "治疗", "text": "急性期使用大剂量糖皮质激素，缓解期使用疾病修饰治疗（如干扰素β、特立氟胺等）。"}
            ]
        }
    ]
    
    symptoms_data = {
        "发热": ("体温升高，通常超过37.3°C", False),
        "咳嗽": ("呼吸道常见症状", False),
        "流鼻涕": ("鼻腔分泌物增多", False),
        "鼻塞": ("鼻腔通气不畅", False),
        "头痛": ("头部疼痛", False),
        "头晕": ("头部昏沉", False),
        "心悸": ("心跳加快或不规律", False),
        "胸闷": ("胸部闷胀感", False),
        "多饮": ("饮水量增加", False),
        "多尿": ("排尿次数增加", False),
        "多食": ("食欲增加", False),
        "体重下降": ("体重减轻", False),
        "上腹痛": ("上腹部疼痛", False),
        "腹胀": ("腹部胀满", False),
        "恶心": ("胃部不适，有呕吐感", False),
        "呕吐": ("胃内容物经口腔排出", False),
        "食欲不振": ("食欲减退", False),
        "咳痰": ("咳嗽时有痰", False),
        "呼吸困难": ("呼吸费力", False),
        "胸痛": ("胸部疼痛", False),
        "肌束颤动": ("肌肉出现不自主的细小快速收缩", True),
        "吞咽困难": ("吞咽食物时感觉困难或疼痛", True),
        "构音障碍": ("发音不清、言语含糊", True),
        "共济失调": ("运动协调障碍，动作不稳", True),
        "雷诺现象": ("受冷后指端颜色变白、发紫、潮红", True),
        "光敏感": ("对光线异常敏感", True),
        "口腔溃疡": ("口腔黏膜反复出现溃疡", True),
        "皮疹": ("皮肤出现异常皮损", False),
        "关节痛": ("关节部位疼痛", False),
        "紫癜": ("皮肤出现出血性紫斑", True),
        "震颤": ("身体某部位不自主的节律性抖动", True),
        "肌强直": ("肌肉持续紧张僵硬", True),
        "运动迟缓": ("动作变慢、起动困难", True),
        "视力下降": ("视力减退", True),
        "感觉异常": ("麻木、刺痛等异常感觉", True),
        "关节出血": ("关节腔内出血", True),
        "肌肉出血": ("肌肉组织内出血", True),
        "便血": ("大便中带血", True)
    }
    
    medicines = [
        {
            "name": "阿莫西林",
            "category": "抗生素",
            "usage": "口服，一次0.5g，一日3次",
            "description": "β-内酰胺类抗生素，用于敏感菌所致的感染",
            "is_rare": False
        },
        {
            "name": "布洛芬",
            "category": "解热镇痛药",
            "usage": "口服，一次0.2-0.4g，每6-8小时1次",
            "description": "非甾体抗炎药，用于缓解疼痛和发热",
            "is_rare": False
        },
        {
            "name": "二甲双胍",
            "category": "降糖药",
            "usage": "口服，一次0.5g，一日2-3次",
            "description": "双胍类降糖药，用于2型糖尿病",
            "is_rare": False
        },
        {
            "name": "奥美拉唑",
            "category": "质子泵抑制剂",
            "usage": "口服，一次20mg，一日1-2次",
            "description": "抑制胃酸分泌，用于胃酸过多相关疾病",
            "is_rare": False
        },
        {
            "name": "氨氯地平",
            "category": "钙通道阻滞剂",
            "usage": "口服，一次5mg，一日1次",
            "description": "用于高血压和心绞痛",
            "is_rare": False
        },
        {
            "name": "感冒灵颗粒",
            "category": "中成药",
            "usage": "开水冲服，一次1袋，一日3次",
            "description": "用于感冒引起的头痛、发热、鼻塞等症状",
            "is_rare": False
        },
        {
            "name": "利鲁唑",
            "category": "神经保护剂",
            "usage": "口服，一次50mg，一日2次",
            "description": "用于肌萎缩侧索硬化症，可延缓疾病进展",
            "is_rare": True
        },
        {
            "name": "羟氯喹",
            "category": "抗疟药/免疫调节剂",
            "usage": "口服，一次200mg，一日1-2次",
            "description": "用于系统性红斑狼疮等自身免疫性疾病的维持治疗",
            "is_rare": True
        },
        {
            "name": "环磷酰胺",
            "category": "免疫抑制剂",
            "usage": "静脉滴注，按体表面积计算剂量",
            "description": "用于系统性红斑狼疮重症患者的诱导缓解治疗",
            "is_rare": True
        },
        {
            "name": "左旋多巴",
            "category": "抗帕金森药",
            "usage": "口服，从小剂量开始，逐渐加量",
            "description": "帕金森病治疗的金标准药物，补充多巴胺",
            "is_rare": True
        },
        {
            "name": "凝血因子VIII浓缩制剂",
            "category": "血液制品",
            "usage": "静脉输注，按体重和出血程度计算剂量",
            "description": "用于血友病A患者的替代治疗和预防出血",
            "is_rare": True
        },
        {
            "name": "干扰素β",
            "category": "免疫调节剂",
            "usage": "皮下注射或肌肉注射，按方案执行",
            "description": "用于多发性硬化症的疾病修饰治疗",
            "is_rare": True
        }
    ]
    
    departments = [
        "呼吸内科", "心血管内科", "消化内科", "内分泌科",
        "神经内科", "风湿免疫科", "血液科"
    ]
    
    print("创建科室节点...")
    for dep in departments:
        db.execute_query(
            "MERGE (dep:Department {name: $name})",
            {"name": dep}
        )
    
    print("创建症状节点...")
    for name, (desc, is_rare) in symptoms_data.items():
        db.create_symptom(name, desc, is_rare=is_rare)
    
    print("创建疾病节点及关系...")
    for disease in diseases:
        db.create_disease(**disease)
        for sym in disease["symptoms"]:
            db.create_relation(disease["name"], "Disease", "HAS_SYMPTOM", sym, "Symptom")
        db.create_relation(disease["name"], "Disease", "BELONGS_TO", disease["department"], "Department")
    
    print("创建药物节点及关系...")
    for med in medicines:
        db.create_medicine(**med)
    
    treatment_relations = {
        "感冒": ["阿莫西林", "布洛芬", "感冒灵颗粒"],
        "肺炎": ["阿莫西林", "布洛芬"],
        "高血压": ["氨氯地平"],
        "糖尿病": ["二甲双胍"],
        "胃炎": ["奥美拉唑"],
        "肌萎缩侧索硬化症": ["利鲁唑"],
        "系统性红斑狼疮": ["羟氯喹", "环磷酰胺"],
        "帕金森病": ["左旋多巴"],
        "血友病": ["凝血因子VIII浓缩制剂"],
        "多发性硬化症": ["干扰素β"]
    }
    
    for disease, meds in treatment_relations.items():
        for med in meds:
            db.create_relation(disease, "Disease", "TREATED_BY", med, "Medicine")
    
    print("创建药品相互作用关系...")
    drug_interactions = [
        {
            "drug_a": "布洛芬", "drug_b": "氨氯地平",
            "severity": "major",
            "description": "布洛芬可减弱氨氯地平的降压效果，并增加肾损伤风险",
            "mechanism": "NSAIDs抑制前列腺素合成，导致血管收缩和水钠潴留",
            "recommendation": "不建议长期联用，如必须联用需密切监测血压和肾功能"
        },
        {
            "drug_a": "布洛芬", "drug_b": "二甲双胍",
            "severity": "moderate",
            "description": "布洛芬可能增加二甲双胍的乳酸酸中毒风险",
            "mechanism": "NSAIDs影响肾功能，可能减少二甲双胍排泄",
            "recommendation": "短期联用需监测肾功能，长期联用需谨慎"
        },
        {
            "drug_a": "奥美拉唑", "drug_b": "氨氯地平",
            "severity": "moderate",
            "description": "奥美拉唑可能增加氨氯地平的血药浓度",
            "mechanism": "奥美拉唑抑制CYP3A4，影响氨氯地平代谢",
            "recommendation": "联用时注意监测血压，可能需要调整氨氯地平剂量"
        },
        {
            "drug_a": "利鲁唑", "drug_b": "奥美拉唑",
            "severity": "major",
            "description": "奥美拉唑可能显著增加利鲁唑的血药浓度，增加肝毒性风险",
            "mechanism": "CYP1A2酶抑制，减少利鲁唑代谢",
            "recommendation": "应避免联用，如必须联用需大幅减少利鲁唑剂量并监测肝功能"
        },
        {
            "drug_a": "阿莫西林", "drug_b": "氨氯地平",
            "severity": "moderate",
            "description": "阿莫西林可能影响氨氯地平的代谢，增加低血压风险",
            "mechanism": "CYP3A4酶竞争性抑制",
            "recommendation": "联合使用时需监测血压"
        },
        {
            "drug_a": "左旋多巴", "drug_b": "布洛芬",
            "severity": "moderate",
            "description": "布洛芬可能增加左旋多巴的血药浓度",
            "mechanism": "NSAIDs影响肾功能从而减少左旋多巴排泄",
            "recommendation": "联用时注意观察左旋多巴的不良反应"
        },
        {
            "drug_a": "阿司匹林", "drug_b": "布洛芬",
            "severity": "major",
            "description": "布洛芬可削弱阿司匹林的心血管保护作用，并增加胃肠道出血风险",
            "mechanism": "竞争性结合COX-1，阻止阿司匹林不可逆抑制血小板",
            "recommendation": "不建议联用，如需镇痛可选用对乙酰氨基酚替代"
        }
    ]
    
    for inter in drug_interactions:
        db.create_interaction_relation(
            inter["drug_a"], inter["drug_b"],
            inter["severity"], inter["description"],
            inter["mechanism"], inter["recommendation"]
        )
    
    print("标记紧急症状...")
    emergency_symptoms = [
        "呼吸困难", "胸痛", "胸闷", "意识障碍", "昏迷",
        "大出血", "呕血", "抽搐", "紫癜"
    ]
    for sym_name in emergency_symptoms:
        db.execute_query(
            "MATCH (s:Symptom {name: $name}) SET s.is_emergency = true",
            {"name": sym_name}
        )
    
    print("知识图谱初始化完成！")
    print(f"共创建 {len(diseases)} 种疾病（含 {sum(1 for d in diseases if d.get('is_rare'))} 种罕见病）")
    print(f"共创建 {len(symptoms_data)} 种症状")
    print(f"共创建 {len(medicines)} 种药物")
    print(f"共创建 {len(drug_interactions)} 条药品相互作用")
    print(f"共标记 {len(emergency_symptoms)} 个紧急症状")
    db.close()

if __name__ == "__main__":
    init_medical_knowledge()
