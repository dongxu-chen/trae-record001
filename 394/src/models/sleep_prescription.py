import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict


class SleepPrescriptionGenerator:
    def __init__(self):
        self.aasm_standards = {
            'sleep_efficiency_min': 85.0,
            'sleep_efficiency_optimal': 90.0,
            'sleep_latency_max': 20.0,
            'waso_max_pct': 10.0,
            'n3_min_pct': 13.0,
            'n3_max_pct': 23.0,
            'rem_min_pct': 20.0,
            'rem_max_pct': 25.0,
            'total_sleep_min': 7.0,
            'total_sleep_max': 9.0,
            'arousal_index_max': 5.0,
        }

    def generate_prescription(self, sleep_score, stage_analysis, regularity_analysis,
                              lifestyle_factors, history_factors=None):
        prescription = {
            'summary': self._generate_summary(sleep_score, stage_analysis),
            'schedule_adjustment': self._generate_schedule_adjustment(stage_analysis, lifestyle_factors),
            'lifestyle_prescription': self._generate_lifestyle_prescription(lifestyle_factors, history_factors),
            'environment_prescription': self._generate_environment_prescription(),
            'pre_sleep_routine': self._generate_pre_sleep_routine(stage_analysis),
            'exercise_prescription': self._generate_exercise_prescription(lifestyle_factors, history_factors),
            'weekly_plan': self._generate_weekly_plan(sleep_score, stage_analysis),
            'expected_improvement': self._calculate_expected_improvement(sleep_score, stage_analysis)
        }
        return prescription

    def _generate_summary(self, sleep_score, stage_analysis):
        score = sleep_score['total_score']
        grade = sleep_score['grade']
        issues = []
        if stage_analysis['sleep_efficiency'] < self.aasm_standards['sleep_efficiency_min']:
            issues.append('睡眠效率偏低')
        if stage_analysis['stage_distribution']['深睡']['percentage'] < self.aasm_standards['n3_min_pct']:
            issues.append('深睡不足')
        if stage_analysis['stage_distribution']['REM']['percentage'] < self.aasm_standards['rem_min_pct']:
            issues.append('REM睡眠不足')
        if stage_analysis['total_sleep_duration'] < self.aasm_standards['total_sleep_min']:
            issues.append('总睡眠时长不足')
        if stage_analysis['sleep_latency'] > self.aasm_standards['sleep_latency_max']:
            issues.append('入睡困难')
        if stage_analysis['waso_pct'] > self.aasm_standards['waso_max_pct']:
            issues.append('夜间易醒')

        issue_text = '、'.join(issues) if issues else '各项指标良好'
        return {
            'current_score': score,
            'current_grade': grade,
            'primary_issues': issues,
            'summary_text': f'当前睡眠评分{score:.1f}分（{grade}），主要问题：{issue_text}。'
        }

    def _generate_schedule_adjustment(self, stage_analysis, lifestyle_factors):
        target_sleep_hours = 8.0
        current_duration = stage_analysis['total_sleep_duration']
        current_bedtime = lifestyle_factors.get('bedtime_hour', 23.0)

        adjustments = []
        new_bedtime = current_bedtime
        new_wakeup = current_bedtime + target_sleep_hours

        if current_duration < 7.0:
            new_bedtime = max(21.0, current_bedtime - 1.0)
            adjustments.append({
                'type': 'bedtime',
                'action': '提前入睡',
                'change': '-1小时',
                'target': f'{int(new_bedtime)}:{int((new_bedtime%1)*60):02d}',
                'reason': '当前睡眠时长不足，需要增加卧床时间'
            })
        elif current_duration > 9.5:
            new_bedtime = min(24.0, current_bedtime + 0.5)
            adjustments.append({
                'type': 'bedtime',
                'action': '推迟入睡',
                'change': '+30分钟',
                'target': f'{int(new_bedtime%24)}:{int((new_bedtime%1)*60):02d}',
                'reason': '睡眠时间过长可能导致睡眠片段化'
            })

        if stage_analysis['sleep_latency'] > 30:
            adjustments.append({
                'type': 'wind_down',
                'action': '增加放松时间',
                'change': '+30分钟',
                'target': '睡前1小时开始放松',
                'reason': '入睡潜伏期过长，需要更长的睡前准备'
            })

        new_wakeup = new_bedtime + target_sleep_hours
        ideal_bedtime_range = (22.0, 23.5)
        if current_bedtime < ideal_bedtime_range[0]:
            schedule_grade = '过早'
        elif current_bedtime > ideal_bedtime_range[1]:
            schedule_grade = '过晚'
        else:
            schedule_grade = '理想'

        return {
            'current_bedtime': current_bedtime,
            'recommended_bedtime': new_bedtime,
            'recommended_wakeup': new_wakeup % 24,
            'target_sleep_duration': target_sleep_hours,
            'schedule_grade': schedule_grade,
            'adjustments': adjustments,
            'bedtime_text': f'建议入睡时间：{int(new_bedtime)}:{int((new_bedtime%1)*60):02d}',
            'wakeup_text': f'建议起床时间：{int(new_wakeup%24)}:{int((new_wakeup%1)*60):02d}'
        }

    def _generate_lifestyle_prescription(self, lifestyle_factors, history_factors=None):
        prescriptions = []
        caffeine = lifestyle_factors.get('caffeine_intake', 0)
        alcohol = lifestyle_factors.get('alcohol_intake', 0)
        stress = lifestyle_factors.get('stress_level', 5)

        if caffeine >= 2:
            prescriptions.append({
                'category': '咖啡因',
                'priority': 'high',
                'action': '减少咖啡因摄入',
                'specific': f'将每日咖啡因从{caffeine}份减少至1份以内',
                'deadline': '下午2点后完全避免',
                'benefit': '预计可改善入睡时间和深睡质量'
            })
        elif caffeine == 1:
            prescriptions.append({
                'category': '咖啡因',
                'priority': 'medium',
                'action': '调整摄入时间',
                'specific': '仅上午摄入咖啡因',
                'deadline': '下午2点后完全避免',
                'benefit': '避免影响夜间睡眠'
            })

        if alcohol >= 1:
            prescriptions.append({
                'category': '酒精',
                'priority': 'high',
                'action': '减少或戒酒',
                'specific': f'将每日饮酒从{alcohol}杯减少至0杯',
                'deadline': '睡前4小时完全避免',
                'benefit': '显著改善REM睡眠和睡眠连续性'
            })

        if stress >= 7:
            prescriptions.append({
                'category': '压力管理',
                'priority': 'high',
                'action': '每日放松练习',
                'specific': '每天进行15-20分钟冥想或深呼吸练习',
                'schedule': '睡前30分钟进行',
                'benefit': '降低皮质醇水平，改善睡眠质量'
            })
        elif stress >= 5:
            prescriptions.append({
                'category': '压力管理',
                'priority': 'medium',
                'action': '轻度放松',
                'specific': '每天进行10分钟正念呼吸',
                'schedule': '睡前20分钟进行',
                'benefit': '帮助身心放松，促进入睡'
            })

        return prescriptions

    def _generate_environment_prescription(self):
        return [
            {
                'aspect': '温度',
                'recommendation': '保持卧室温度18-20°C',
                'evidence': 'AASM研究显示此温度范围最利于深睡',
                'priority': 'high'
            },
            {
                'aspect': '光线',
                'recommendation': '使用遮光窗帘，睡前1小时调暗灯光',
                'evidence': '黑暗促进褪黑素分泌',
                'priority': 'high'
            },
            {
                'aspect': '噪音',
                'recommendation': '保持环境安静，必要时使用白噪音机',
                'evidence': '噪音是睡眠中断的主要原因之一',
                'priority': 'medium'
            },
            {
                'aspect': '电子设备',
                'recommendation': '睡前30分钟停止使用电子设备',
                'evidence': '蓝光抑制褪黑素分泌',
                'priority': 'high'
            },
            {
                'aspect': '床品',
                'recommendation': '选择中等硬度床垫和透气枕头',
                'evidence': '舒适的床品减少夜间翻身',
                'priority': 'medium'
            }
        ]

    def _generate_pre_sleep_routine(self, stage_analysis):
        routine = []
        if stage_analysis['sleep_latency'] > 20:
            prep_time = 60
        else:
            prep_time = 30

        routine.append({
            'time': f'睡前{prep_time}分钟',
            'activity': '停止工作和电子设备使用',
            'duration': f'{prep_time}分钟'
        })
        routine.append({
            'time': '睡前30分钟',
            'activity': '温水泡脚或温水澡',
            'duration': '10-15分钟'
        })
        routine.append({
            'time': '睡前20分钟',
            'activity': '阅读纸质书或听轻音乐',
            'duration': '15分钟'
        })
        routine.append({
            'time': '睡前10分钟',
            'activity': '深呼吸或渐进性肌肉放松',
            'duration': '10分钟'
        })

        return {
            'prep_duration': prep_time,
            'routine_steps': routine,
            'avoid_activities': ['剧烈运动', '争论', '看恐怖片', '吃太饱']
        }

    def _generate_exercise_prescription(self, lifestyle_factors, history_factors=None):
        exercise_min = lifestyle_factors.get('exercise_minutes', 0)
        intensity = lifestyle_factors.get('exercise_intensity', 'moderate')

        prescriptions = []
        if exercise_min < 30:
            prescriptions.append({
                'type': '有氧训练',
                'recommendation': '每日中等强度有氧运动30分钟',
                'examples': ['快走', '慢跑', '游泳', '骑行'],
                'best_time': '上午或下午',
                'avoid_time': '睡前3小时内'
            })
        elif exercise_min > 120:
            prescriptions.append({
                'type': '运动调整',
                'recommendation': '减少运动量至每日60-90分钟',
                'warning': '过量运动可能导致疲劳和睡眠质量下降',
                'recovery': '确保充足的恢复时间'
            })

        if history_factors:
            d1 = history_factors.get('exercise_minutes_1d', 0)
            d2 = history_factors.get('exercise_minutes_2d', 0)
            d3 = history_factors.get('exercise_minutes_3d', 0)
            consistency = 1 - np.std([exercise_min, d1, d2, d3]) / (np.mean([exercise_min, d1, d2, d3]) + 1)
            if consistency < 0.5:
                prescriptions.append({
                    'type': '规律运动',
                    'recommendation': '保持每日规律运动',
                    'target': '每天固定时间运动30-45分钟',
                    'benefit': '运动的规律性比单次时长更重要'
                })

        prescriptions.append({
            'type': '放松运动',
            'recommendation': '睡前可进行轻度拉伸或瑜伽',
            'examples': ['猫牛式', '儿童式', '腿上墙式'],
            'duration': '10-15分钟'
        })

        return prescriptions

    def _generate_weekly_plan(self, sleep_score, stage_analysis):
        score = sleep_score['total_score']
        if score >= 80:
            phase = '维持期'
        elif score >= 60:
            phase = '改善期'
        else:
            phase = '强化期'

        weekly_goals = []
        if phase == '强化期':
            weekly_goals = [
                {'day': '第1-2天', 'goal': '建立规律作息，固定入睡起床时间', 'focus': '作息规律'},
                {'day': '第3-4天', 'goal': '优化睡眠环境，减少咖啡因', 'focus': '环境+饮食'},
                {'day': '第5-6天', 'goal': '增加日间运动，建立睡前仪式', 'focus': '运动+放松'},
                {'day': '第7天', 'goal': '回顾调整，巩固良好习惯', 'focus': '总结巩固'}
            ]
        elif phase == '改善期':
            weekly_goals = [
                {'day': '第1-3天', 'goal': '优化入睡时间和睡前习惯', 'focus': '作息调整'},
                {'day': '第4-5天', 'goal': '增加日间光照和运动', 'focus': '生物节律'},
                {'day': '第6-7天', 'goal': '巩固改善，评估效果', 'focus': '巩固评估'}
            ]
        else:
            weekly_goals = [
                {'day': '全周', 'goal': '维持现有良好睡眠习惯', 'focus': '持续保持'}
            ]

        return {
            'phase': phase,
            'weekly_goals': weekly_goals,
            'expected_duration': f'预计{4 if phase == "强化期" else 2 if phase == "改善期" else 1}周可见明显改善'
        }

    def _calculate_expected_improvement(self, sleep_score, stage_analysis):
        current_score = sleep_score['total_score']
        potential_gain = 0
        factors = []

        if stage_analysis['sleep_efficiency'] < 85:
            gain = min(10, (85 - stage_analysis['sleep_efficiency']) * 0.5)
            potential_gain += gain
            factors.append({'factor': '睡眠效率', 'potential_gain': gain})

        if stage_analysis['stage_distribution']['深睡']['percentage'] < 13:
            gain = min(8, (13 - stage_analysis['stage_distribution']['深睡']['percentage']) * 0.8)
            potential_gain += gain
            factors.append({'factor': '深睡时长', 'potential_gain': gain})

        if stage_analysis['stage_distribution']['REM']['percentage'] < 20:
            gain = min(6, (20 - stage_analysis['stage_distribution']['REM']['percentage']) * 0.5)
            potential_gain += gain
            factors.append({'factor': 'REM睡眠', 'potential_gain': gain})

        if stage_analysis['sleep_latency'] > 20:
            gain = min(5, (stage_analysis['sleep_latency'] - 20) * 0.2)
            potential_gain += gain
            factors.append({'factor': '入睡速度', 'potential_gain': gain})

        if stage_analysis['waso_pct'] > 10:
            gain = min(6, (stage_analysis['waso_pct'] - 10) * 0.3)
            potential_gain += gain
            factors.append({'factor': '睡眠连续性', 'potential_gain': gain})

        return {
            'current_score': current_score,
            'potential_score': min(100, current_score + potential_gain),
            'potential_gain': potential_gain,
            'factor_breakdown': factors,
            'timeframe': '坚持执行处方2-4周可见显著改善'
        }


