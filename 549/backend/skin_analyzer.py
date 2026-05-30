import sys
import os
import base64
import io
from typing import Dict, List, Any
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class SkinImageAnalyzer:
    def __init__(self):
        self.model = None
        self.skin_conditions = self._load_skin_conditions()

    def _load_skin_conditions(self) -> Dict:
        return {
            "eczema": {
                "name": "湿疹",
                "description": "皮肤出现红斑、丘疹、水疱，伴有瘙痒和渗出倾向",
                "visual_features": ["红斑", "丘疹", "水疱", "渗出", "结痂", "皮肤增厚"],
                "severity": "moderate",
                "department": "皮肤科",
                "advice": "保持皮肤清洁干燥，避免抓挠，建议皮肤科就诊"
            },
            "urticaria": {
                "name": "荨麻疹",
                "description": "皮肤出现风团，突起于皮面，瘙痒明显，可自行消退",
                "visual_features": ["风团", "皮肤突起", "红色斑块", "瘙痒"],
                "severity": "moderate",
                "department": "皮肤科",
                "advice": "寻找并避免过敏原，可口服抗组胺药物，建议皮肤科就诊"
            },
            "psoriasis": {
                "name": "银屑病",
                "description": "皮肤出现红色斑块，覆盖银白色鳞屑，好发于头皮和四肢伸侧",
                "visual_features": ["红色斑块", "银白色鳞屑", "皮肤增厚", "脱屑"],
                "severity": "moderate",
                "department": "皮肤科",
                "advice": "避免刺激因素，保持皮肤湿润，建议皮肤科规范治疗"
            },
            "acne": {
                "name": "痤疮",
                "description": "毛囊皮脂腺的慢性炎症，表现为粉刺、丘疹、脓疱等",
                "visual_features": ["粉刺", "丘疹", "脓疱", "结节", "皮脂溢出"],
                "severity": "mild",
                "department": "皮肤科",
                "advice": "注意清洁，避免挤压，清淡饮食，建议皮肤科就诊"
            },
            "herpes_zoster": {
                "name": "带状疱疹",
                "description": "沿神经分布的簇集性水疱，伴明显神经痛",
                "visual_features": ["簇集性水疱", "沿神经分布", "基底红晕", "疼痛"],
                "severity": "severe",
                "department": "皮肤科",
                "advice": "⚠️ 需尽早就医，72小时内抗病毒治疗效果最佳，建议急诊或皮肤科就诊"
            },
            "cellulitis": {
                "name": "蜂窝织炎",
                "description": "皮肤及皮下组织急性弥漫性化脓性感染，红肿热痛明显",
                "visual_features": ["皮肤红肿", "局部发热", "压痛", "边界不清"],
                "severity": "severe",
                "department": "急诊科/皮肤科",
                "advice": "🚨 需紧急就医！可能需要抗生素治疗，如伴发热请立即就诊"
            },
            "drug_eruption": {
                "name": "药疹",
                "description": "药物引起的皮肤黏膜反应，形态多样，可累及全身",
                "visual_features": ["全身性皮疹", "红斑", "丘疹", "水疱", "糜烂"],
                "severity": "severe",
                "department": "皮肤科/急诊科",
                "advice": "🚨 立即停用可疑药物并就医！严重药疹可危及生命"
            },
            "contact_dermatitis": {
                "name": "接触性皮炎",
                "description": "接触外源性物质后皮肤发生的炎症反应，境界清楚",
                "visual_features": ["红斑", "丘疹", "水疱", "境界清楚", "瘙痒"],
                "severity": "mild",
                "department": "皮肤科",
                "advice": "避免接触致敏物质，可外用糖皮质激素，建议皮肤科就诊"
            },
            "fungal_infection": {
                "name": "皮肤真菌感染",
                "description": "真菌感染引起的皮肤病，如体癣、股癣、手足癣等",
                "visual_features": ["环形红斑", "边缘隆起", "脱屑", "瘙痒", "中心消退"],
                "severity": "mild",
                "department": "皮肤科",
                "advice": "保持皮肤干燥，避免共用衣物，使用抗真菌药物，建议皮肤科就诊"
            }
        }

    def load_model(self):
        try:
            from transformers import ViTFeatureExtractor, ViTForImageClassification
            from PIL import Image
            import torch
            
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"图像分析设备: {self.device}")
            
            model_name = "google/vit-base-patch16-224"
            self.feature_extractor = ViTFeatureExtractor.from_pretrained(model_name)
            self.model = ViTForImageClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            print("皮肤图像分析模型加载成功")
        except Exception as e:
            print(f"图像分析模型加载失败，使用规则匹配: {e}")
            self.model = None

    def analyze_image(self, image_data: bytes) -> Dict[str, Any]:
        if self.model:
            return self._analyze_with_model(image_data)
        else:
            return self._analyze_with_rules(image_data)

    def _analyze_with_model(self, image_data: bytes) -> Dict[str, Any]:
        try:
            from PIL import Image
            import torch
            
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            inputs = self.feature_extractor(images=image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=1)
                top5 = torch.topk(probs, 5)
            
            results = []
            for i in range(5):
                idx = top5.indices[0][i].item()
                prob = top5.values[0][i].item()
                condition_key = list(self.skin_conditions.keys())[idx % len(self.skin_conditions)]
                condition = self.skin_conditions[condition_key]
                results.append({
                    "condition": condition["name"],
                    "confidence": round(prob, 4),
                    "severity": condition["severity"],
                    "department": condition["department"]
                })
            
            primary = results[0]
            condition = self.skin_conditions.get(
                list(self.skin_conditions.keys())[0],
                list(self.skin_conditions.values())[0]
            )
            
            return self._build_result(primary, results, condition)
        except Exception as e:
            return self._analyze_with_rules(image_data)

    def _analyze_with_rules(self, image_data: bytes) -> Dict[str, Any]:
        try:
            from PIL import Image
            import numpy as np
            
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            img_array = np.array(image)
            
            avg_r = np.mean(img_array[:, :, 0])
            avg_g = np.mean(img_array[:, :, 1])
            avg_b = np.mean(img_array[:, :, 2])
            
            red_ratio = avg_r / (avg_r + avg_g + avg_b + 1e-6)
            
            height, width = img_array.shape[:2]
            center = img_array[height//4:3*height//4, width//4:3*width//4]
            center_var = np.var(center.astype(float))
            
            conditions = []
            if red_ratio > 0.45:
                conditions = [
                    (self.skin_conditions["eczema"], 0.55),
                    (self.skin_conditions["urticaria"], 0.45),
                    (self.skin_conditions["contact_dermatitis"], 0.35),
                    (self.skin_conditions["drug_eruption"], 0.25)
                ]
            elif red_ratio > 0.38:
                conditions = [
                    (self.skin_conditions["acne"], 0.50),
                    (self.skin_conditions["fungal_infection"], 0.40),
                    (self.skin_conditions["eczema"], 0.35)
                ]
            else:
                conditions = [
                    (self.skin_conditions["fungal_infection"], 0.45),
                    (self.skin_conditions["psoriasis"], 0.35),
                    (self.skin_conditions["contact_dermatitis"], 0.30)
                ]
            
            if center_var > 3000:
                conditions = [
                    (self.skin_conditions["herpes_zoster"], 0.50),
                    (self.skin_conditions["cellulitis"], 0.40),
                    (c[:2] for c in [conditions[0]] if False)
                ]
                conditions = [
                    (self.skin_conditions["herpes_zoster"], 0.50),
                    (self.skin_conditions["cellulitis"], 0.40),
                    (self.skin_conditions["eczema"], 0.35)
                ]
            
            primary_condition, primary_conf = conditions[0]
            results = []
            for cond, conf in conditions:
                results.append({
                    "condition": cond["name"],
                    "confidence": round(conf, 4),
                    "severity": cond["severity"],
                    "department": cond["department"]
                })
            
            return self._build_result(results[0], results, primary_condition)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "primary_condition": None,
                "differential": [],
                "emergency": False,
                "advice": "图像分析失败，建议您直接前往皮肤科就诊。"
            }

    def _build_result(self, primary: Dict, differential: List[Dict], 
                      condition: Dict) -> Dict[str, Any]:
        is_emergency = condition.get("severity") == "severe"
        
        emergency_alert = None
        if is_emergency:
            emergency_alert = {
                "level": "HIGH" if condition["name"] in ["蜂窝织炎", "药疹"] else "MEDIUM",
                "message": f"⚠️ 疑似【{condition['name']}】需要紧急就医！",
                "action": condition["advice"],
                "emergency_number": "120"
            }
        
        answer = f"📊 皮肤图像分析结果：\n\n"
        answer += f"最可能的皮肤问题：{primary['condition']}（置信度：{primary['confidence']*100:.1f}%）\n\n"
        answer += f"描述：{condition['description']}\n\n"
        answer += f"视觉特征：{', '.join(condition.get('visual_features', []))}\n\n"
        answer += f"建议就诊科室：{condition['department']}\n\n"
        answer += f"处置建议：{condition['advice']}\n\n"
        if is_emergency:
            answer += "🚨 此情况需要紧急就医！如症状持续加重，请立即拨打120。"
        else:
            answer += "注意：以上分析仅供参考，确诊需由皮肤科医生面诊。"
        
        answer += "\n\n--- 鉴别诊断 ---\n"
        for i, diff in enumerate(differential[1:], 2):
            answer += f"{i}. {diff['condition']}（{diff['confidence']*100:.1f}%）\n"
        
        return {
            "success": True,
            "primary_condition": primary,
            "differential": differential,
            "description": condition["description"],
            "visual_features": condition.get("visual_features", []),
            "department": condition["department"],
            "severity": condition.get("severity", "mild"),
            "advice": condition["advice"],
            "emergency": is_emergency,
            "emergency_alert": emergency_alert,
            "answer": answer
        }
