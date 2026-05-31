from typing import List, Dict, Any
import pandas as pd
from collections import defaultdict


class PersonalizedTrainingRecommender:
    def __init__(self):
        self.training_modules = {
            "response_speed": {
                "name": "响应速度提升",
                "weakness_indicators": ["响应速度", "平均响应时间", "slow_responses"],
                "level1": {
                    "title": "基础响应技巧专项训练",
                    "target_weakness": "响应不及时",
                    "content": [
                        "【专项训练1】消息提醒机制设置与快速反应练习",
                        "【专项训练2】20条高频问题快捷回复模板背诵与应用",
                        "【专项训练3】打字速度强化训练（目标60字/分钟）",
                        "【专项训练4】快速抓重点技巧——客户问题关键词识别"
                    ],
                    "duration": "3小时",
                    "priority": "high",
                    "practice_exercises": [
                        "每日10分钟快速反应练习（模拟客户消息，计时回复）",
                        "整理并熟记30条常用快捷回复",
                        "打字练习软件每日训练30分钟"
                    ],
                    "expected_improvement": "+15分"
                },
                "level2": {
                    "title": "多任务高效处理专项",
                    "target_weakness": "多会话处理能力不足",
                    "content": [
                        "【专项训练1】多会话并行处理优先级判断方法",
                        "【专项训练2】复杂问题快速拆解与预估回复时间",
                        "【专项训练3】高峰期时间管理与压力应对",
                        "【专项训练4】预估等待时间的话术技巧"
                    ],
                    "duration": "4小时",
                    "priority": "medium",
                    "practice_exercises": [
                        "模拟3个客户同时咨询的场景练习",
                        "学习使用便签记录待处理事项"
                    ],
                    "expected_improvement": "+10分"
                }
            },
            "customer_satisfaction": {
                "name": "用户满意度提升",
                "weakness_indicators": ["用户满意度", "满意度", "satisfaction", "very_dissatisfied", "dissatisfied"],
                "level1": {
                    "title": "客户需求精准把握专项",
                    "target_weakness": "未能准确理解客户需求",
                    "content": [
                        "【专项训练1】有效提问技巧——5W1H问话法",
                        "【专项训练2】倾听与确认技巧——避免理解偏差",
                        "【专项训练3】客户隐含需求识别能力训练",
                        "【专项训练4】期望值管理与合理承诺"
                    ],
                    "duration": "4小时",
                    "priority": "high",
                    "practice_exercises": [
                        "每日记录3个客户需求点，分析匹配度",
                        "练习复述客户问题确保理解一致"
                    ],
                    "expected_improvement": "+12分"
                },
                "level2": {
                    "title": "超出期望服务技巧专项",
                    "target_weakness": "服务不够贴心",
                    "content": [
                        "【专项训练1】个性化服务策略设计",
                        "【专项训练2】主动提供增值信息技巧",
                        "【专项训练3】预判客户潜在问题",
                        "【专项训练4】问题预防建议提供方法"
                    ],
                    "duration": "3小时",
                    "priority": "medium",
                    "practice_exercises": [
                        "每通对话后思考：还能为客户提供什么？",
                        "收集整理5个超出期望的服务案例"
                    ],
                    "expected_improvement": "+8分"
                }
            },
            "service_emotion": {
                "name": "客服情绪管理与归因",
                "weakness_indicators": ["客服情绪归因", "情绪", "emotion", "不礼貌", "负面情绪"],
                "level1": {
                    "title": "情绪自控与专业形象维持专项",
                    "target_weakness": "容易受客户情绪影响",
                    "content": [
                        "【专项训练1】情绪觉察——识别自己的情绪触发点",
                        "【专项训练2】深呼吸法——3秒冷静技巧",
                        "【专项训练3】认知重构——把客户不满看作问题而非针对个人",
                        "【专项训练4】标准化话术——情绪激动时的安全表达"
                    ],
                    "duration": "4小时",
                    "priority": "high",
                    "practice_exercises": [
                        "记录每日情绪触发事件与应对方式",
                        "背诵10句情绪激动时的安全话术",
                        "模拟高难度客户对话的情绪应对练习"
                    ],
                    "expected_improvement": "+15分"
                },
                "level2": {
                    "title": "客户情绪安抚专项",
                    "target_weakness": "不会安抚情绪激动的客户",
                    "content": [
                        "【专项训练1】共情表达——让客户感受到被理解",
                        "【专项训练2】降低语速与语调控制技巧",
                        "【专项训练3】致歉与承担责任的艺术",
                        "【专项训练4】提供解决方案前先处理情绪"
                    ],
                    "duration": "5小时",
                    "priority": "high",
                    "practice_exercises": [
                        "整理5个共情表达模板并反复练习",
                        "观看优秀客服处理抱怨案例视频"
                    ],
                    "expected_improvement": "+12分"
                },
                "level3": {
                    "title": "服务礼仪标准化专项",
                    "target_weakness": "服务用语不规范",
                    "content": [
                        "【专项训练1】礼貌用语标准化——七声服务",
                        "【专项训练2】称呼与表达方式训练",
                        "【专项训练3】避免否定表达的转换技巧",
                        "【专项训练4】热情度保持——语气语调活力训练"
                    ],
                    "duration": "3小时",
                    "priority": "medium",
                    "practice_exercises": [
                        "每日晨读标准服务话术10分钟",
                        "录音自检服务用语规范度"
                    ],
                    "expected_improvement": "+10分"
                }
            },
            "problem_solving": {
                "name": "问题解决能力",
                "weakness_indicators": ["问题解决", "解决", "resolution"],
                "level1": {
                    "title": "产品知识与问题排查专项",
                    "target_weakness": "产品知识不扎实",
                    "content": [
                        "【专项训练1】核心产品功能思维导图梳理",
                        "【专项训练2】常见问题知识库快速检索",
                        "【专项训练3】问题分级——哪些能立即回答，哪些需要查询",
                        "【专项训练4】不知道答案时的专业回应方式"
                    ],
                    "duration": "5小时",
                    "priority": "high",
                    "practice_exercises": [
                        "每日学习并测试3个产品知识点",
                        "整理10个最常被问到的问题及标准答案"
                    ],
                    "expected_improvement": "+12分"
                },
                "level2": {
                    "title": "升级处理与闭环管理专项",
                    "target_weakness": "升级处理不规范",
                    "content": [
                        "【专项训练1】何时应该升级——判断标准",
                        "【专项训练2】升级前的信息收集清单",
                        "【专项训练3】客户期望值管理——升级后多久答复",
                        "【专项训练4】问题追踪与闭环反馈技巧"
                    ],
                    "duration": "3小时",
                    "priority": "medium",
                    "practice_exercises": [
                        "整理升级处理checklist",
                        "模拟3个需要升级的场景练习"
                    ],
                    "expected_improvement": "+8分"
                }
            }
        }

        self.improvement_templates = {
            "response_speed": [
                {"action": "设置消息弹窗+声音双重提醒", "timeline": "立即", "check_point": "测试消息提醒是否及时"},
                {"action": "整理30条高频问题快捷回复", "timeline": "3天内", "check_point": "快捷回复覆盖率达80%"},
                {"action": "每日打字训练30分钟", "timeline": "持续2周", "check_point": "打字速度达60字/分钟"}
            ],
            "customer_satisfaction": [
                {"action": "每通对话后确认客户需求是否满足", "timeline": "立即", "check_point": "形成确认习惯"},
                {"action": "记录客户不满意案例并分析原因", "timeline": "每日", "check_point": "每周复盘改进"},
                {"action": "学习5个超出期望服务案例", "timeline": "1周内", "check_point": "能复述案例要点"}
            ],
            "service_emotion": [
                {"action": "背诵10句情绪激动时的安全话术", "timeline": "3天内", "check_point": "能脱口而出"},
                {"action": "记录情绪触发事件与应对方式", "timeline": "每日", "check_point": "识别自己的触发点"},
                {"action": "模拟高难度客户对话练习", "timeline": "每周2次", "check_point": "情绪稳定性提升"}
            ],
            "problem_solving": [
                {"action": "系统梳理产品知识体系", "timeline": "2周内", "check_point": "通过基础知识测试"},
                {"action": "整理升级处理标准流程", "timeline": "1周内", "check_point": "有明确的判断标准"},
                {"action": "每日记录3个典型问题及解决方案", "timeline": "持续", "check_point": "形成个人知识库"}
            ]
        }

    def analyze_personal_weaknesses(self, agent_results: List[Dict[str, Any]], agent_id: str) -> Dict[str, Any]:
        agent_conversations = [r for r in agent_results if r.get("agent_id") == agent_id]

        if not agent_conversations:
            return {"weaknesses": [], "strengths": [], "overall_assessment": "数据不足"}

        dimension_scores = defaultdict(list)
        deduction_counts = defaultdict(int)
        deduction_details = defaultdict(list)

        for result in agent_conversations:
            dim_scores = result.get("dimension_scores", {})
            for dim, data in dim_scores.items():
                dimension_scores[dim].append(data.get("score", 0))

            for deduction in result.get("deductions", []):
                category = deduction.get("category", "")
                deduction_counts[category] += 1
                deduction_details[category].append(deduction.get("description", ""))

        avg_scores = {dim: sum(scores) / len(scores) for dim, scores in dimension_scores.items() if scores}

        weaknesses = []
        strengths = []

        score_thresholds = [
            ("response_speed", 85, 70),
            ("customer_satisfaction", 85, 70),
            ("service_emotion", 85, 70)
        ]

        for dim, good_threshold, weak_threshold in score_thresholds:
            score = avg_scores.get(dim, 0)
            if score >= good_threshold:
                strengths.append({
                    "dimension": dim,
                    "score": round(score, 2),
                    "assessment": "优秀，继续保持"
                })
            elif score < weak_threshold:
                weaknesses.append({
                    "dimension": dim,
                    "score": round(score, 2),
                    "gap": round(85 - score, 1),
                    "deduction_count": deduction_counts.get(self._get_category_name(dim), 0),
                    "common_issues": deduction_details.get(self._get_category_name(dim), [])[:3]
                })

        weaknesses.sort(key=lambda x: x["gap"], reverse=True)

        return {
            "agent_id": agent_id,
            "conversation_count": len(agent_conversations),
            "avg_comprehensive_score": round(sum(r.get("comprehensive_score", 0) for r in agent_conversations) / len(agent_conversations), 2),
            "dimension_averages": {k: round(v, 2) for k, v in avg_scores.items()},
            "weaknesses": weaknesses,
            "strengths": strengths,
            "primary_weakness": weaknesses[0] if weaknesses else None,
            "overall_assessment": self._get_overall_assessment(weaknesses, strengths)
        }

    def _get_category_name(self, dim: str) -> str:
        mapping = {
            "response_speed": "响应速度",
            "customer_satisfaction": "用户满意度",
            "service_emotion": "客服情绪归因"
        }
        return mapping.get(dim, dim)

    def _get_overall_assessment(self, weaknesses: List, strengths: List) -> str:
        if len(weaknesses) == 0:
            return "表现优秀，各项指标均衡发展"
        elif len(weaknesses) == 1:
            return f"表现良好，主要需改进：{weaknesses[0]['dimension']}"
        else:
            return f"有提升空间，重点改进：{', '.join([w['dimension'] for w in weaknesses[:2]])}"

    def generate_personalized_training_plan(self, weakness_analysis: Dict[str, Any]) -> Dict[str, Any]:
        weaknesses = weakness_analysis.get("weaknesses", [])

        if not weaknesses:
            return {
                "recommendation": "表现优秀，建议巩固现有优势，可参与进阶培训",
                "modules": [],
                "action_items": []
            }

        training_modules = []
        action_items = []

        for weakness in weaknesses:
            dim = weakness["dimension"]
            score = weakness["score"]

            module_info = self._select_training_module(dim, score)
            if module_info:
                training_modules.append(module_info)

            actions = self._generate_specific_actions(dim, score)
            action_items.extend(actions)

        total_hours = sum(float(m.get("duration", "0").replace("小时", "")) for m in training_modules)

        return {
            "agent_id": weakness_analysis.get("agent_id"),
            "overall_assessment": weakness_analysis.get("overall_assessment"),
            "primary_improvement_area": weaknesses[0]["dimension"] if weaknesses else None,
            "weakness_details": weaknesses,
            "recommended_modules": training_modules,
            "total_training_hours": round(total_hours, 1),
            "action_items": action_items,
            "improvement_goals": self._set_improvement_goals(weaknesses)
        }

    def _select_training_module(self, dimension: str, current_score: float) -> Dict[str, Any]:
        module_category = self.training_modules.get(dimension, {})
        if not module_category:
            return None

        category_name = module_category.get("name", dimension)

        if current_score < 60:
            level = "level1"
        elif current_score < 75:
            level = "level1"
        else:
            level = "level2"

        module_data = module_category.get(level, {})

        return {
            "category": category_name,
            "category_key": dimension,
            "level": level,
            "title": module_data.get("title", ""),
            "target_weakness": module_data.get("target_weakness", ""),
            "content": module_data.get("content", []),
            "duration": module_data.get("duration", "0小时"),
            "priority": module_data.get("priority", "medium"),
            "practice_exercises": module_data.get("practice_exercises", []),
            "expected_improvement": module_data.get("expected_improvement", "+10分"),
            "current_score": round(current_score, 2),
            "target_score": min(100, current_score + 15)
        }

    def _generate_specific_actions(self, dimension: str, current_score: float) -> List[Dict]:
        templates = self.improvement_templates.get(dimension, [])
        actions = []

        for i, template in enumerate(templates):
            priority = "high" if i == 0 else "medium" if i == 1 else "low"
            actions.append({
                **template,
                "dimension": dimension,
                "priority": priority,
                "status": "pending"
            })

        return actions

    def _set_improvement_goals(self, weaknesses: List) -> List[Dict]:
        goals = []
        for weakness in weaknesses[:2]:
            dim = weakness["dimension"]
            current = weakness["score"]
            target = min(100, current + 15)
            goals.append({
                "dimension": dim,
                "current_score": round(current, 2),
                "target_score": round(target, 2),
                "improvement_target": round(target - current, 1),
                "timeframe": "4周"
            })
        return goals

    def generate_batch_training_report(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not all_results:
            return {}

        agent_ids = list(set(r.get("agent_id", "unknown") for r in all_results))

        agent_analyses = []
        for agent_id in agent_ids:
            analysis = self.analyze_personal_weaknesses(all_results, agent_id)
            agent_analyses.append(analysis)

        agent_training_plans = []
        for analysis in agent_analyses:
            plan = self.generate_personalized_training_plan(analysis)
            agent_training_plans.append(plan)

        common_weaknesses = self._identify_common_weaknesses(agent_analyses)

        return {
            "total_agents": len(agent_ids),
            "total_conversations": len(all_results),
            "common_weaknesses": common_weaknesses,
            "agent_training_plans": agent_training_plans,
            "team_training_recommendation": self._generate_team_training_recommendation(common_weaknesses)
        }

    def _identify_common_weaknesses(self, agent_analyses: List[Dict]) -> List[Dict]:
        weakness_counts = defaultdict(int)
        weakness_scores = defaultdict(list)

        for analysis in agent_analyses:
            for weakness in analysis.get("weaknesses", []):
                dim = weakness["dimension"]
                weakness_counts[dim] += 1
                weakness_scores[dim].append(weakness["score"])

        common_weaknesses = []
        for dim, count in weakness_counts.items():
            if count >= 2:
                avg_score = sum(weakness_scores[dim]) / len(weakness_scores[dim])
                common_weaknesses.append({
                    "dimension": dim,
                    "affected_agents": count,
                    "avg_score": round(avg_score, 2),
                    "recommendation": f"建议组织{dim}专项培训"
                })

        common_weaknesses.sort(key=lambda x: x["affected_agents"], reverse=True)
        return common_weaknesses

    def _generate_team_training_recommendation(self, common_weaknesses: List[Dict]) -> Dict[str, Any]:
        if not common_weaknesses:
            return {
                "recommendation": "团队整体表现良好，建议组织经验分享会",
                "priority_modules": []
            }

        top_weakness = common_weaknesses[0]
        dim = top_weakness["dimension"]

        module_info = self.training_modules.get(dim, {})
        category_name = module_info.get("name", dim)

        return {
            "primary_focus": category_name,
            "affected_agents": top_weakness["affected_agents"],
            "avg_score": top_weakness["avg_score"],
            "recommended_module": module_info.get("level1", {}).get("title", ""),
            "duration": module_info.get("level1", {}).get("duration", ""),
            "expected_impact": f"预计提升团队{category_name}平均分10-15分"
        }
