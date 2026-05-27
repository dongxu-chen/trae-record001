import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime


ACTION_CATEGORIES = {
    'turn_off': '关闭电源',
    'replace': '更换节能设备',
    'shift_usage': '错峰使用',
    'optimize_setting': '优化设置',
    'maintenance': '维护保养',
    'habit_change': '习惯养成'
}


APPLIANCE_SAVE_TIPS = {
    'air_conditioner': {
        'name_cn': '空调',
        'baseline_kwh_per_hour': 1.5,
        'tips': [
            {
                'category': 'optimize_setting',
                'action': '将空调设定温度从当前值提高1-2℃',
                'steps': [
                    '使用遥控器将制冷温度调高至26℃以上',
                    '开启睡眠模式，夜间自动升高温度',
                    '使用ECO节能模式运行'
                ],
                'condition': lambda data: data.get('on_ratio', 0) > 0.5,
                'saving_potential': 0.12,
                'priority': 'high'
            },
            {
                'category': 'shift_usage',
                'action': '将空调使用时间从18:00-22:00调整到其他时段',
                'steps': [
                    '下午14:00-16:00提前开启预冷房间',
                    '晚上22:00后降低制冷强度',
                    '利用凌晨低温时段通风降温'
                ],
                'condition': lambda data: len(data.get('peak_usage_hours', [])) > 0 and \
                                         any(18 <= h <= 22 for h in data.get('peak_usage_hours', [])),
                'saving_potential': 0.15,
                'priority': 'high'
            },
            {
                'category': 'maintenance',
                'action': '清洁空调滤网和室外机',
                'steps': [
                    '打开空调面板，取出滤网',
                    '用清水冲洗滤网灰尘，晾干后装回',
                    '清理室外机周围杂物，保持通风'
                ],
                'condition': lambda data: data.get('on_ratio', 0) > 0.3,
                'saving_potential': 0.15,
                'priority': 'medium'
            },
            {
                'category': 'turn_off',
                'action': '离家时关闭空调电源',
                'steps': [
                    '出门前15分钟提前关闭空调',
                    '关闭后拔下插头或关闭插排开关',
                    '长时间外出时断开总电源'
                ],
                'condition': lambda data: True,
                'saving_potential': 0.08,
                'priority': 'low'
            }
        ]
    },
    'refrigerator': {
        'name_cn': '冰箱',
        'baseline_kwh_per_hour': 0.1,
        'tips': [
            {
                'category': 'maintenance',
                'action': '检查并更换冰箱门封条',
                'steps': [
                    '将一张A4纸夹在门缝中，拉动检查阻力',
                    '如阻力小说明密封不良，需要更换',
                    '用酒精擦拭门封条保持清洁弹性'
                ],
                'condition': lambda data: data.get('on_ratio', 0) > 0.5,
                'saving_potential': 0.12,
                'priority': 'high'
            },
            {
                'category': 'optimize_setting',
                'action': '调整冰箱温度档位',
                'steps': [
                    '冷藏室设置为4-8℃，冷冻室设置为-15~-18℃',
                    '冬季调高档位（数字调小），夏季调低档位（数字调大）',
                    '根据存放食物量适当调整'
                ],
                'condition': lambda data: data.get('on_ratio', 0) > 0.4,
                'saving_potential': 0.10,
                'priority': 'medium'
            },
            {
                'category': 'habit_change',
                'action': '减少冰箱开门次数',
                'steps': [
                    '计划好要取的食物，一次性取出',
                    '取放食物后立即关门',
                    '将常用食物放在容易取的位置'
                ],
                'condition': lambda data: True,
                'saving_potential': 0.06,
                'priority': 'low'
            }
        ]
    },
    'washing_machine': {
        'name_cn': '洗衣机',
        'baseline_kwh_per_hour': 0.5,
        'tips': [
            {
                'category': 'shift_usage',
                'action': '将洗衣时间调整到夜间低谷时段',
                'steps': [
                    '使用预约功能设定22:00后启动',
                    '集中在周末白天或早晨洗衣',
                    '避开18:00-22:00用电高峰'
                ],
                'condition': lambda data: len(data.get('peak_usage_hours', [])) > 0 and \
                                         any(18 <= h <= 22 for h in data.get('peak_usage_hours', [])),
                'saving_potential': 0.15,
                'priority': 'high'
            },
            {
                'category': 'optimize_setting',
                'action': '选择节能洗衣程序',
                'steps': [
                    '衣物少时使用快速洗程序',
                    '使用冷水洗涤（除非特别脏）',
                    '选择合适水位，避免过量用水'
                ],
                'condition': lambda data: data.get('usage_frequency_per_day', 0) > 0.5,
                'saving_potential': 0.10,
                'priority': 'medium'
            },
            {
                'category': 'habit_change',
                'action': '集中洗涤，减少开机次数',
                'steps': [
                    '积攒足够衣物后一次洗涤',
                    '避免少量衣物单独洗涤',
                    '利用洗衣机的最大容量'
                ],
                'condition': lambda data: data.get('usage_frequency_per_day', 0) > 1,
                'saving_potential': 0.18,
                'priority': 'high'
            }
        ]
    },
    'lighting': {
        'name_cn': '照明',
        'baseline_kwh_per_hour': 0.1,
        'tips': [
            {
                'category': 'replace',
                'action': '将传统灯具更换为LED灯具',
                'steps': [
                    '购买相同接口的LED灯泡（推荐10W以下）',
                    '关闭电源后拆下旧灯泡',
                    '安装LED灯泡，注意功率匹配'
                ],
                'condition': lambda data: data.get('on_ratio', 0) > 0.3,
                'saving_potential': 0.75,
                'priority': 'high'
            },
            {
                'category': 'turn_off',
                'action': '养成随手关灯习惯',
                'steps': [
                    '离开房间立即关灯',
                    '白天充分利用自然光',
                    '使用感应灯或定时开关控制'
                ],
                'condition': lambda data: data.get('on_ratio', 0) > 0.2,
                'saving_potential': 0.15,
                'priority': 'medium'
            },
            {
                'category': 'optimize_setting',
                'action': '优化照明布局和亮度',
                'steps': [
                    '采用局部照明替代全屋照明',
                    '使用台灯/落地灯满足阅读需求',
                    '安装调光器，按需调节亮度'
                ],
                'condition': lambda data: True,
                'saving_potential': 0.10,
                'priority': 'low'
            }
        ]
    }
}