class CircadianRhythmAnalyzer:
    def __init__(self):
        self.chronotype_reference = {
            'early_bird': {'bedtime': (21.5, 22.5), 'wakeup': (5.5, 6.5), 'label': '百灵鸟型'},
            'intermediate': {'bedtime': (22.5, 23.5), 'wakeup': (6.5, 7.5), 'label': '中间型'},
            'night_owl': {'bedtime': (23.5, 1.5), 'wakeup': (7.5, 9.5), 'label': '猫头鹰型'}
        }
        self.circadian_phases = [
            {'phase': '深度睡眠期', 'time_range': (0, 3), 'description': '生长激素分泌高峰，身体修复'},
            {'phase': 'REM睡眠期', 'time_range': (3, 6), 'description': '梦境活跃，记忆巩固'},
            {'phase': '浅睡过渡期', 'time_range': (6, 8), 'description': '易醒，皮质醇上升'},
            {'phase': '清醒活跃期', 'time_range': (8, 12), 'description': '认知能力高峰'},
            {'phase': '午后低迷期', 'time_range': (12, 15), 'description': '体温下降，适合小憩'},
            {'phase': '傍晚活跃期', 'time_range': (15, 20), 'description': '运动表现最佳'},
            {'phase': '褪黑素分泌期', 'time_range': (20, 22), 'description': '开始感到困倦'},
            {'phase': '睡眠准备期', 'time_range': (22, 24), 'description': '放松准备入睡'}
        ]

    def predict_circadian_type(self, sleep_stages, bedtime_hour=23.0, wakeup_hour=7.0, history_factors=None):
        sleep_duration = wakeup_hour - bedtime_hour if wakeup_hour > bedtime_hour else wakeup_hour + 24 - bedtime_hour
        avg_hr_night = 65
        if history_factors:
            avg_sleep_dur = np.mean([
                history_factors.get('sleep_duration_1d', 7.5),
                history_factors.get('sleep_duration_2d', 7.5),
                history_factors.get('sleep_duration_3d', 7.5)
            ])
            avg_bedtime = np.mean([
                history_factors.get('bedtime_hour_1d', 23.0),
                history_factors.get('bedtime_hour_2d', 23.0),
                history_factors.get('bedtime_hour_3d', 23.0)
            ])
            bedtime_hour = avg_bedtime

        if bedtime_hour <= 22.5:
            chronotype = 'early_bird'
        elif bedtime_hour <= 23.5:
            chronotype = 'intermediate'
        else:
            chronotype = 'night_owl'

        chronotype_info = self.chronotype_reference[chronotype]
        optimal_bedtime = np.mean(chronotype_info['bedtime'])
        optimal_wakeup = np.mean(chronotype_info['wakeup'])
        optimal_sleep_duration = optimal_wakeup - optimal_bedtime if optimal_wakeup > optimal_bedtime else optimal_wakeup + 24 - optimal_bedtime

        melatonin_start = max(20, bedtime_hour - 3)
        melatonin_peak = bedtime_hour - 1
        cortisol_rise = wakeup_hour - 1
        core_body_temp_min = bedtime_hour + 2
        best_exercise_time = 16.5
        best_cognitive_time = 10.0

        bed_delay = bedtime_hour - optimal_bedtime
        alignment_score = max(0, 100 - abs(bed_delay) * 20)

        return {
            'chronotype': chronotype,
            'chronotype_label': chronotype_info['label'],
            'chronotype_description': self._get_chronotype_description(chronotype),
            'optimal_bedtime': optimal_bedtime,
            'optimal_wakeup': optimal_wakeup,
            'optimal_sleep_duration': optimal_sleep_duration,
            'current_bedtime': bedtime_hour,
            'current_wakeup': wakeup_hour,
            'alignment_score': alignment_score,
            'biological_markers': {
                'melatonin_start': melatonin_start,
                'melatonin_peak': melatonin_peak,
                'cortisol_rise': cortisol_rise,
                'core_body_temp_min': core_body_temp_min,
                'best_exercise_time': best_exercise_time,
                'best_cognitive_time': best_cognitive_time
            },
            'optimal_schedule': self._generate_optimal_schedule(chronotype),
            'adjustment_recommendation': self._generate_circadian_adjustment(bedtime_hour, chronotype)
        }

    def _get_chronotype_description(self, chronotype):
        descriptions = {
            'early_bird': '您属于"百灵鸟型"，早睡早起，早晨精力充沛，下午较早感到疲劳。',
            'intermediate': '您属于"中间型"，作息较为灵活，适应能力较强。',
            'night_owl': '您属于"猫头鹰型"，晚睡晚起，晚上精力旺盛，早晨较难起床。'
        }
        return descriptions[chronotype]

    def _generate_optimal_schedule(self, chronotype):
        schedules = {
            'early_bird': [
                {'time': '05:30', 'activity': '自然醒来，沐浴晨光', 'phase': '皮质醇上升'},
                {'time': '06:00', 'activity': '轻度运动或冥想', 'phase': '最佳运动期'},
                {'time': '07:00', 'activity': '营养早餐', 'phase': '代谢高峰'},
                {'time': '10:00', 'activity': '处理复杂工作', 'phase': '认知高峰'},
                {'time': '12:30', 'activity': '午餐', 'phase': ''},
                {'time': '13:00', 'activity': '15-20分钟小憩', 'phase': '午后低迷'},
                {'time': '17:00', 'activity': '适度运动', 'phase': ''},
                {'time': '19:00', 'activity': '晚餐', 'phase': ''},
                {'time': '21:00', 'activity': '放松准备', 'phase': '褪黑素开始分泌'},
                {'time': '22:00', 'activity': '入睡', 'phase': '最佳入睡窗口'}
            ],
            'intermediate': [
                {'time': '06:30', 'activity': '自然醒来，沐浴晨光', 'phase': '皮质醇上升'},
                {'time': '07:00', 'activity': '轻度运动', 'phase': ''},
                {'time': '07:30', 'activity': '营养早餐', 'phase': '代谢高峰'},
                {'time': '10:30', 'activity': '处理复杂工作', 'phase': '认知高峰'},
                {'time': '12:30', 'activity': '午餐', 'phase': ''},
                {'time': '13:30', 'activity': '15分钟小憩', 'phase': '午后低迷'},
                {'time': '18:00', 'activity': '适度运动', 'phase': '最佳运动期'},
                {'time': '19:30', 'activity': '晚餐', 'phase': ''},
                {'time': '22:00', 'activity': '放松准备', 'phase': '褪黑素开始分泌'},
                {'time': '23:00', 'activity': '入睡', 'phase': '最佳入睡窗口'}
            ],
            'night_owl': [
                {'time': '08:00', 'activity': '慢慢醒来，避免立即起床', 'phase': '皮质醇缓慢上升'},
                {'time': '08:30', 'activity': '沐浴晨光+轻度拉伸', 'phase': ''},
                {'time': '09:00', 'activity': '营养早餐', 'phase': '代谢启动'},
                {'time': '11:00', 'activity': '处理复杂工作', 'phase': '认知高峰'},
                {'time': '13:00', 'activity': '午餐', 'phase': ''},
                {'time': '14:00', 'activity': '20分钟小憩', 'phase': '午后低迷'},
                {'time': '19:00', 'activity': '适度运动', 'phase': '最佳运动期'},
                {'time': '20:30', 'activity': '晚餐', 'phase': ''},
                {'time': '22:30', 'activity': '放松准备', 'phase': '褪黑素开始分泌'},
                {'time': '24:00', 'activity': '入睡', 'phase': '最佳入睡窗口'}
            ]
        }
        return schedules[chronotype]

    def _generate_circadian_adjustment(self, current_bedtime, chronotype):
        target = self.chronotype_reference[chronotype]['bedtime'][0]
        diff = current_bedtime - target

        if abs(diff) < 0.5:
            return {
                'status': '已对齐',
                'recommendation': '您的作息与生物钟基本一致，继续保持！',
                'adjustment_minutes': 0
            }

        direction = '提前' if diff > 0 else '推迟'
        minutes = abs(diff) * 60
        return {
            'status': '需要调整',
            'direction': direction,
            'adjustment_minutes': int(minutes),
            'recommendation': f'建议将入睡时间{direction}{int(minutes)}分钟，以与您的生物钟节律对齐。可每天{direction}15分钟，逐步调整。',
            'steps': [
                f'第1周：每天{direction}15分钟',
                f'第2周：再{direction}15分钟',
                '第3-4周：巩固新的作息时间'
            ]
        }

    def get_current_phase(self, current_hour=None):
        if current_hour is None:
            current_hour = datetime.now().hour + datetime.now().minute / 60

        for phase in self.circadian_phases:
            start, end = phase['time_range']
            if start <= current_hour < end or (start > end and (current_hour >= start or current_hour < end)):
                return phase
        return self.circadian_phases[-1]


