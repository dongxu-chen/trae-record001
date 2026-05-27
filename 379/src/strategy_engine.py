import pandas as pd
import numpy as np


class StrategyEngine:
    def __init__(self):
        self.segment_strategies = {
            '高价值客户': self._high_value_maintenance_strategy,
            '中高价值客户': self._medium_high_value_strategy,
            '中价值客户': self._medium_value_activation_strategy,
            '中低价值客户': self._medium_low_value_strategy,
            '低价值客户': self._low_value_conversion_strategy
        }
    
    def generate_segment_strategy(self, segment_name, segment_profile, segment_stats):
        if segment_name in self.segment_strategies:
            return self.segment_strategies[segment_name](segment_profile, segment_stats)
        else:
            return self._generic_strategy(segment_name, segment_profile, segment_stats)
    
    def _high_value_maintenance_strategy(self, profile, stats):
        avg_ltv = profile.get('avg_ltv', 0)
        churn_rate = profile.get('churn_rate', 0)
        avg_reactivation = profile.get('avg_reactivation_prob', 0)
        
        strategies = {
            'segment_name': '高价值客户',
            'strategy_type': '维护',
            'customer_count': profile.get('customer_count', 0),
            'avg_ltv': avg_ltv,
            'churn_rate': churn_rate,
            'avg_reactivation_prob': avg_reactivation,
            'priority': '最高',
            'overall_goal': '维持高价值客户忠诚度，防止流失，最大化长期价值',
            'maintenance_strategies': [
                {
                    'strategy': '专属客户经理制',
                    'description': '为每位高价值客户配备专属客户经理，提供一对一服务',
                    'expected_impact': '提升客户满意度 30-50%，降低流失率 20-30%',
                    'implementation_cost': '高'
                },
                {
                    'strategy': 'VIP专属权益包',
                    'description': '提供专属折扣、优先配送、免费退换、专属客服通道等VIP权益',
                    'expected_impact': '提升客户粘性，延长生命周期 12-24个月',
                    'implementation_cost': '中高'
                },
                {
                    'strategy': '个性化精准营销',
                    'description': '基于购买历史、浏览行为和偏好进行深度个性化推荐',
                    'expected_impact': '提升复购率 15-25%，客单价提升 10-20%',
                    'implementation_cost': '中'
                },
                {
                    'strategy': '会员等级保级机制',
                    'description': '设置消费保级门槛，享受持续高等级权益激励',
                    'expected_impact': '维持高价值客户消费动力，减少降级风险',
                    'implementation_cost': '中'
                },
                {
                    'strategy': '专属产品与服务',
                    'description': '推出仅限高价值客户购买的限量版产品或定制化服务',
                    'expected_impact': '提升品牌认同感，增加溢价收入 15-30%',
                    'implementation_cost': '中高'
                }
            ],
            'churn_prevention': [
                {
                    'strategy': '实时流失预警',
                    'description': '建立活跃度监控系统，活跃度下降10%时自动触发关怀流程',
                    'expected_impact': '将高价值客户流失率控制在 5% 以内'
                },
                {
                    'strategy': '主动关怀回访',
                    'description': '每月至少1次主动回访，了解需求和满意度',
                    'expected_impact': '及时发现问题，提升客户忠诚度'
                },
                {
                    'strategy': '专属流失挽回方案',
                    'description': '对已流失高价值客户提供专属挽回礼包和高级客户经理跟进',
                    'expected_impact': '流失客户召回率提升 30-50%'
                }
            ],
            'exclusive_activities': [
                '邀请参加新品发布会、品鉴会、高端沙龙',
                '新品上线前优先体验和试用资格',
                '年度VIP答谢晚宴或专属旅游活动',
                '限量版产品优先购买权'
            ],
            'communication_preferences': [
                '频次：每月1-2次高质量内容，避免过度打扰',
                '渠道：专属客户经理电话/微信、高端定制邮件、VIP专线',
                '内容：专属优惠、新品预告、品牌故事、节日问候'
            ],
            'reactivation_strategy_for_churned': [
                {
                    'strategy': '高价值客户专属召回',
                    'description': '对流失的高价值客户提供高额回归礼包（如大额优惠券、赠送服务）',
                    'expected_impact': f'预计召回率: {avg_reactivation*100:.1f}%',
                    'implementation_cost': '高'
                }
            ],
            'key_metrics_to_track': [
                '活跃度变化趋势',
                '客单价变化',
                '购买频次',
                '客户满意度评分',
                '净推荐值(NPS)',
                '流失率',
                '召回率'
            ],
            'estimated_budget_allocation': f'建议分配 45-55% 的客户营销预算'
        }
        
        return strategies
    
    def _medium_value_activation_strategy(self, profile, stats):
        avg_ltv = profile.get('avg_ltv', 0)
        avg_frequency = profile.get('avg_frequency', 0)
        churn_rate = profile.get('churn_rate', 0)
        avg_reactivation = profile.get('avg_reactivation_prob', 0)
        
        strategies = {
            'segment_name': '中价值客户',
            'strategy_type': '促活',
            'customer_count': profile.get('customer_count', 0),
            'avg_ltv': avg_ltv,
            'churn_rate': churn_rate,
            'avg_reactivation_prob': avg_reactivation,
            'priority': '高',
            'overall_goal': '提升购买频次和活跃度，促进向高价值客户转化',
            'activation_strategies': [
                {
                    'strategy': '购买频次提升计划',
                    'description': '通过满减券、买赠活动、积分翻倍等激励提升购买频次',
                    'expected_impact': '购买频次提升 20-40%',
                    'implementation_cost': '中'
                },
                {
                    'strategy': '活跃度运营',
                    'description': '签到奖励、任务中心、日常互动活动提升APP活跃度',
                    'expected_impact': '日活提升 15-30%，复购周期缩短 10-20%',
                    'implementation_cost': '中低'
                },
                {
                    'strategy': '场景化精准触达',
                    'description': '基于购买周期、浏览行为、节日场景推送相关产品',
                    'expected_impact': '营销响应率提升 20-35%',
                    'implementation_cost': '中'
                },
                {
                    'strategy': '会员升级激励',
                    'description': '设置升级目标和进度条，达成后升级享受更多权益',
                    'expected_impact': '向高价值客户转化率提升 15-25%',
                    'implementation_cost': '中'
                },
                {
                    'strategy': '交叉销售推荐',
                    'description': '基于已购商品推荐互补品类和关联产品',
                    'expected_impact': '客单价提升 15-25%，品类渗透率提升',
                    'implementation_cost': '中'
                }
            ],
            'engagement_enhancement': [
                {
                    'strategy': '内容营销培育',
                    'description': '提供产品使用指南、行业资讯、生活方式内容',
                    'expected_impact': '增加品牌接触频次，提升产品认知'
                },
                {
                    'strategy': '社群运营',
                    'description': '邀请加入客户社群，促进用户间交流和分享',
                    'expected_impact': '增强归属感，提升复购意愿'
                }
            ],
            'churn_prevention': [
                {
                    'strategy': '沉睡客户唤醒',
                    'description': '对30天未购买客户发送阶梯式优惠券',
                    'expected_impact': '唤醒率预计 10-20%'
                },
                {
                    'strategy': '复购周期提醒',
                    'description': '基于购买周期智能提醒补货或再次购买',
                    'expected_impact': '提升复购率 10-18%'
                }
            ],
            'reactivation_strategy_for_churned': [
                {
                    'strategy': '中价值客户召回计划',
                    'description': '对流失的中价值客户提供回归优惠券和限时权益',
                    'expected_impact': f'预计召回率: {avg_reactivation*100:.1f}%',
                    'implementation_cost': '中'
                },
                {
                    'strategy': '回归礼包激励',
                    'description': '回归即送积分礼包和会员临时升级体验',
                    'expected_impact': '提升回归客户的留存率'
                }
            ],
            'communication_preferences': [
                '频次：每周1-2次，活动期间可适当增加',
                '渠道：APP推送、短信、邮件、社交媒体',
                '内容：优惠信息、新品推荐、使用技巧、活动通知'
            ],
            'key_metrics_to_track': [
                '购买频次变化',
                '活跃度(DAU/MAU)',
                '客单价提升幅度',
                '品类渗透率',
                '高价值客户转化率',
                '活动参与率',
                '唤醒率'
            ],
            'estimated_budget_allocation': f'建议分配 30-40% 的客户营销预算'
        }
        
        return strategies
    
    def _medium_high_value_strategy(self, profile, stats):
        base_strategy = self._medium_value_activation_strategy(profile, stats)
        base_strategy['segment_name'] = '中高价值客户'
        base_strategy['overall_goal'] = '稳定消费行为，加速向高价值客户转化'
        base_strategy['priority'] = '高'
        base_strategy['estimated_budget_allocation'] = f'建议分配 25-35% 的客户营销预算'
        return base_strategy
    
    def _medium_low_value_strategy(self, profile, stats):
        base_strategy = self._low_value_conversion_strategy(profile, stats)
        base_strategy['segment_name'] = '中低价值客户'
        base_strategy['overall_goal'] = '筛选有潜力客户，尝试提升活跃度和客单价'
        base_strategy['priority'] = '中低'
        base_strategy['estimated_budget_allocation'] = f'建议分配 8-15% 的客户营销预算'
        return base_strategy
    
    def _low_value_conversion_strategy(self, profile, stats):
        avg_ltv = profile.get('avg_ltv', 0)
        churn_rate = profile.get('churn_rate', 0)
        avg_reactivation = profile.get('avg_reactivation_prob', 0)
        
        strategies = {
            'segment_name': '低价值客户',
            'strategy_type': '促转化',
            'customer_count': profile.get('customer_count', 0),
            'avg_ltv': avg_ltv,
            'churn_rate': churn_rate,
            'avg_reactivation_prob': avg_reactivation,
            'priority': '低',
            'overall_goal': '筛选有转化潜力的客户，控制服务成本，挖掘增量价值',
            'conversion_strategies': [
                {
                    'strategy': '首单/复购激励',
                    'description': '对新客户或低频客户提供首单优惠、复购券等激励',
                    'expected_impact': '提升转化率 5-15%',
                    'implementation_cost': '低'
                },
                {
                    'strategy': '高性价比产品推荐',
                    'description': '推荐热销、高好评、低客单价的性价比产品',
                    'expected_impact': '降低购买决策门槛，提升尝试意愿',
                    'implementation_cost': '低'
                },
                {
                    'strategy': '小额凑单推荐',
                    'description': '根据购物车金额智能推荐凑单商品',
                    'expected_impact': '客单价提升 5-12%',
                    'implementation_cost': '极低'
                },
                {
                    'strategy': '潜力客户识别与培育',
                    'description': '通过行为数据(浏览时长、收藏、加购)识别潜在高价值客户',
                    'expected_impact': '筛选出 5-10% 可提升的潜力客户',
                    'implementation_cost': '中低'
                }
            ],
            'cost_optimization': [
                {
                    'strategy': '自动化运营为主',
                    'description': '通过标准化流程和自动化工具进行维护，减少人工干预',
                    'expected_impact': '降低人工服务成本 60-80%',
                    'implementation_cost': '低'
                },
                {
                    'strategy': '自助服务引导',
                    'description': '引导使用在线客服、FAQ、智能助手，降低人工客服压力',
                    'expected_impact': '人工咨询量降低 40-60%',
                    'implementation_cost': '低'
                },
                {
                    'strategy': '批量营销触达',
                    'description': '参与大众化营销活动，不进行单独触达',
                    'expected_impact': '最小化营销投入',
                    'implementation_cost': '极低'
                }
            ],
            'potential_mining': [
                {
                    'strategy': '行为变化监测',
                    'description': '监测购买频次和金额的积极变化，及时升级服务',
                    'expected_impact': '识别可能升级的客户'
                },
                {
                    'strategy': '促销响应测试',
                    'description': '偶尔测试高价值优惠的响应情况，筛选潜力客户',
                    'expected_impact': '挖掘潜在价值客户'
                }
            ],
            'reactivation_strategy_for_churned': [
                {
                    'strategy': '低价值客户批量召回',
                    'description': '通过邮件、短信批量发送通用优惠券',
                    'expected_impact': f'预计召回率: {max(avg_reactivation*0.5, 0.02)*100:.1f}%',
                    'implementation_cost': '低'
                },
                {
                    'strategy': '高潜力流失客户召回',
                    'description': '对历史行为显示有潜力的流失客户进行定向召回',
                    'expected_impact': '针对高潜力客户召回率可达 15-25%',
                    'implementation_cost': '中低'
                }
            ],
            'communication_preferences': [
                '频次：每月1次或更少，仅大型促销活动',
                '渠道：仅批量邮件、APP推送',
                '内容：仅限大型促销活动通知、通用优惠券'
            ],
            'churn_policy': [
                '不主动进行一对一流失挽回',
                '自然流失后仅批量召回尝试',
                '服务资源优先向中高价值客群倾斜'
            ],
            'key_metrics_to_track': [
                '客户获取成本(CAC)',
                '服务成本',
                '低价值客户向中价值转化率',
                '营销投入回报率',
                '批量召回响应率'
            ],
            'estimated_budget_allocation': f'建议分配 5-10% 的客户营销预算'
        }
        
        return strategies
    
    def _generic_strategy(self, segment_name, profile, stats):
        return {
            'segment_name': segment_name,
            'strategy_type': '通用',
            'customer_count': profile.get('customer_count', 0),
            'avg_ltv': profile.get('avg_ltv', 0),
            'priority': '中等',
            'overall_goal': '根据客户特征制定针对性策略',
            'recommendations': [
                '深入分析该客群特征和行为模式',
                '测试不同营销策略的效果',
                '逐步优化运营策略'
            ]
        }
    
    def generate_reactivation_plan(self, ltv_data, segment_stats):
        churned = ltv_data[ltv_data['is_churned'] == True].copy()
        
        reactivation_plan = {
            'total_churned': len(churned),
            'churn_rate': len(churned) / len(ltv_data) * 100,
            'segment_breakdown': []
        }
        
        for _, row in segment_stats.iterrows():
            segment_name = row['segment_name']
            segment_id = row['segment']
            
            segment_churned = churned[churned['segment'] == segment_id]
            if len(segment_churned) > 0:
                reactivation_plan['segment_breakdown'].append({
                    'segment': segment_name,
                    'churned_count': len(segment_churned),
                    'avg_ltv': segment_churned['ltv'].mean(),
                    'avg_reactivation_prob': segment_churned['reactivation_prob'].mean(),
                    'potential_value': segment_churned['ltv'].sum() * segment_churned['reactivation_prob'].mean()
                })
        
        reactivation_plan['total_potential_value'] = sum(
            item['potential_value'] for item in reactivation_plan['segment_breakdown']
        )
        
        reactivation_plan['priority_list'] = sorted(
            reactivation_plan['segment_breakdown'],
            key=lambda x: x['potential_value'],
            reverse=True
        )
        
        return reactivation_plan
    
    def generate_churn_warning(self, ltv_data, threshold_days=90):
        at_risk = ltv_data[
            (ltv_data['probability_alive'] < 0.5) & 
            (ltv_data['ltv'] > ltv_data['ltv'].median())
        ]
        
        warning = {
            'at_risk_count': len(at_risk),
            'at_risk_percentage': len(at_risk) / len(ltv_data) * 100,
            'total_ltv_at_risk': at_risk['ltv'].sum(),
            'avg_ltv_at_risk': at_risk['ltv'].mean(),
            'at_risk_customers': at_risk[['customer_id', 'ltv', 'probability_alive']].to_dict('records'),
            'recommended_actions': [
                '立即启动流失挽回 campaign',
                '对高价值风险客户进行一对一关怀',
                '分析流失原因，优化产品和服务',
                '考虑推出专属挽留优惠'
            ]
        }
        
        return warning
    
    def generate_budget_allocation(self, segment_stats):
        total_customers = segment_stats['customer_count'].sum()
        total_ltv = (segment_stats['ltv_mean'] * segment_stats['customer_count']).sum()
        
        budget_rules = {
            '高价值客户': 0.50,
            '中高价值客户': 0.25,
            '中价值客户': 0.15,
            '中低价值客户': 0.07,
            '低价值客户': 0.03
        }
        
        budget_allocation = []
        for _, row in segment_stats.iterrows():
            segment_ltv = row['ltv_mean'] * row['customer_count']
            ltv_share = segment_ltv / total_ltv
            
            suggested_budget_pct = budget_rules.get(row['segment_name'], 0.05)
            
            budget_allocation.append({
                'segment': row['segment_name'],
                'strategy_type': self._get_strategy_type(row['segment_name']),
                'customer_count': row['customer_count'],
                'customer_share': row['customer_count'] / total_customers * 100,
                'ltv_share': ltv_share * 100,
                'suggested_budget_pct': suggested_budget_pct * 100,
                'expected_roi': ltv_share / suggested_budget_pct if suggested_budget_pct > 0 else 0
            })
        
        return budget_allocation
    
    def _get_strategy_type(self, segment_name):
        type_mapping = {
            '高价值客户': '维护',
            '中高价值客户': '维护+促活',
            '中价值客户': '促活',
            '中低价值客户': '促活+促转化',
            '低价值客户': '促转化'
        }
        return type_mapping.get(segment_name, '通用')
    
    def generate_action_plan(self, ltv_data, segment_stats, top_n=10):
        high_value = ltv_data[ltv_data['segment'] == segment_stats[segment_stats['segment_name'] == '高价值客户']['segment'].values[0]] if '高价值客户' in segment_stats['segment_name'].values else pd.DataFrame()
        medium_value = ltv_data[ltv_data['segment'] == segment_stats[segment_stats['segment_name'] == '中价值客户']['segment'].values[0]] if '中价值客户' in segment_stats['segment_name'].values else pd.DataFrame()
        low_value = ltv_data[ltv_data['segment'] == segment_stats[segment_stats['segment_name'] == '低价值客户']['segment'].values[0]] if '低价值客户' in segment_stats['segment_name'].values else pd.DataFrame()
        
        plan = {
            'immediate_actions': [
                {
                    'action': '高价值客户维护关怀',
                    'description': f'联系 Top {top_n} 高价值客户，进行满意度调研和专属服务介绍',
                    'target_customers': high_value.nlargest(top_n, 'ltv')['customer_id'].tolist() if len(high_value) > 0 else [],
                    'priority': '紧急',
                    'deadline': '1周内',
                    'strategy_type': '维护'
                },
                {
                    'action': '高价值流失风险预警',
                    'description': '对活跃度低于 0.3 的高价值客户启动挽回流程',
                    'target_customers': high_value[high_value['probability_alive'] < 0.3]['customer_id'].tolist() if len(high_value) > 0 else [],
                    'priority': '紧急',
                    'deadline': '3天内',
                    'strategy_type': '维护'
                },
                {
                    'action': '流失客户再激活',
                    'description': '对已流失的中高价值客户启动召回计划',
                    'target_customers': ltv_data[(ltv_data['is_churned'] == True) & (ltv_data['ltv'] > ltv_data['ltv'].median())]['customer_id'].tolist(),
                    'priority': '高',
                    'deadline': '1周内',
                    'strategy_type': '再激活'
                }
            ],
            'short_term_actions': [
                {
                    'action': '中价值客户促活活动',
                    'description': f'针对 Top {top_n * 2} 中价值客户推送购买频次提升活动',
                    'target_customers': medium_value.nlargest(top_n * 2, 'ltv')['customer_id'].tolist() if len(medium_value) > 0 else [],
                    'priority': '高',
                    'deadline': '2周内',
                    'strategy_type': '促活'
                },
                {
                    'action': '沉睡中价值客户唤醒',
                    'description': '对沉睡超过30天的中价值客户发送阶梯式优惠券',
                    'target_customers': medium_value[medium_value['recency'] > 30]['customer_id'].tolist() if 'recency' in medium_value.columns and len(medium_value) > 0 else [],
                    'priority': '中',
                    'deadline': '2周内',
                    'strategy_type': '促活'
                },
                {
                    'action': '低价值客户促转化',
                    'description': '对低价值客户推送高性价比产品和首单/复购激励',
                    'target_customers': low_value['customer_id'].tolist() if len(low_value) > 0 else [],
                    'priority': '中低',
                    'deadline': '1个月内',
                    'strategy_type': '促转化'
                }
            ],
            'long_term_strategies': [
                {
                    'action': '会员体系优化',
                    'description': '基于LTV分析结果优化会员等级和权益设置，强化维护-促活-促转化的分层运营体系',
                    'priority': '高',
                    'deadline': '3个月内',
                    'strategy_type': '系统优化'
                },
                {
                    'action': '再激活机制建设',
                    'description': '搭建流失客户召回机制，建立分客群的再激活策略和流程',
                    'priority': '高',
                    'deadline': '3个月内',
                    'strategy_type': '再激活'
                },
                {
                    'action': '营销自动化系统',
                    'description': '搭建基于LTV的自动化营销触达系统，实现维护-促活-促转化的自动化运营',
                    'priority': '中高',
                    'deadline': '3-6个月',
                    'strategy_type': '系统优化'
                },
                {
                    'action': '产品策略调整',
                    'description': '针对高价值客户偏好开发专属维护型产品，针对中低价值开发促活促转化型产品',
                    'priority': '中',
                    'deadline': '6个月内',
                    'strategy_type': '产品优化'
                }
            ]
        }
        
        return plan


