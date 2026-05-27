import numpy as np
import pandas as pd
from collections import Counter


class SleepQualityAnalyzer:
    def __init__(self):
        self.aasm_standards = {
            'sleep_efficiency_min': 85.0,
            'sleep_efficiency_optimal': 90.0,
            'sleep_latency_max': 20.0,
            'waso_max_pct': 10.0,
            'n1_max_pct': 10.0,
            'n2_min_pct': 45.0,
            'n2_max_pct': 65.0,
            'n3_min_pct': 13.0,
            'n3_max_pct': 23.0,
            'rem_min_pct': 20.0,
            'rem_max_pct': 25.0,
            'total_sleep_min': 7.0,
            'total_sleep_max': 9.0,
            'arousal_index_max': 5.0,
        }
        self.expert_weights = {
            'sleep_efficiency': 0.20,
            'sleep_duration': 0.20,
            'n3_sleep': 0.20,
            'rem_sleep': 0.15,
            'sleep_fragmentation': 0.15,
            'sleep_latency': 0.10,
        }
        self.grade_calibration = {
            'excellent': {'min': 90, 'label': '优秀', 'color': '#2ed573'},
            'good': {'min': 75, 'label': '良好', 'color': '#7bed9f'},
            'fair': {'min': 60, 'label': '一般', 'color': '#ffd93d'},
            'poor': {'min': 45, 'label': '较差', 'color': '#ffa502'},
            'very_poor': {'min': 0, 'label': '差', 'color': '#ff4b5c'},
        }

    def analyze_sleep_stages(self, stages, epoch_duration=30):
        total_epochs = len(stages)
        total_minutes = total_epochs * epoch_duration / 60
        stage_counts = Counter(stages)
        stage_distribution = {}
        for stage in ['清醒', '浅睡', '深睡', 'REM']:
            count = stage_counts.get(stage, 0)
            stage_distribution[stage] = {
                'minutes': count * epoch_duration / 60,
                'percentage': count / total_epochs * 100
            }
        sleep_efficiency = (total_epochs - stage_counts.get('清醒', 0)) / total_epochs * 100
        sleep_period = total_minutes
        sleep_latency = self._estimate_sleep_latency(stages, epoch_duration)
        waso_pct = self._calculate_waso(stages, epoch_duration)
        arousal_index = self._estimate_arousal_index(stages, epoch_duration)
        result = {
            'total_sleep_duration': total_minutes,
            'stage_distribution': stage_distribution,
            'sleep_efficiency': sleep_efficiency,
            'sleep_latency': sleep_latency,
            'waso_pct': waso_pct,
            'arousal_index': arousal_index,
            'sleep_period': sleep_period
        }
        return result

    def _estimate_sleep_latency(self, stages, epoch_duration):
        for i, stage in enumerate(stages):
            if stage != '清醒':
                return (i + 1) * epoch_duration / 60
        return len(stages) * epoch_duration / 60

    def _calculate_waso(self, stages, epoch_duration):
        sleep_start_idx = None
        for i, stage in enumerate(stages):
            if stage != '清醒':
                sleep_start_idx = i
                break
        if sleep_start_idx is None:
            return 100.0
        sleep_end_idx = len(stages)
        for i in range(len(stages) - 1, -1, -1):
            if stages[i] != '清醒':
                sleep_end_idx = i
                break
        wake_after_sleep = sum(1 for s in stages[sleep_start_idx:sleep_end_idx + 1] if s == '清醒')
        total_sleep_epochs = sleep_end_idx - sleep_start_idx + 1
        return wake_after_sleep / total_sleep_epochs * 100

    def _estimate_arousal_index(self, stages, epoch_duration):
        transitions = 0
        for i in range(1, len(stages)):
            if stages[i] == '清醒' and stages[i - 1] != '清醒':
                transitions += 1
        sleep_hours = len(stages) * epoch_duration / 3600
        return transitions / sleep_hours if sleep_hours > 0 else 0

    def calculate_sleep_score(self, stage_analysis, hrv_metrics=None):
        score_components = {}
        stage_dist = stage_analysis['stage_distribution']
        sleep_efficiency = stage_analysis['sleep_efficiency']
        efficiency_score = self._score_sleep_efficiency(sleep_efficiency)
        score_components['sleep_efficiency'] = {'score': efficiency_score, 'weight': self.expert_weights['sleep_efficiency']}
        total_duration = stage_analysis['total_sleep_duration']
        duration_score = self._score_sleep_duration(total_duration)
        score_components['sleep_duration'] = {'score': duration_score, 'weight': self.expert_weights['sleep_duration']}
        n3_pct = stage_dist['深睡']['percentage']
        n3_score = self._score_n3_sleep(n3_pct)
        score_components['n3_sleep'] = {'score': n3_score, 'weight': self.expert_weights['n3_sleep']}
        rem_pct = stage_dist['REM']['percentage']
        rem_score = self._score_rem_sleep(rem_pct)
        score_components['rem_sleep'] = {'score': rem_score, 'weight': self.expert_weights['rem_sleep']}
        transitions_per_hour = stage_analysis['arousal_index']
        frag_score = self._score_sleep_fragmentation(transitions_per_hour)
        score_components['sleep_fragmentation'] = {'score': frag_score, 'weight': self.expert_weights['sleep_fragmentation']}
        sleep_latency = stage_analysis['sleep_latency']
        latency_score = self._score_sleep_latency(sleep_latency)
        score_components['sleep_latency'] = {'score': latency_score, 'weight': self.expert_weights['sleep_latency']}
        total_score = sum(comp['score'] * comp['weight'] for comp in score_components.values())
        grade = self._determine_grade(total_score)
        self.last_result = {
            'total_score': total_score,
            'grade': grade,
            'components': score_components
        }
        return self.last_result

    def _score_sleep_efficiency(self, value):
        optimal = self.aasm_standards['sleep_efficiency_optimal']
        min_acceptable = self.aasm_standards['sleep_efficiency_min']
        if value >= optimal:
            return 100.0
        elif value >= min_acceptable:
            return 70 + (value - min_acceptable) / (optimal - min_acceptable) * 30
        else:
            return max(0, value / min_acceptable * 70)

    def _score_sleep_duration(self, value):
        min_val = self.aasm_standards['total_sleep_min']
        max_val = self.aasm_standards['total_sleep_max']
        if min_val <= value <= max_val:
            return 100.0
        elif value < min_val:
            return max(0, value / min_val * 100)
        else:
            return max(40, 100 - (value - max_val) * 10)

    def _score_n3_sleep(self, value):
        min_val = self.aasm_standards['n3_min_pct']
        max_val = self.aasm_standards['n3_max_pct']
        if min_val <= value <= max_val:
            return 100.0
        elif value < min_val:
            return max(0, value / min_val * 100)
        else:
            return max(50, 100 - (value - max_val) * 5)

    def _score_rem_sleep(self, value):
        min_val = self.aasm_standards['rem_min_pct']
        max_val = self.aasm_standards['rem_max_pct']
        if min_val <= value <= max_val:
            return 100.0
        elif value < min_val:
            return max(0, value / min_val * 100)
        else:
            return max(50, 100 - (value - max_val) * 5)

    def _score_sleep_fragmentation(self, value):
        max_val = self.aasm_standards['arousal_index_max']
        if value <= max_val:
            return 100.0
        else:
            return max(0, 100 - (value - max_val) * 10)

    def _score_sleep_latency(self, value):
        max_val = self.aasm_standards['sleep_latency_max']
        if value <= max_val:
            return 100.0
        else:
            return max(0, 100 - (value - max_val) * 2)

    def _determine_grade(self, score):
        for grade_name, grade_info in self.grade_calibration.items():
            if score >= grade_info['min']:
                return grade_info['label']
        return self.grade_calibration['very_poor']['label']

    def analyze_sleep_regularity(self, stage_sequence):
        transitions = 0
        for i in range(1, len(stage_sequence)):
            if stage_sequence[i] != stage_sequence[i-1]:
                transitions += 1
        transitions_per_hour = transitions / (len(stage_sequence) * 30 / 3600)
        sleep_fragmentation = transitions / len(stage_sequence) * 100
        stage_durations = []
        current_stage = stage_sequence[0]
        current_duration = 1
        for stage in stage_sequence[1:]:
            if stage == current_stage:
                current_duration += 1
            else:
                stage_durations.append(current_duration * 30 / 60)
                current_stage = stage
                current_duration = 1
        stage_durations.append(current_duration * 30 / 60)
        avg_stage_duration = np.mean(stage_durations)
        max_stage_duration = np.max(stage_durations)
        sleep_cycles = self._detect_sleep_cycles(stage_sequence)
        regularity_score = max(0, 100 - transitions_per_hour * 5)
        return {
            'transitions_count': transitions,
            'transitions_per_hour': transitions_per_hour,
            'sleep_fragmentation_index': sleep_fragmentation,
            'average_stage_duration_min': avg_stage_duration,
            'max_stage_duration_min': max_stage_duration,
            'sleep_cycles_count': len(sleep_cycles),
            'regularity_score': regularity_score
        }

    def _detect_sleep_cycles(self, stage_sequence):
        cycles = []
        cycle_start = 0
        rem_seen = False
        for i, stage in enumerate(stage_sequence):
            if stage == 'REM':
                rem_seen = True
            elif rem_seen and stage in ['浅睡', '深睡'] and i > cycle_start + 30:
                cycles.append((cycle_start, i))
                cycle_start = i
                rem_seen = False
        return cycles

    def generate_recommendations(self, sleep_score, stage_analysis, regularity_analysis):
        recommendations = []
        score = sleep_score['total_score']
        stage_dist = stage_analysis['stage_distribution']
        if score < 75:
            recommendations.append({
                'category': 'overall',
                'priority': 'high',
                'message': '根据AASM睡眠医学标准，您的睡眠质量需要改善。建议调整作息时间并建立规律的睡眠习惯，目标睡眠效率>85%。'
            })
        if stage_analysis['sleep_efficiency'] < self.aasm_standards['sleep_efficiency_min']:
            recommendations.append({
                'category': 'efficiency',
                'priority': 'high',
                'message': f'睡眠效率({stage_analysis["sleep_efficiency"]:.1f}%)低于AASM建议的85%标准。建议减少卧床清醒时间，建立固定的起床时间。'
            })
        if stage_dist['深睡']['percentage'] < self.aasm_standards['n3_min_pct']:
            recommendations.append({
                'category': 'deep_sleep',
                'priority': 'high',
                'message': f'深睡(N3)时间({stage_dist["深睡"]["percentage"]:.1f}%)低于AASM建议的13-23%范围。建议睡前避免使用电子设备，保持卧室凉爽(18-20°C)黑暗。'
            })
        if stage_dist['REM']['percentage'] < self.aasm_standards['rem_min_pct']:
            recommendations.append({
                'category': 'rem_sleep',
                'priority': 'medium',
                'message': f'REM睡眠({stage_dist["REM"]["percentage"]:.1f}%)低于AASM建议的20-25%范围。尝试减轻压力，睡前进行放松活动如冥想或深呼吸。'
            })
        if stage_analysis['sleep_latency'] > self.aasm_standards['sleep_latency_max']:
            recommendations.append({
                'category': 'latency',
                'priority': 'medium',
                'message': f'入睡潜伏期({stage_analysis["sleep_latency"]:.0f}分钟)超过AASM建议的20分钟。建议建立睡前放松仪式，减少睡前刺激。'
            })
        if stage_analysis['waso_pct'] > self.aasm_standards['waso_max_pct']:
            recommendations.append({
                'category': 'waso',
                'priority': 'high',
                'message': f'睡眠后清醒时间(WASO)占比({stage_analysis["waso_pct"]:.1f}%)超过AASM建议的10%。检查睡眠环境，减少噪音和光线干扰。'
            })
        if regularity_analysis['transitions_per_hour'] > self.aasm_standards['arousal_index_max']:
            recommendations.append({
                'category': 'fragmentation',
                'priority': 'medium',
                'message': f'觉醒指数({regularity_analysis["transitions_per_hour"]:.1f}次/小时)偏高。睡眠较易中断，建议优化睡眠环境。'
            })
        if stage_analysis['total_sleep_duration'] < self.aasm_standards['total_sleep_min']:
            recommendations.append({
                'category': 'duration',
                'priority': 'high',
                'message': f'总睡眠时间({stage_analysis["total_sleep_duration"]:.1f}小时)低于AASM建议的7-9小时。建议提前入睡时间。'
            })
        if not recommendations:
            recommendations.append({
                'category': 'overall',
                'priority': 'low',
                'message': '根据AASM睡眠医学标准，您的睡眠质量良好！各项指标均在正常范围内，继续保持健康的睡眠习惯。'
            })
        return recommendations