class AgeGroupComparator:
    def __init__(self):
        self.age_group_norms = {
            '18-25': {
                'label': '青年(18-25岁)',
                'mean_score': 72,
                'std_score': 12,
                'mean_duration': 7.2,
                'mean_efficiency': 86,
                'mean_n3_pct': 18,
                'mean_rem_pct': 22,
                'percentiles': [45, 58, 68, 72, 78, 85, 92]
            },
            '26-35': {
                'label': '青年(26-35岁)',
                'mean_score': 70,
                'std_score': 13,
                'mean_duration': 6.8,
                'mean_efficiency': 85,
                'mean_n3_pct': 16,
                'mean_rem_pct': 21,
                'percentiles': [42, 55, 65, 70, 76, 83, 90]
            },
            '36-45': {
                'label': '中年(36-45岁)',
                'mean_score': 68,
                'std_score': 14,
                'mean_duration': 6.5,
                'mean_efficiency': 83,
                'mean_n3_pct': 14,
                'mean_rem_pct': 20,
                'percentiles': [40, 52, 62, 68, 74, 81, 88]
            },
            '46-55': {
                'label': '中年(46-55岁)',
                'mean_score': 65,
                'std_score': 15,
                'mean_duration': 6.2,
                'mean_efficiency': 82,
                'mean_n3_pct': 12,
                'mean_rem_pct': 19,
                'percentiles': [38, 50, 60, 65, 71, 78, 85]
            },
            '56-65': {
                'label': '中老年(56-65岁)',
                'mean_score': 62,
                'std_score': 16,
                'mean_duration': 6.0,
                'mean_efficiency': 80,
                'mean_n3_pct': 10,
                'mean_rem_pct': 18,
                'percentiles': [35, 47, 57, 62, 68, 75, 82]
            },
            '65+': {
                'label': '老年(65岁以上)',
                'mean_score': 58,
                'std_score': 17,
                'mean_duration': 5.5,
                'mean_efficiency': 78,
                'mean_n3_pct': 8,
                'mean_rem_pct': 16,
                'percentiles': [32, 44, 54, 58, 64, 71, 78]
            }
        }
        self.gender_norms = {
            'male': {'score_adjustment': -2, 'n3_adjustment': -1},
            'female': {'score_adjustment': +2, 'n3_adjustment': +1}
        }

    def get_age_group(self, age):
        if age < 26:
            return '18-25'
        elif age < 36:
            return '26-35'
        elif age < 46:
            return '36-45'
        elif age < 56:
            return '46-55'
        elif age < 66:
            return '56-65'
        else:
            return '65+'

    def calculate_percentile_rank(self, sleep_score, age=30, gender='unknown'):
        age_group = self.get_age_group(age)
        norms = self.age_group_norms[age_group]

        adjusted_score = sleep_score
        if gender in self.gender_norms:
            adjusted_score -= self.gender_norms[gender]['score_adjustment']

        from scipy import stats
        percentile = stats.norm.cdf((adjusted_score - norms['mean_score']) / norms['std_score']) * 100

        if percentile < 10:
            rank = '较低'
            description = '您的睡眠质量低于同年龄段90%的人，建议重点改善'
        elif percentile < 25:
            rank = '中下'
            description = '您的睡眠质量低于同年龄段大多数人，有改进空间'
        elif percentile < 50:
            rank = '中等'
            description = '您的睡眠质量处于同年龄段中等水平'
        elif percentile < 75:
            rank = '良好'
            description = '您的睡眠质量优于同年龄段大多数人'
        elif percentile < 90:
            rank = '优秀'
            description = '您的睡眠质量非常好，优于同年龄段90%的人'
        else:
            rank = '极佳'
            description = '您的睡眠质量极佳，处于同年龄段前10%水平'

        return {
            'age_group': age_group,
            'age_group_label': norms['label'],
            'age': age,
            'gender': gender,
            'sleep_score': sleep_score,
            'adjusted_score': adjusted_score,
            'percentile': percentile,
            'rank': rank,
            'description': description,
            'group_norm': {
                'mean_score': norms['mean_score'],
                'std_score': norms['std_score'],
                'mean_duration': norms['mean_duration'],
                'mean_efficiency': norms['mean_efficiency'],
                'mean_n3_pct': norms['mean_n3_pct'],
                'mean_rem_pct': norms['mean_rem_pct']
            }
        }

    def compare_to_group(self, stage_analysis, age=30, gender='unknown'):
        age_group = self.get_age_group(age)
        norms = self.age_group_norms[age_group]

        comparisons = []
        duration = stage_analysis['total_sleep_duration']
        duration_diff = duration - norms['mean_duration']
        duration_status = '达标' if 7 <= duration <= 9 else '不足' if duration < 7 else '过多'
        comparisons.append({
            'metric': '睡眠时长',
            'your_value': f'{duration:.1f}小时',
            'group_mean': f"{norms['mean_duration']:.1f}小时",
            'difference': f"{duration_diff:+.1f}小时",
            'status': duration_status,
            'reference': 'AASM推荐: 7-9小时'
        })

        efficiency = stage_analysis['sleep_efficiency']
        efficiency_diff = efficiency - norms['mean_efficiency']
        efficiency_status = '优秀' if efficiency >= 90 else '良好' if efficiency >= 85 else '偏低'
        comparisons.append({
            'metric': '睡眠效率',
            'your_value': f'{efficiency:.1f}%',
            'group_mean': f"{norms['mean_efficiency']:.1f}%",
            'difference': f"{efficiency_diff:+.1f}%",
            'status': efficiency_status,
            'reference': 'AASM推荐: ≥85%'
        })

        n3_pct = stage_analysis['stage_distribution']['深睡']['percentage']
        n3_diff = n3_pct - norms['mean_n3_pct']
        n3_status = '良好' if 13 <= n3_pct <= 23 else '不足' if n3_pct < 13 else '过多'
        comparisons.append({
            'metric': '深睡比例',
            'your_value': f'{n3_pct:.1f}%',
            'group_mean': f"{norms['mean_n3_pct']:.1f}%",
            'difference': f"{n3_diff:+.1f}%",
            'status': n3_status,
            'reference': 'AASM推荐: 13-23%'
        })

        rem_pct = stage_analysis['stage_distribution']['REM']['percentage']
        rem_diff = rem_pct - norms['mean_rem_pct']
        rem_status = '良好' if 20 <= rem_pct <= 25 else '不足' if rem_pct < 20 else '过多'
        comparisons.append({
            'metric': 'REM睡眠比例',
            'your_value': f'{rem_pct:.1f}%',
            'group_mean': f"{norms['mean_rem_pct']:.1f}%",
            'difference': f"{rem_diff:+.1f}%",
            'status': rem_status,
            'reference': 'AASM推荐: 20-25%'
        })

        latency = stage_analysis['sleep_latency']
        latency_status = '良好' if latency <= 20 else '偏长' if latency <= 30 else '过长'
        comparisons.append({
            'metric': '入睡潜伏期',
            'your_value': f'{latency:.1f}分钟',
            'group_mean': '15-20分钟',
            'difference': '-',
            'status': latency_status,
            'reference': 'AASM推荐: ≤20分钟'
        })

        waso = stage_analysis['waso_pct']
        waso_status = '良好' if waso <= 10 else '偏高' if waso <= 15 else '过高'
        comparisons.append({
            'metric': 'WASO(夜间清醒)',
            'your_value': f'{waso:.1f}%',
            'group_mean': '5-10%',
            'difference': '-',
            'status': waso_status,
            'reference': 'AASM推荐: ≤10%'
        })

        return {
            'age_group': age_group,
            'age_group_label': norms['label'],
            'comparisons': comparisons,
            'summary': self._generate_comparison_summary(comparisons)
        }

    def _generate_comparison_summary(self, comparisons):
        good_count = sum(1 for c in comparisons if c['status'] in ['良好', '优秀', '达标'])
        total_count = len(comparisons)

        if good_count == total_count:
            return f'恭喜！您的{total_count}项睡眠指标全部达标，显著优于同龄人平均水平。'
        elif good_count >= total_count * 0.7:
            return f'您的{good_count}/{total_count}项指标达标，整体睡眠质量优于同龄人平均水平。'
        elif good_count >= total_count * 0.5:
            return f'您的{good_count}/{total_count}项指标达标，睡眠质量处于同龄人中等水平，有改进空间。'
        else:
            return f'您的{good_count}/{total_count}项指标达标，建议重点关注未达标项目的改善。'

    def generate_comparison_chart_data(self, sleep_score, age=30):
        age_group = self.get_age_group(age)
        norms = self.age_group_norms[age_group]
        percentiles = norms['percentiles']
        percentile_labels = ['P10', 'P25', 'P50', 'P75', 'P90', 'P95', 'P99']

        chart_data = {
            'percentile_labels': percentile_labels,
            'percentile_values': percentiles,
            'your_score': sleep_score,
            'mean_score': norms['mean_score'],
            'your_position': np.searchsorted(percentiles, sleep_score)
        }
        return chart_data