if __name__ == '__main__':
    from data_generator import generate_customer_profiles, generate_transaction_history, generate_behavior_logs, prepare_model_data
    from bg_nbd_model import BGNBDModel
    from gamma_gamma_model import GammaGammaModel
    from ltv_analysis import LTVAnalyzer
    
    profiles = generate_customer_profiles(n_customers=500)
    transactions = generate_transaction_history(profiles)
    behavior_logs = generate_behavior_logs(profiles)
    model_data = prepare_model_data(profiles, transactions, behavior_logs)
    
    bg_nbd = BGNBDModel()
    bg_nbd.fit(model_data)
    
    gg = GammaGammaModel()
    gg.fit(model_data)
    
    analyzer = LTVAnalyzer(bg_nbd, gg)
    ltv_data = analyzer.calculate_ltv(model_data, future_months=12)
    ltv_data, segment_stats = analyzer.segment_customers(model_data, ltv_data, n_segments=4)
    
    engine = StrategyEngine()
    
    print("=== 各客群策略建议 ===\n")
    for idx, row in segment_stats.iterrows():
        profile = analyzer.get_segment_profile(model_data, ltv_data, row['segment'])
        strategy = engine.generate_segment_strategy(row['segment_name'], profile, row)
        print(f"【{strategy['segment_name']}】")
        print(f"客户数: {strategy['customer_count']}, 平均LTV: ¥{strategy['avg_ltv']:.2f}")
        print(f"优先级: {strategy['priority']}")
        print(f"目标: {strategy['overall_goal']}")
        print("---")
    
    churn_warning = engine.generate_churn_warning(ltv_data)
    print("\n=== 流失预警 ===")
    print(f"风险客户数: {churn_warning['at_risk_count']} ({churn_warning['at_risk_percentage']:.1f}%)")
    print(f"风险LTV总额: ¥{churn_warning['total_ltv_at_risk']:.2f}")
    
    budget = engine.generate_budget_allocation(segment_stats)
    print("\n=== 预算分配建议 ===")
    for b in budget:
        print(f"{b['segment']}: 建议分配 {b['suggested_budget_pct']:.1f}% 预算 (预计ROI: {b['expected_roi']:.2f})")
