from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import re


@dataclass
class ResponseSuggestion:
    strategy: str
    strategy_cn: str
    priority: int
    suggested_responses: List[str]
    explanation: str
    confidence: float
    applicable_emotions: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'strategy': self.strategy,
            'strategy_cn': self.strategy_cn,
            'priority': self.priority,
            'suggested_responses': self.suggested_responses,
            'explanation': self.explanation,
            'confidence': self.confidence,
            'applicable_emotions': self.applicable_emotions
        }


class ResponseStrategyEngine:
    def __init__(self):
        self.strategies = {
            'empathy': ResponseSuggestion(
                strategy='empathy',
                strategy_cn='共情安抚',
                priority=1,
                suggested_responses=[
                    "我非常理解您的感受，给您带来不便确实很抱歉。",
                    "您的心情我完全理解，换作是我也会感到不舒服。",
                    "非常抱歉让您有这样的体验，我们会认真对待的。"
                ],
                explanation="当客户表达负面情绪时，首先需要表达理解和共情，让客户感受到被尊重。",
                confidence=0.9,
                applicable_emotions=['angry', 'disappointed', 'anxious']
            ),
            'apology': ResponseSuggestion(
                strategy='apology',
                strategy_cn='真诚道歉',
                priority=2,
                suggested_responses=[
                    "真的非常抱歉，这是我们的问题，我们立即为您处理。",
                    "对不起，给您带来了不好的体验，我们马上改进。",
                    "非常抱歉，确实是我们做得不够好，请您原谅。"
                ],
                explanation="当明确是我方问题时，应主动承担责任，不推诿，不辩解。",
                confidence=0.95,
                applicable_emotions=['angry', 'disappointed']
            ),
            'solution_focused': ResponseSuggestion(
                strategy='solution_focused',
                strategy_cn='提供方案',
                priority=3,
                suggested_responses=[
                    "针对这个问题，我们可以为您提供以下解决方案...",
                    "我来帮您处理这个问题，具体可以这样做...",
                    "为了解决您的问题，我建议我们可以..."
                ],
                explanation="在安抚情绪后，需要及时提供具体的解决方案，让客户看到解决问题的希望。",
                confidence=0.85,
                applicable_emotions=['angry', 'disappointed', 'anxious']
            ),
            'time_assurance': ResponseSuggestion(
                strategy='time_assurance',
                strategy_cn='时效承诺',
                priority=4,
                suggested_responses=[
                    "我会在30分钟内给您回复，请您稍等。",
                    "这个问题我们今天内一定解决，您放心。",
                    "我现在就为您处理，预计10分钟可以完成。"
                ],
                explanation="当客户表现出焦虑时，明确告知处理时限可以有效降低焦虑感。",
                confidence=0.8,
                applicable_emotions=['anxious']
            ),
            'step_by_step': ResponseSuggestion(
                strategy='step_by_step',
                strategy_cn='分步指引',
                priority=5,
                suggested_responses=[
                    "请您按照以下步骤操作：首先...然后...最后...",
                    "我一步步教您怎么处理，首先请您...",
                    "解决这个问题很简单，您只需要做这几步..."
                ],
                explanation="对于操作类问题，分步清晰的指引可以让客户更容易理解和操作。",
                confidence=0.75,
                applicable_emotions=['anxious', 'disappointed']
            ),
            'compensation': ResponseSuggestion(
                strategy='compensation',
                strategy_cn='补偿方案',
                priority=6,
                suggested_responses=[
                    "为了表达歉意，我们可以为您提供...作为补偿。",
                    "考虑到您的情况，我们可以赠送您...",
                    "我们可以为您申请...作为这次不好体验的补偿。"
                ],
                explanation="当客户情绪非常激动或问题比较严重时，可以考虑提供适当补偿。",
                confidence=0.7,
                applicable_emotions=['angry']
            ),
            'reassurance': ResponseSuggestion(
                strategy='reassurance',
                strategy_cn='后续保障',
                priority=7,
                suggested_responses=[
                    "后续如果还有任何问题，您随时联系我，我会全程跟进。",
                    "您放心，我会持续关注这个问题，直到完全解决。",
                    "如果后续还有不满意的地方，您直接找我就好。"
                ],
                explanation="问题解决后，提供后续保障承诺可以增强客户信任感。",
                confidence=0.8,
                applicable_emotions=['satisfied', 'angry', 'disappointed', 'anxious']
            ),
            'positive_reinforcement': ResponseSuggestion(
                strategy='positive_reinforcement',
                strategy_cn='积极回应',
                priority=8,
                suggested_responses=[
                    "非常感谢您的理解和支持！",
                    "很高兴能帮到您，您的满意是我们最大的动力。",
                    "感谢您的反馈，我们会继续努力做得更好！"
                ],
                explanation="当客户表达满意时，积极回应可以强化正面情绪，提升客户体验。",
                confidence=0.9,
                applicable_emotions=['satisfied']
            ),
            'clarification': ResponseSuggestion(
                strategy='clarification',
                strategy_cn='确认问题',
                priority=9,
                suggested_responses=[
                    "为了更好地帮助您，我想再确认一下具体情况是...",
                    "您的意思是...对吗？我理解得没错吧？",
                    "可以请您再详细描述一下吗？这样我能更准确地帮您。"
                ],
                explanation="在问题不明确时，及时确认可以避免误解，提高解决效率。",
                confidence=0.7,
                applicable_emotions=['angry', 'disappointed', 'anxious']
            ),
            'expertise': ResponseSuggestion(
                strategy='expertise',
                strategy_cn='专业解答',
                priority=10,
                suggested_responses=[
                    "根据您的情况，从专业角度来说，建议您...",
                    "这个问题的原因是...，解决方案是...",
                    "我来为您详细解释一下这个问题..."
                ],
                explanation="当客户需要了解详细原因时，专业的解答可以增强可信度。",
                confidence=0.75,
                applicable_emotions=['anxious', 'disappointed']
            )
        }
        
        self.emotion_context_patterns = {
            'angry': {
                'keywords': ['为什么', '怎么回事', '投诉', '垃圾', '差劲', '再也不'],
                'escalation_signs': ['我要投诉', '找你们经理', '媒体曝光', '315', '起诉']
            },
            'disappointed': {
                'keywords': ['没想到', '太让人失望', '算了', '以后不会', '不应该是这样'],
                'escalation_signs': ['以后再也不来了', '太失望了', '对你们失去信心']
            },
            'anxious': {
                'keywords': ['急', '快点', '什么时候', '怎么还没', '等不及'],
                'escalation_signs': ['很急', '马上要', '必须今天', '等不了']
            }
        }

    def analyze_context(self, conversation_history: List[Dict], current_sentiment: Dict) -> Dict:
        context_info = {
            'emotion': current_sentiment.get('predicted_label', 'neutral'),
            'emotion_scores': current_sentiment.get('scores', {}),
            'confidence': current_sentiment.get('confidence', 0),
            'escalation_risk': 'low',
            'key_concerns': [],
            'conversation_phase': 'ongoing'
        }
        
        recent_messages = [h for h in conversation_history[-5:] if h.get('speaker') == 'customer']
        
        for msg in recent_messages:
            text = msg.get('text', '')
            emotion = context_info['emotion']
            
            if emotion in self.emotion_context_patterns:
                patterns = self.emotion_context_patterns[emotion]
                
                for keyword in patterns['keywords']:
                    if keyword in text:
                        context_info['key_concerns'].append(keyword)
                
                for sign in patterns['escalation_signs']:
                    if sign in text:
                        context_info['escalation_risk'] = 'high'
        
        total_messages = len(conversation_history)
        if total_messages < 3:
            context_info['conversation_phase'] = 'early'
        elif total_messages < 8:
            context_info['conversation_phase'] = 'ongoing'
        else:
            context_info['conversation_phase'] = 'extended'
        
        return context_info

    def calculate_strategy_relevance(self, strategy: ResponseSuggestion, 
                                     context_info: Dict) -> float:
        score = 0.0
        
        if context_info['emotion'] in strategy.applicable_emotions:
            score += 0.4
        
        emotion_score = context_info['emotion_scores'].get(context_info['emotion'], 0)
        score += emotion_score * 0.3
        
        if context_info['escalation_risk'] == 'high':
            if strategy.strategy in ['empathy', 'apology', 'compensation', 'time_assurance']:
                score += 0.2
        
        if context_info['conversation_phase'] == 'early':
            if strategy.strategy in ['clarification', 'empathy']:
                score += 0.1
        elif context_info['conversation_phase'] == 'extended':
            if strategy.strategy in ['solution_focused', 'compensation', 'reassurance']:
                score += 0.1
        
        priority_factor = 1.0 - (strategy.priority / 20)
        score += priority_factor * 0.2
        
        return min(1.0, max(0.1, score))

    def generate_suggestions(self, conversation_history: List[Dict], 
                             current_sentiment: Dict, 
                             top_k: int = 3) -> List[ResponseSuggestion]:
        context_info = self.analyze_context(conversation_history, current_sentiment)
        
        scored_strategies = []
        for strategy in self.strategies.values():
            relevance = self.calculate_strategy_relevance(strategy, context_info)
            if relevance > 0.3:
                scored_strategies.append((strategy, relevance))
        
        scored_strategies.sort(key=lambda x: x[1], reverse=True)
        
        suggestions = []
        for strategy, confidence in scored_strategies[:top_k]:
            suggestion = ResponseSuggestion(
                strategy=strategy.strategy,
                strategy_cn=strategy.strategy_cn,
                priority=strategy.priority,
                suggested_responses=self._adapt_responses(strategy.suggested_responses, context_info),
                explanation=strategy.explanation,
                confidence=confidence,
                applicable_emotions=strategy.applicable_emotions
            )
            suggestions.append(suggestion)
        
        return suggestions

    def _adapt_responses(self, responses: List[str], context_info: Dict) -> List[str]:
        adapted = []
        for resp in responses:
            if context_info['escalation_risk'] == 'high' and '非常' not in resp and '真的' not in resp:
                resp = resp.replace('抱歉', '非常抱歉').replace('对不起', '真的对不起')
            adapted.append(resp)
        return adapted

    def get_quick_replies(self, sentiment_label: str) -> List[str]:
        quick_replies = {
            'satisfied': [
                "不客气，很高兴能帮到您！",
                "感谢您的支持，祝您生活愉快！",
                "有任何问题随时联系我们！"
            ],
            'angry': [
                "非常抱歉给您带来不好的体验，我马上为您处理。",
                "我理解您的心情，您能告诉我具体情况吗？",
                "这确实是我们的问题，我立即为您解决。"
            ],
            'disappointed': [
                "非常理解您的感受，我们会努力改进的。",
                "您的反馈对我们很重要，能详细说说吗？",
                "抱歉让您失望了，我们可以为您做些什么吗？"
            ],
            'anxious': [
                "您别急，我来帮您看看具体情况。",
                "请您稍等，我正在为您查询处理进度。",
                "这个问题我们会尽快处理，预计30分钟内给您回复。"
            ]
        }
        return quick_replies.get(sentiment_label, [])


