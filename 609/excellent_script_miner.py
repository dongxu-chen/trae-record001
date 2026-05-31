from typing import List, Dict, Any
import numpy as np


class ExcellentScriptMiner:
    def __init__(self):
        self.categories = {
            "greeting": ["您好", "你好", "欢迎", "很高兴为您服务", "请问有什么可以帮您"],
            "empathy": ["理解", "明白", "我了解", "确实", "您的心情我理解", "感同身受"],
            "apology": ["抱歉", "对不起", "不好意思", "给您带来不便", "请您谅解"],
            "solution": ["帮您", "为您", "可以", "建议", "推荐", "解决", "处理"],
            "polite_close": ["不客气", "应该的", "祝您", "欢迎再来", "感谢您的咨询"]
        }
        
        self.high_score_threshold = 85

    def mine_excellent_scripts(self, conversation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        high_score_conversations = [
            r for r in conversation_results 
            if r["comprehensive_score"] >= self.high_score_threshold
        ]
        
        if not high_score_conversations:
            return {
                "total_high_score": 0,
                "categories": {},
                "recommended_scripts": [],
                "analysis": "暂无足够的高评分对话数据"
            }
        
        category_scripts = {}
        all_service_messages = []
        
        for result in high_score_conversations:
            conversation = self._find_conversation_by_id(result["conversation_id"])
            if conversation:
                service_msgs = [
                    m for m in conversation.get("messages", []) 
                    if m.get("role") == "service"
                ]
                all_service_messages.extend(service_msgs)
        
        for category, keywords in self.categories.items():
            category_scripts[category] = self._extract_scripts_by_category(
                all_service_messages, keywords
            )
        
        recommended_scripts = self._generate_recommendations(category_scripts)
        
        return {
            "total_high_score": len(high_score_conversations),
            "high_score_ratio": round(len(high_score_conversations) / len(conversation_results) * 100, 2),
            "categories": category_scripts,
            "recommended_scripts": recommended_scripts,
            "analysis": self._generate_analysis(category_scripts)
        }

    def _find_conversation_by_id(self, conv_id: str) -> Dict[str, Any]:
        from sample_data import sample_conversations
        for conv in sample_conversations:
            if conv.get("id") == conv_id:
                return conv
        return None

    def _extract_scripts_by_category(self, messages: List[Dict[str, Any]], 
                                       keywords: List[str]) -> List[Dict[str, Any]]:
        matched_scripts = []
        
        for msg in messages:
            text = msg.get("content", "")
            matched_keywords = [k for k in keywords if k in text]
            
            if matched_keywords and len(text) >= 5:
                quality_score = self._score_script_quality(text)
                
                matched_scripts.append({
                    "text": text,
                    "matched_keywords": matched_keywords,
                    "quality_score": quality_score,
                    "length": len(text)
                })
        
        matched_scripts.sort(key=lambda x: x["quality_score"], reverse=True)
        return matched_scripts[:10]

    def _score_script_quality(self, text: str) -> float:
        score = 50.0
        
        polite_words = ["您好", "请", "谢谢", "感谢", "抱歉", "您"]
        for word in polite_words:
            if word in text:
                score += 8
        
        if len(text) >= 10 and len(text) <= 80:
            score += 15
        elif len(text) > 80 and len(text) <= 150:
            score += 10
        
        if text.endswith("。") or text.endswith("！") or text.endswith("？"):
            score += 5
        
        positive_patterns = ["帮您", "为您", "可以", "没问题"]
        for pattern in positive_patterns:
            if pattern in text:
                score += 5
        
        return min(100, score)

    def _generate_recommendations(self, category_scripts: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        recommendations = []
        
        category_names = {
            "greeting": "开场问候",
            "empathy": "共情表达",
            "apology": "道歉安抚",
            "solution": "解决方案",
            "polite_close": "礼貌收尾"
        }
        
        for category, scripts in category_scripts.items():
            if scripts:
                top_scripts = [s["text"] for s in scripts[:3]]
                recommendations.append({
                    "category": category_names.get(category, category),
                    "category_key": category,
                    "example_count": len(scripts),
                    "top_scripts": top_scripts,
                    "best_practice": self._get_best_practice(category)
                })
        
        return recommendations

    def _get_best_practice(self, category: str) -> str:
        practices = {
            "greeting": "在客户进线30秒内主动问候，使用礼貌用语，询问需求",
            "empathy": "先表达理解和共情，再提供解决方案，让客户感受到被重视",
            "apology": "真诚道歉，不推诿责任，明确告知后续处理方案",
            "solution": "提供2-3个可选方案，说明优缺点，帮助客户决策",
            "polite_close": "确认客户无其他问题，送上祝福，欢迎再次咨询"
        }
        return practices.get(category, "持续优化服务话术，提升客户体验")

    def _generate_analysis(self, category_scripts: Dict[str, List[Dict[str, Any]]]) -> str:
        strong_categories = []
        weak_categories = []
        
        for category, scripts in category_scripts.items():
            if len(scripts) >= 3:
                strong_categories.append(category)
            elif len(scripts) == 0:
                weak_categories.append(category)
        
        analysis_parts = []
        
        if strong_categories:
            analysis_parts.append(f"优秀话术较多的场景：{', '.join(strong_categories)}")
        
        if weak_categories:
            analysis_parts.append(f"需要加强的场景：{', '.join(weak_categories)}")
        
        if not analysis_parts:
            analysis_parts.append("各场景话术分布较为均衡，建议持续积累优质案例")
        
        return "；".join(analysis_parts)

    def get_script_for_scenario(self, scenario: str) -> List[str]:
        scenario_map = {
            "complaint": [
                "非常抱歉给您带来不好的体验，我马上为您处理这个问题。",
                "您的心情我完全理解，换成是我也会很生气，我们一定帮您解决。",
                "感谢您的反馈，这对我们非常重要，我们会立即改进。"
            ],
            "refund": [
                "关于退款申请，我来帮您查询一下具体流程，请稍等。",
                "您的退款申请已经受理，预计3-5个工作日内到账。",
                "为了尽快完成退款，请您提供一下相关信息。"
            ],
            "technical": [
                "这个问题我来帮您排查，可能有以下几种原因...",
                "建议您先尝试重启设备，如果问题依然存在，我们安排技术人员联系您。",
                "您描述的现象我已经记录，我来给您提供具体的解决方案。"
            ],
            "general": [
                "您好，很高兴为您服务，请问有什么可以帮您的？",
                "好的，我来为您详细说明一下。",
                "不客气，这是我们应该做的，祝您生活愉快！"
            ]
        }
        return scenario_map.get(scenario, scenario_map["general"])

    def compare_agent_scripts(self, agent_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        agent_script_quality = {}
        
        for agent_id, results in agent_results.items():
            total_score = 0
            script_count = 0
            
            for result in results:
                conv = self._find_conversation_by_id(result["conversation_id"])
                if conv:
                    service_msgs = [
                        m for m in conv.get("messages", []) 
                        if m.get("role") == "service"
                    ]
                    for msg in service_msgs:
                        total_score += self._score_script_quality(msg.get("content", ""))
                        script_count += 1
            
            avg_score = round(total_score / script_count, 2) if script_count > 0 else 0
            agent_script_quality[agent_id] = {
                "avg_script_quality": avg_score,
                "script_count": script_count,
                "level": "优秀" if avg_score >= 80 else "良好" if avg_score >= 70 else "待提升"
            }
        
        sorted_agents = sorted(
            agent_script_quality.items(),
            key=lambda x: x[1]["avg_script_quality"],
            reverse=True
        )
        
        return {
            "agent_ranking": sorted_agents,
            "avg_team_score": round(np.mean([v["avg_script_quality"] for v in agent_script_quality.values()]), 2)
        }
