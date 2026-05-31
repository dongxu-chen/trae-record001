import os
import json
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
from pypinyin import lazy_pinyin

class CorrectionEvaluator:
    def __init__(self, evaluation_path, domain_dict):
        self.evaluation_path = evaluation_path
        self.domain_dict = domain_dict
        
        self.correction_records = []
        self.daily_stats = defaultdict(lambda: {
            'total_queries': 0,
            'corrected_queries': 0,
            'accepted_corrections': 0,
            'skipped_corrections': 0,
            'avg_confidence': [],
            'edit_distances': [],
            'domain_match_rate': []
        })
        
        self.overall_stats = {
            'total_queries': 0,
            'corrected_queries': 0,
            'accepted_corrections': 0,
            'skipped_corrections': 0
        }
        
        self.load_evaluation()
    
    def load_evaluation(self):
        if os.path.exists(self.evaluation_path):
            try:
                with open(self.evaluation_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.correction_records = data.get('records', [])
                    self.overall_stats = data.get('overall_stats', {
                        'total_queries': 0,
                        'corrected_queries': 0,
                        'accepted_corrections': 0,
                        'skipped_corrections': 0
                    })
                    
                    for record in self.correction_records:
                        date = record.get('timestamp', '')[:10]
                        if date:
                            stats = self.daily_stats[date]
                            stats['total_queries'] += 1
                            if record.get('needs_correction', False):
                                stats['corrected_queries'] += 1
                            if record.get('confidence') is not None:
                                stats['avg_confidence'].append(record['confidence'])
                            if record.get('edit_distance') is not None:
                                stats['edit_distances'].append(record['edit_distance'])
            except Exception as e:
                print(f"Error loading evaluation: {e}")
    
    def save_evaluation(self):
        data = {
            'records': self.correction_records[-10000:],
            'overall_stats': self.overall_stats,
            'timestamp': datetime.now().isoformat()
        }
        
        os.makedirs(os.path.dirname(self.evaluation_path), exist_ok=True)
        with open(self.evaluation_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def record_correction(self, original_query, corrected_query, needs_correction, 
                          confidence=0.0, edit_distance=0, user_feedback=None):
        timestamp = datetime.now().isoformat()
        date = timestamp[:10]
        
        in_domain = corrected_query in self.domain_dict.words
        domain_weight = self.domain_dict.get_weight(corrected_query)
        
        record = {
            'timestamp': timestamp,
            'original': original_query,
            'corrected': corrected_query,
            'needs_correction': needs_correction,
            'confidence': confidence,
            'edit_distance': edit_distance,
            'in_domain': in_domain,
            'domain_weight': domain_weight,
            'user_feedback': user_feedback
        }
        
        self.correction_records.append(record)
        
        self.overall_stats['total_queries'] += 1
        if needs_correction:
            self.overall_stats['corrected_queries'] += 1
        
        if user_feedback == 'accept':
            self.overall_stats['accepted_corrections'] += 1
        elif user_feedback == 'skip':
            self.overall_stats['skipped_corrections'] += 1
        
        stats = self.daily_stats[date]
        stats['total_queries'] += 1
        if needs_correction:
            stats['corrected_queries'] += 1
        if confidence is not None:
            stats['avg_confidence'].append(confidence)
        if edit_distance is not None:
            stats['edit_distances'].append(edit_distance)
        if in_domain:
            stats['domain_match_rate'].append(1)
        else:
            stats['domain_match_rate'].append(0)
        
        if user_feedback == 'accept':
            stats['accepted_corrections'] += 1
        elif user_feedback == 'skip':
            stats['skipped_corrections'] += 1
        
        self.save_evaluation()
        return record
    
    def evaluate_improvement(self, original_query, corrected_query):
        original_in_domain = original_query in self.domain_dict.words
        corrected_in_domain = corrected_query in self.domain_dict.words
        
        original_weight = self.domain_dict.get_weight(original_query)
        corrected_weight = self.domain_dict.get_weight(corrected_query)
        
        edit_distance = self._calc_edit_distance(original_query, corrected_query)
        
        improvement = {
            'original_in_domain': original_in_domain,
            'corrected_in_domain': corrected_in_domain,
            'original_weight': original_weight,
            'corrected_weight': corrected_weight,
            'weight_improvement': corrected_weight - original_weight,
            'edit_distance': edit_distance,
            'domain_coverage_improved': corrected_in_domain and not original_in_domain,
            'weight_improved': corrected_weight > original_weight
        }
        
        search_effect_before = self._estimate_search_effect(original_query)
        search_effect_after = self._estimate_search_effect(corrected_query)
        
        improvement['search_effect_before'] = search_effect_before
        improvement['search_effect_after'] = search_effect_after
        improvement['search_effect_improvement'] = search_effect_after - search_effect_before
        improvement['improvement_percentage'] = ((search_effect_after - search_effect_before) / max(search_effect_before, 0.01)) * 100
        
        return improvement
    
    def _estimate_search_effect(self, query):
        if query in self.domain_dict.words:
            weight = self.domain_dict.get_weight(query)
            max_weight = max(self.domain_dict.words.values()) if self.domain_dict.words else 1
            return weight / max_weight * 100
        else:
            pinyin = ''.join([p for p in lazy_pinyin(query)])
            matches = self.domain_dict.vector_match_pinyin(pinyin, min_similarity=0.5)
            if matches:
                best_match = matches[0]
                similarity = best_match[1]
                weight = self.domain_dict.get_weight(best_match[0])
                max_weight = max(self.domain_dict.words.values()) if self.domain_dict.words else 1
                return (weight / max_weight) * similarity * 60
            return 10
    
    def _calc_edit_distance(self, s1, s2):
        if len(s1) > len(s2):
            s1, s2 = s2, s1
        distances = range(len(s1) + 1)
        for i2, c2 in enumerate(s2):
            distances_ = [i2 + 1]
            for i1, c1 in enumerate(s1):
                if c1 == c2:
                    distances_.append(distances[i1])
                else:
                    distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
            distances = distances_
        return distances[-1]
    
    def get_overall_metrics(self):
        total = self.overall_stats['total_queries']
        corrected = self.overall_stats['corrected_queries']
        accepted = self.overall_stats['accepted_corrections']
        skipped = self.overall_stats['skipped_corrections']
        
        correction_rate = corrected / total * 100 if total > 0 else 0
        acceptance_rate = accepted / max(corrected, 1) * 100 if corrected > 0 else 0
        
        recent_confidences = []
        recent_distances = []
        for record in self.correction_records[-100:]:
            if record.get('confidence') is not None:
                recent_confidences.append(record['confidence'])
            if record.get('edit_distance') is not None:
                recent_distances.append(record['edit_distance'])
        
        avg_confidence = np.mean(recent_confidences) if recent_confidences else 0
        avg_edit_distance = np.mean(recent_distances) if recent_distances else 0
        
        return {
            'total_queries': total,
            'corrected_queries': corrected,
            'accepted_corrections': accepted,
            'skipped_corrections': skipped,
            'correction_rate': correction_rate,
            'acceptance_rate': acceptance_rate,
            'avg_confidence': avg_confidence,
            'avg_edit_distance': avg_edit_distance,
            'user_satisfaction_score': acceptance_rate * 0.7 + avg_confidence * 30
        }
    
    def get_daily_metrics(self, days=7):
        dates = sorted(self.daily_stats.keys())[-days:]
        metrics = []
        
        for date in dates:
            stats = self.daily_stats[date]
            total = stats['total_queries']
            corrected = stats['corrected_queries']
            accepted = stats.get('accepted_corrections', 0)
            
            metrics.append({
                'date': date,
                'total_queries': total,
                'corrected_queries': corrected,
                'correction_rate': corrected / total * 100 if total > 0 else 0,
                'acceptance_rate': accepted / max(corrected, 1) * 100 if corrected > 0 else 0,
                'avg_confidence': np.mean(stats['avg_confidence']) if stats['avg_confidence'] else 0,
                'avg_edit_distance': np.mean(stats['edit_distances']) if stats['edit_distances'] else 0,
                'domain_match_rate': np.mean(stats['domain_match_rate']) * 100 if stats['domain_match_rate'] else 0
            })
        
        return metrics
    
    def get_top_corrections(self, limit=10):
        correction_counts = defaultdict(lambda: {'count': 0, 'accepted': 0})
        
        for record in self.correction_records:
            if record.get('needs_correction'):
                key = f"{record['original']} → {record['corrected']}"
                correction_counts[key]['count'] += 1
                if record.get('user_feedback') == 'accept':
                    correction_counts[key]['accepted'] += 1
        
        sorted_corrections = sorted(
            correction_counts.items(),
            key=lambda x: -x[1]['count']
        )[:limit]
        
        return [
            {
                'correction': key,
                'count': value['count'],
                'accepted': value['accepted'],
                'acceptance_rate': value['accepted'] / max(value['count'], 1) * 100
            }
            for key, value in sorted_corrections
        ]
    
    def update_feedback(self, original_query, corrected_query, feedback):
        for record in reversed(self.correction_records):
            if record['original'] == original_query and record['corrected'] == corrected_query:
                record['user_feedback'] = feedback
                
                if feedback == 'accept':
                    self.overall_stats['accepted_corrections'] += 1
                elif feedback == 'skip':
                    self.overall_stats['skipped_corrections'] += 1
                
                self.save_evaluation()
                break