class ConversationCoaching:
    def __init__(self):
        self.quality_metrics = {
            'response_time': {'good': 60, 'warning': 180, 'unit': '秒'},
            'empathy_score': {'good': 0.7, 'warning': 0.4},
            'resolution_rate': {'good': 0.8, 'warning': 0.5}
        }
        
        self.best_practices = {
            'do': [
                "使用客户称呼，建立亲切沟通",
                "适时表达理解和共情",
                "主动提供解决方案",
                "确认客户是否完全理解",
                "结束语要友好专业"
            ],
            'dont': [
                "避免使用专业术语或行话",
                "不要打断客户讲话",
                "避免推诿责任（如'不是我们的问题'）",
                "不要过度承诺",
                "避免使用负面词汇"
            ]
        }

    def analyze_conversation_quality(self, conversation_history: List[Dict]) -> Dict:
        quality_score = 0.8
        issues = []
        positives = []
        
        agent_messages = [h for h in conversation_history if h.get('speaker') == 'agent']
        customer_messages = [h for h in conversation_history if h.get('speaker') == 'customer']
        
        for msg in agent_messages:
            text = msg.get('text', '')
            if any(word in text for word in ['理解', '抱歉', '对不起', '您说的对']):
                quality_score += 0.02
                positives.append('使用了共情表达')
            
            if any(word in text for word in ['可以为您', '解决方案', '建议您', '我来帮您']):
                quality_score += 0.02
                positives.append('主动提供解决方案')
            
            if any(word in text for word in ['不是我们', '没办法', '规定', '制度']):
                quality_score -= 0.05
                issues.append('可能使用了推诿或生硬的表达')
            
            if len(text) > 200:
                quality_score -= 0.01
                issues.append('回复内容过长，建议简洁明了')
        
        if len(customer_messages) >= 2:
            last_customer = customer_messages[-1]
            last_customer_sentiment = last_customer.get('sentiment', {}).get('predicted_label', '')
            if last_customer_sentiment in ['angry', 'disappointed']:
                if len(agent_messages) > 0:
                    last_agent = agent_messages[-1].get('text', '')
                    if not any(word in last_agent for word in ['理解', '抱歉', '对不起', '解决']):
                        quality_score -= 0.05
                        issues.append('客户情绪负面，建议先表达理解再解决问题')
        
        quality_score = max(0, min(1, quality_score))
        
        return {
            'overall_score': quality_score,
            'grade': 'A' if quality_score >= 0.9 else 'B' if quality_score >= 0.7 else 'C' if quality_score >= 0.5 else 'D',
            'positives': list(set(positives)),
            'issues': list(set(issues)),
            'suggestions': self._generate_improvement_suggestions(issues)
        }

    def _generate_improvement_suggestions(self, issues: List[str]) -> List[str]:
        suggestions = []
        
        if any('共情' in i for i in issues):
            suggestions.append("建议在回复中加入共情表达，如'我理解您的感受'")
        
        if any('推诿' in i for i in issues):
            suggestions.append("避免使用生硬的推托措辞，改为'我来帮您看看怎么处理'")
        
        if any('过长' in i for i in issues):
            suggestions.append("建议将长回复拆分成多条，每条聚焦一个要点")
        
        if not suggestions:
            suggestions.append("继续保持良好的沟通风格！")
        
        return suggestions


def create_response_suggester() -> ResponseStrategyEngine:
    return ResponseStrategyEngine()


def create_conversation_coaching() -> ConversationCoaching:
    return ConversationCoaching()