class EnergySavingAdvisor:
    def __init__(self, electricity_price: float = 0.6):
        self.electricity_price = electricity_price
    
    def generate_appliance_tips(self, 
                                appliance: str,
                                usage_data: Dict,
                                energy_data: Dict) -> List[Dict]:
        if appliance not in APPLIANCE_SAVE_TIPS:
            return []
        
        appliance_config = APPLIANCE_SAVE_TIPS[appliance]
        tips = []
        
        combined_data = {**usage_data, **energy_data}
        
        for tip_config in appliance_config['tips']:
            if tip_config['condition'](combined_data):
                total_kwh = energy_data.get('total_kwh', 0)
                estimated_saving_kwh = total_kwh * tip_config['saving_potential']
                estimated_saving_money = estimated_saving_kwh * self.electricity_price
                
                tips.append({
                    'appliance': appliance,
                    'appliance_name': appliance_config['name_cn'],
                    'category': tip_config['category'],
                    'category_name': ACTION_CATEGORIES.get(tip_config['category'], tip_config['category']),
                    'action': tip_config['action'],
                    'steps': tip_config['steps'],
                    'saving_potential': tip_config['saving_potential'],
                    'estimated_saving_kwh': round(estimated_saving_kwh, 2),
                    'estimated_saving_money': round(estimated_saving_money, 2),
                    'priority': tip_config['priority']
                })
        
        return tips
    
    def generate_all_tips(self,
                          energy_report: Dict,
                          max_tips_per_appliance: int = 3) -> Dict:
        all_tips = []
        total_saving_kwh = 0
        total_saving_money = 0
        
        energy_analysis = energy_report.get('energy_analysis', {})
        usage_habits = energy_report.get('usage_habits', {})
        
        for appliance in energy_analysis.keys():
            if appliance in usage_habits:
                appliance_tips = self.generate_appliance_tips(
                    appliance,
                    usage_habits[appliance],
                    energy_analysis[appliance]
                )
                
                appliance_tips = sorted(
                    appliance_tips,
                    key=lambda x: (x['priority'] == 'high', x['priority'] == 'medium'),
                    reverse=True
                )[:max_tips_per_appliance]
                
                all_tips.extend(appliance_tips)
        
        for tip in all_tips:
            total_saving_kwh += tip['estimated_saving_kwh']
            total_saving_money += tip['estimated_saving_money']
        
        general_tips = self._generate_general_tips(energy_report)
        
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        all_tips = sorted(all_tips, key=lambda x: priority_order[x['priority']])
        
        return {
            'appliance_tips': all_tips,
            'general_tips': general_tips,
            'summary': {
                'total_tips_count': len(all_tips) + len(general_tips),
                'estimated_monthly_saving_kwh': round(total_saving_kwh, 2),
                'estimated_monthly_saving_money': round(total_saving_money, 2),
                'estimated_yearly_saving_kwh': round(total_saving_kwh * 12, 2),
                'estimated_yearly_saving_money': round(total_saving_money * 12, 2)
            }
        }
    
    def _generate_general_tips(self, energy_report: Dict) -> List[Dict]:
        tips = []
        daily_pattern = energy_report.get('daily_pattern', {})
        weekly_pattern = energy_report.get('weekly_pattern', {})
        
        peak_hours = daily_pattern.get('peak_hours', [])
        if any(18 <= h <= 22 for h in peak_hours):
            tips.append({
                'category': 'shift_usage',
                'category_name': '错峰使用',
                'action': '将高耗电设备使用时间调整到非高峰时段',
                'steps': [
                    '电热水器、电水壶等可在早晨或夜间使用',
                    '电动车充电安排在22:00后进行',
                    '使用智能插座设定设备启停时间'
                ],
                'saving_potential': 0.10,
                'priority': 'medium'
            })
        
        weekend_ratio = weekly_pattern.get('weekend_weekday_ratio', 1)
        if weekend_ratio > 1.3:
            tips.append({
                'category': 'turn_off',
                'category_name': '关闭电源',
                'action': '周末离家前检查并关闭电器',
                'steps': [
                    '关闭空调、电视等大功率电器',
                    '拔掉充电器、小家电等插头',
                    '关闭饮水机、空气净化器等非必要设备'
                ],
                'saving_potential': 0.08,
                'priority': 'low'
            })
        
        energy_analysis = energy_report.get('energy_analysis', {})
        ac_ratio = energy_analysis.get('air_conditioner', {}).get('energy_ratio', 0)
        if ac_ratio > 0.5:
            tips.append({
                'category': 'replace',
                'category_name': '更换节能设备',
                'action': '安装智能温控系统',
                'steps': [
                    '购买智能温控器或空调伴侣',
                    '设置温度范围和定时开关',
                    '连接手机APP远程控制'
                ],
                'saving_potential': 0.15,
                'priority': 'high'
            })
        
        tips.append({
            'category': 'turn_off',
            'category_name': '关闭电源',
            'action': '消除待机耗电',
            'steps': [
                '使用带独立开关的插排',
                '关闭电视、机顶盒等设备的总电源',
                '不充电时拔掉充电器插头'
            ],
            'saving_potential': 0.05,
            'priority': 'low'
        })
        
        return tips
    
    def get_energy_grade(self, total_energy_kwh: float, days: int) -> Dict:
        daily_energy = total_energy_kwh / max(days, 1)
        monthly_energy = daily_energy * 30
        
        if monthly_energy < 150:
            grade = 'A+'
            description = '非常节能，继续保持！'
            color = 'green'
        elif monthly_energy < 250:
            grade = 'A'
            description = '节能表现良好'
            color = 'lightgreen'
        elif monthly_energy < 350:
            grade = 'B'
            description = '正常水平，有优化空间'
            color = 'yellow'
        elif monthly_energy < 450:
            grade = 'C'
            description = '能耗偏高，建议采取节能措施'
            color = 'orange'
        else:
            grade = 'D'
            description = '能耗较高，急需节能改造'
            color = 'red'
        
        return {
            'grade': grade,
            'description': description,
            'color': color,
            'monthly_estimate': round(monthly_energy, 2)
        }


