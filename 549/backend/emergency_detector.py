import sys
import os
from typing import Dict, List, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class EmergencyDetector:
    def __init__(self):
        self.critical_symptoms = self._load_critical_symptoms()
        self.emergency_keywords = self._load_emergency_keywords()

    def _load_critical_symptoms(self) -> List[Dict]:
        return [
            {
                "symptoms": ["呼吸困难", "呼吸急促", "窒息", "喘息"],
                "condition": "急性呼吸窘迫",
                "level": "CRITICAL",
                "action": "立即拨打120急救电话！保持患者半坐位，解开衣领。",
                "departments": ["急诊科", "呼吸内科"],
                "possible_causes": ["哮喘急性发作", "肺栓塞", "心力衰竭", "气胸", "严重肺炎"]
            },
            {
                "symptoms": ["胸痛", "胸闷", "心悸", "大汗淋漓"],
                "condition": "疑似急性心血管事件",
                "level": "CRITICAL",
                "action": "立即拨打120急救电话！让患者平卧或半坐位，不要活动，如备有硝酸甘油可舌下含服。",
                "departments": ["急诊科", "心血管内科"],
                "possible_causes": ["急性心肌梗死", "心绞痛", "主动脉夹层", "肺栓塞"]
            },
            {
                "symptoms": ["意识障碍", "昏迷", "意识模糊", "嗜睡"],
                "condition": "意识障碍",
                "level": "CRITICAL",
                "action": "立即拨打120急救电话！将患者侧卧防止误吸，检查呼吸和脉搏。",
                "departments": ["急诊科", "神经内科"],
                "possible_causes": ["脑卒中", "低血糖", "糖尿病酮症酸中毒", "药物中毒"]
            },
            {
                "symptoms": ["剧烈头痛", "呕吐", "颈部僵硬"],
                "condition": "疑似颅内出血/脑膜炎",
                "level": "CRITICAL",
                "action": "立即拨打120急救电话！保持患者安静，头部稍垫高。",
                "departments": ["急诊科", "神经内科"],
                "possible_causes": ["蛛网膜下腔出血", "脑出血", "脑膜炎"]
            },
            {
                "symptoms": ["大出血", "呕血", "便血", "大量咯血"],
                "condition": "急性出血",
                "level": "CRITICAL",
                "action": "立即拨打120急救电话！保持安静，呕血时侧卧防止窒息，不要进食饮水。",
                "departments": ["急诊科"],
                "possible_causes": ["消化道大出血", "肺部大出血", "外伤出血"]
            },
            {
                "symptoms": ["高热", "抽搐", "惊厥"],
                "condition": "高热惊厥/严重感染",
                "level": "HIGH",
                "action": "立即拨打120或前往急诊！保持患者侧卧，防止咬伤舌头，物理降温。",
                "departments": ["急诊科", "感染科"],
                "possible_causes": ["严重感染", "高热惊厥", "癫痫发作", "脑炎"]
            },
            {
                "symptoms": ["剧烈腹痛", "腹部压痛", "腹肌紧张"],
                "condition": "疑似急腹症",
                "level": "HIGH",
                "action": "立即就医！禁食禁水，不要服用止痛药（可能掩盖病情）。",
                "departments": ["急诊科", "普外科"],
                "possible_causes": ["急性阑尾炎", "胃穿孔", "肠梗阻", "宫外孕破裂"]
            },
            {
                "symptoms": ["过敏反应", "喉头水肿", "全身皮疹", "血压骤降"],
                "condition": "严重过敏反应",
                "level": "CRITICAL",
                "action": "立即拨打120急救电话！如备有肾上腺素自动注射器请立即使用。远离过敏原。",
                "departments": ["急诊科"],
                "possible_causes": ["药物过敏", "食物过敏", "昆虫叮咬过敏"]
            },
            {
                "symptoms": ["偏瘫", "言语不清", "口角歪斜", "肢体麻木"],
                "condition": "疑似脑卒中",
                "level": "CRITICAL",
                "action": "立即拨打120急救电话！记住发病时间（溶栓黄金4.5小时），让患者平卧，头偏向一侧。",
                "departments": ["急诊科", "神经内科"],
                "possible_causes": ["缺血性脑卒中", "出血性脑卒中", "短暂性脑缺血发作"]
            },
            {
                "symptoms": ["紫癜", "广泛出血", "牙龈出血", "鼻衄"],
                "condition": "凝血功能异常",
                "level": "HIGH",
                "action": "尽快就医！避免磕碰，不要用力擤鼻或刷牙，注意观察出血情况。",
                "departments": ["急诊科", "血液科"],
                "possible_causes": ["血小板减少症", "血友病出血", "弥散性血管内凝血"]
            }
        ]

    def _load_emergency_keywords(self) -> Dict:
        return {
            "CRITICAL": ["不能呼吸", "窒息", "昏迷", "心脏骤停", "大出血", "意识丧失",
                         "剧烈胸痛", "突然说不出话", "半身不能动", "口角歪斜"],
            "HIGH": ["高烧不退", "剧烈腹痛", "大量呕血", "严重过敏", "抽搐", "持续呕吐",
                     "突然视力丧失", "剧烈头痛", "全身出血点"],
            "MODERATE": ["持续发热", "反复呕吐", "严重腹泻", "明显消瘦", "持续疼痛"]
        }

    def detect_emergency(self, question: str, entities: List[Dict] = None) -> Dict[str, Any]:
        detected = []
        matched_keywords = []
        
        for emergency in self.critical_symptoms:
            matched = []
            for symptom in emergency["symptoms"]:
                if symptom in question:
                    matched.append(symptom)
                    matched_keywords.append(symptom)
            
            if entities:
                for entity in entities:
                    entity_text = entity.get("text", "")
                    if entity_text in emergency["symptoms"] and entity_text not in matched:
                        matched.append(entity_text)
                        matched_keywords.append(entity_text)
            
            if matched:
                detected.append({
                    "condition": emergency["condition"],
                    "level": emergency["level"],
                    "matched_symptoms": matched,
                    "action": emergency["action"],
                    "departments": emergency["departments"],
                    "possible_causes": emergency["possible_causes"]
                })
        
        for level, keywords in self.emergency_keywords.items():
            for keyword in keywords:
                if keyword in question and keyword not in matched_keywords:
                    detected.append({
                        "condition": f"用户描述: {keyword}",
                        "level": level,
                        "matched_symptoms": [keyword],
                        "action": self._get_default_action(level),
                        "departments": ["急诊科"],
                        "possible_causes": ["需医生进一步评估"]
                    })
                    break
        
        if not detected:
            return {
                "is_emergency": False,
                "level": "NONE",
                "alerts": [],
                "emergency_advice": None
            }
        
        highest = max(detected, key=lambda x: {"CRITICAL": 3, "HIGH": 2, "MODERATE": 1}.get(x["level"], 0))
        
        return {
            "is_emergency": True,
            "level": highest["level"],
            "alerts": detected,
            "emergency_advice": self._build_emergency_advice(highest, detected)
        }

    def _get_default_action(self, level: str) -> str:
        actions = {
            "CRITICAL": "立即拨打120急救电话！请勿延误！",
            "HIGH": "请尽快前往最近的医院急诊科就诊！",
            "MODERATE": "建议尽早到医院就诊，如症状加重请立即就医。"
        }
        return actions.get(level, "如有不适请及时就医。")

    def _build_emergency_advice(self, highest: Dict, all_alerts: List[Dict]) -> str:
        level_display = {"CRITICAL": "🚨 危急", "HIGH": "⚠️ 紧急", "MODERATE": "⚠ 注意"}
        level_text = level_display.get(highest["level"], "⚠ 注意")
        
        advice = f"{level_text} 检测到疑似危急症状！\n\n"
        advice += f"疑似情况：{highest['condition']}\n"
        advice += f"匹配症状：{', '.join(highest['matched_symptoms'])}\n\n"
        advice += f"🆘 紧急处置：{highest['action']}\n\n"
        advice += f"🏥 建议就诊科室：{', '.join(highest['departments'])}\n\n"
        advice += f"可能原因：{', '.join(highest['possible_causes'])}\n\n"
        
        if len(all_alerts) > 1:
            advice += "其他疑似情况：\n"
            for alert in all_alerts[1:]:
                advice += f"  - {alert['condition']}（{alert['level']}）\n"
            advice += "\n"
        
        if highest["level"] == "CRITICAL":
            advice += "🚨 请立即拨打120急救电话，不要等待！时间就是生命！\n"
            advice += "如身边有人，请让他人帮忙拨打120。"
        elif highest["level"] == "HIGH":
            advice += "请尽快前往最近的医院急诊科，不要自行驾车，可请他人送医或拨打120。"
        
        return advice
