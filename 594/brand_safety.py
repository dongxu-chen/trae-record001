import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


class BrandSafetyDetector:
    def __init__(self):
        self.risk_categories = {
            'political_sensitivity': {
                'name': '政治敏感',
                'weight': 0.25,
                'keywords': ['政治', '政府', '国家', '领导人', '敏感事件', '抗议', '示威', '游行', '政策争议', '选举'],
                'severity': 'high'
            },
            'controversial_topics': {
                'name': '争议话题',
                'weight': 0.20,
                'keywords': ['堕胎', '宗教', '种族', '歧视', '性别争议', '枪支', '战争', '暴力', '极端观点'],
                'severity': 'high'
            },
            'inappropriate_content': {
                'name': '不当内容',
                'weight': 0.20,
                'keywords': ['低俗', '色情', '暴力', '血腥', '恐怖', '恶心', '赌博', '毒品', '烟酒'],
                'severity': 'high'
            },
            'negative_sentiment': {
                'name': '负面情绪',
                'weight': 0.15,
                'keywords': ['抱怨', '投诉', '负面', '不满', '愤怒', '批评', '指责', '攻击', '辱骂', '撕逼'],
                'severity': 'medium'
            },
            'brand_conflict': {
                'name': '品牌冲突',
                'weight': 0.20,
                'keywords': ['竞品', '对手品牌', '其他品牌', '代言冲突', '品牌负面', '质量问题', '虚假宣传'],
                'severity': 'medium'
            }
        }
        
        self.brand_taxonomy = {
            'beauty': ['美妆', '护肤', '化妆品', '香水', '美容', '彩妆'],
            'fashion': ['时尚', '服装', '穿搭', '奢侈品', '包包', '鞋履', '配饰'],
            'food': ['美食', '餐饮', '零食', '饮料', '健康食品', '保健品'],
            'tech': ['科技', '数码', '手机', '电脑', '游戏', '电子'],
            'fitness': ['健身', '运动', '瑜伽', '户外', '体育', '减肥'],
            'travel': ['旅行', '酒店', '航空', '旅游', '度假'],
            'parenting': ['母婴', '育儿', '亲子', '儿童', '宝宝'],
            'finance': ['金融', '理财', '保险', '银行', '投资']
        }

    def analyze_content_risk(self, influencer_id: str, content_history: List[Dict] = None) -> Dict:
        if content_history is None:
            content_history = self._generate_mock_content_history(influencer_id)
        
        risk_scores = {}
        detected_risks = []
        
        for category, config in self.risk_categories.items():
            score = 0
            matched_keywords = []
            
            for content in content_history:
                text = content.get('content', '').lower()
                for keyword in config['keywords']:
                    if keyword in text:
                        score += config['weight'] * content.get('importance', 1.0)
                        matched_keywords.append(keyword)
            
            risk_scores[category] = {
                'score': min(score * 20, 100),
                'matched_keywords': list(set(matched_keywords)),
                'severity': config['severity']
            }
            
            if risk_scores[category]['score'] > 30:
                detected_risks.append({
                    'category': config['name'],
                    'score': risk_scores[category]['score'],
                    'severity': config['severity'],
                    'keywords': matched_keywords[:5]
                })
        
        overall_risk_score = sum(
            risk_scores[cat]['score'] * config['weight']
            for cat, config in self.risk_categories.items()
        )
        
        risk_level = self._get_risk_level(overall_risk_score)
        
        return {
            'influencer_id': influencer_id,
            'overall_risk_score': round(overall_risk_score, 1),
            'risk_level': risk_level,
            'risk_breakdown': risk_scores,
            'detected_risks': detected_risks,
            'content_analyzed': len(content_history),
            'recommendation': self._get_safety_recommendation(risk_level, detected_risks)
        }

    def _generate_mock_content_history(self, influencer_id: str) -> List[Dict]:
        np.random.seed(hash(influencer_id) % 10000)
        
        content_templates = [
            '今天分享一个超棒的产品给大家！真的太好用了',
            '最近发现这个牌子的东西质量真的很一般，大家谨慎购买',
            '参加了一个超棒的活动，认识了很多有趣的人',
            '关于最近的热点事件，我想说几句我的看法...',
            '日常vlog | 跟我一起过一天 工作 健身 美食',
            '这个品牌的护肤品我用了三年，真心推荐',
            '最近在尝试新的风格，大家觉得怎么样？',
            '收到了品牌爸爸的礼物，太开心了！',
            '分享一下我的理财心得，希望对大家有帮助',
            '最近心情不好，有些事情真的很无语'
        ]
        
        history = []
        for i in range(np.random.randint(20, 50)):
            days_ago = np.random.randint(1, 365)
            content = content_templates[np.random.randint(0, len(content_templates))]
            
            if np.random.random() < 0.15:
                risk_keywords = []
                for config in self.risk_categories.values():
                    if np.random.random() < 0.3:
                        risk_keywords.append(np.random.choice(config['keywords']))
                if risk_keywords:
                    content = content + ' ' + ' '.join(risk_keywords)
            
            history.append({
                'content_id': f'CONTENT_{influencer_id}_{i}',
                'content': content,
                'date': (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d'),
                'platform': np.random.choice(['TikTok', 'Xiaohongshu', 'Weibo', 'Instagram']),
                'views': np.random.randint(1000, 1000000),
                'importance': np.random.uniform(0.5, 1.5)
            })
        
        return sorted(history, key=lambda x: x['date'], reverse=True)

    def _get_risk_level(self, score: float) -> str:
        if score < 15:
            return 'A - 安全'
        elif score < 30:
            return 'B - 低风险'
        elif score < 50:
            return 'C - 中等风险'
        elif score < 70:
            return 'D - 高风险'
        else:
            return 'E - 极高风险'

    def _get_safety_recommendation(self, risk_level: str, detected_risks: List[Dict]) -> List[str]:
        recommendations = []
        
        if 'A' in risk_level:
            recommendations.append('品牌安全度高，可以正常合作')
            recommendations.append('建议定期进行内容安全复核')
        elif 'B' in risk_level:
            recommendations.append('整体风险较低，可进行合作')
            recommendations.append('建议在合作前进行内容审查')
        elif 'C' in risk_level:
            recommendations.append('存在一定风险，建议谨慎合作')
            recommendations.append('建议在合同中增加内容审查条款')
            recommendations.append('可考虑降低合作预算或缩短合作周期')
        elif 'D' in risk_level:
            recommendations.append('风险较高，不建议进行重要合作')
            recommendations.append('如需合作，建议增加严格的内容审核机制')
            recommendations.append('建议设置违约条款和终止合作机制')
        else:
            recommendations.append('风险极高，强烈不建议合作')
            recommendations.append('建议将该网红加入风险监控名单')
        
        if detected_risks:
            high_severity = [r for r in detected_risks if r['severity'] == 'high']
            if high_severity:
                recommendations.append(f"检测到 {len(high_severity)} 项高风险内容，需重点关注")
        
        return recommendations

    def calculate_brand_fit_score(self, influencer_data: pd.Series, brand_category: str, 
                                   brand_values: List[str] = None) -> Dict:
        category_score = 0
        influencer_category = influencer_data.get('category', '')
        
        if brand_category in self.brand_taxonomy:
            brand_keywords = self.brand_taxonomy[brand_category]
            if influencer_category in brand_keywords:
                category_score = 100
            else:
                for keyword in brand_keywords:
                    if keyword in influencer_category:
                        category_score = 70
                        break
                else:
                    category_score = 30
        
        content_risk = self.analyze_content_risk(influencer_data['id'])
        safety_score = 100 - content_risk['overall_risk_score']
        
        value_alignment = 70
        if brand_values:
            value_alignment = np.random.randint(50, 100)
        
        overall_fit = category_score * 0.4 + safety_score * 0.35 + value_alignment * 0.25
        
        fit_level = '完美匹配' if overall_fit >= 80 else \
                   '较好匹配' if overall_fit >= 60 else \
                   '一般匹配' if overall_fit >= 40 else '匹配度低'
        
        return {
            'influencer_id': influencer_data['id'],
            'influencer_name': influencer_data['name'],
            'brand_category': brand_category,
            'category_match_score': round(category_score, 1),
            'safety_score': round(safety_score, 1),
            'value_alignment_score': round(value_alignment, 1),
            'overall_brand_fit_score': round(overall_fit, 1),
            'fit_level': fit_level,
            'risk_warnings': content_risk['detected_risks'],
            'recommendations': [
                f"品牌匹配度：{fit_level}",
                f"类目匹配度：{category_score:.1f}分",
                f"内容安全度：{safety_score:.1f}分",
                f"价值观契合：{value_alignment:.1f}分"
            ]
        }

    def batch_analyze_safety(self, influencer_df: pd.DataFrame) -> pd.DataFrame:
        results = []
        for _, row in influencer_df.iterrows():
            analysis = self.analyze_content_risk(row['id'])
            results.append({
                'id': row['id'],
                'name': row['name'],
                'platform': row['platform'],
                'category': row['category'],
                'overall_risk_score': analysis['overall_risk_score'],
                'risk_level': analysis['risk_level'],
                'risk_category_count': len(analysis['detected_risks']),
                'high_risk_count': len([r for r in analysis['detected_risks'] if r['severity'] == 'high'])
            })
        
        return pd.DataFrame(results)

    def get_safety_report(self, influencer_df: pd.DataFrame, influencer_id: str) -> Dict:
        influencer_data = influencer_df[influencer_df['id'] == influencer_id].iloc[0]
        
        content_risk = self.analyze_content_risk(influencer_id)
        
        history = self._generate_mock_content_history(influencer_id)
        
        recent_high_risk = []
        for content in history[:10]:
            for category, config in self.risk_categories.items():
                for keyword in config['keywords']:
                    if keyword in content['content']:
                        recent_high_risk.append({
                            'date': content['date'],
                            'content': content['content'][:50] + '...',
                            'platform': content['platform'],
                            'risk_category': config['name'],
                            'views': content['views']
                        })
                        break
        
        return {
            'basic_info': {
                'id': influencer_data['id'],
                'name': influencer_data['name'],
                'platform': influencer_data['platform'],
                'category': influencer_data['category'],
                'followers': influencer_data['followers']
            },
            'risk_summary': {
                'overall_risk_score': content_risk['overall_risk_score'],
                'risk_level': content_risk['risk_level'],
                'total_risk_items': len(content_risk['detected_risks']),
                'high_risk_items': len([r for r in content_risk['detected_risks'] if r['severity'] == 'high'])
            },
            'risk_details': content_risk['risk_breakdown'],
            'recent_high_risk_content': recent_high_risk[:5],
            'recommendations': content_risk['recommendation'],
            'safety_score': 100 - content_risk['overall_risk_score']
        }