if __name__ == '__main__':
    from data_generator import generate_aggregated_data
    from energy_analyzer import EnergyAnalyzer
    
    print("Generating test data...")
    df = generate_aggregated_data(days=7, sample_interval_min=5)
    
    disaggregated_data = {
        'air_conditioner': df['air_conditioner_power'].values,
        'refrigerator': df['refrigerator_power'].values,
        'washing_machine': df['washing_machine_power'].values,
        'lighting': df['lighting_power'].values
    }
    
    analyzer = EnergyAnalyzer(sample_interval_min=5)
    report = analyzer.generate_comprehensive_report(disaggregated_data, df.index)
    
    advisor = EnergySavingAdvisor(electricity_price=0.6)
    
    print("\nGenerating energy saving tips...")
    tips_result = advisor.generate_all_tips(report)
    
    print(f"\nTotal tips: {tips_result['summary']['total_tips_count']}")
    print(f"Estimated monthly saving: {tips_result['summary']['estimated_monthly_saving_kwh']} kWh")
    print(f"Estimated monthly saving money: {tips_result['summary']['estimated_monthly_saving_money']} 元")
    
    print("\nAppliance tips:")
    for tip in tips_result['appliance_tips'][:5]:
        print(f"\n  [{tip['priority']}] {tip['appliance_name']}:")
        print(f"    {tip['tip']}")
        print(f"    可节省: {tip['estimated_saving_kwh']} kWh ({tip['estimated_saving_money']} 元)")
    
    print("\nGeneral tips:")
    for tip in tips_result['general_tips']:
        print(f"\n  [{tip['priority']}] {tip['tip']}")
    
    grade = advisor.get_energy_grade(
        report['summary']['total_energy_kwh'],
        report['summary']['analysis_period_days']
    )
    print(f"\nEnergy grade: {grade['grade']} - {grade['description']}")
