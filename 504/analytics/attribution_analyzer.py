import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional
from itertools import combinations
import copy


class AttributionAnalyzer:
    def __init__(self):
        self.conversion_paths = []
        self.non_conversion_paths = []
        self._is_fitted = False

    def fit(self, paths_df: pd.DataFrame, 
            conversion_event: str = 'purchase') -> 'AttributionAnalyzer':
        self.conversion_paths = []
        self.non_conversion_paths = []
        self.conversion_event = conversion_event
        self.all_events = set()

        for _, row in paths_df.iterrows():
            path = row['path']
            count = row.get('count', 1)
            events = path.split(' -> ')

            for event in events:
                self.all_events.add(event)

            if conversion_event in events:
                for _ in range(count):
                    self.conversion_paths.append(events[:events.index(conversion_event) + 1])
            else:
                for _ in range(count):
                    self.non_conversion_paths.append(events)

        self._is_fitted = True
        return self

    def first_touch_attribution(self) -> pd.DataFrame:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        first_touch_counts = Counter()
        for path in self.conversion_paths:
            if path:
                first_touch_counts[path[0]] += 1

        total = sum(first_touch_counts.values())
        results = []
        for event, count in first_touch_counts.most_common():
            results.append({
                'event': event,
                'attributed_conversions': count,
                'attribution_weight': round(count / total * 100, 2) if total > 0 else 0,
                'model': '首次触达'
            })

        return pd.DataFrame(results)

    def last_touch_attribution(self) -> pd.DataFrame:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        last_touch_counts = Counter()
        for path in self.conversion_paths:
            if len(path) >= 2:
                last_touch_counts[path[-2]] += 1
            elif path:
                last_touch_counts[path[0]] += 1

        total = sum(last_touch_counts.values())
        results = []
        for event, count in last_touch_counts.most_common():
            results.append({
                'event': event,
                'attributed_conversions': count,
                'attribution_weight': round(count / total * 100, 2) if total > 0 else 0,
                'model': '末次触达'
            })

        return pd.DataFrame(results)

    def linear_attribution(self) -> pd.DataFrame:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        event_weights = defaultdict(float)
        for path in self.conversion_paths:
            if len(path) <= 1:
                continue
            touchpoints = path[:-1]
            weight_per_touchpoint = 1.0 / len(touchpoints)
            for event in touchpoints:
                event_weights[event] += weight_per_touchpoint

        total = sum(event_weights.values())
        results = []
        for event, weight in sorted(event_weights.items(), key=lambda x: x[1], reverse=True):
            results.append({
                'event': event,
                'attributed_conversions': round(weight, 2),
                'attribution_weight': round(weight / total * 100, 2) if total > 0 else 0,
                'model': '线性归因'
            })

        return pd.DataFrame(results)

    def time_decay_attribution(self, decay_factor: float = 0.7) -> pd.DataFrame:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        event_weights = defaultdict(float)
        for path in self.conversion_paths:
            if len(path) <= 1:
                continue
            touchpoints = path[:-1]
            n = len(touchpoints)
            weights = [decay_factor ** (n - 1 - i) for i in range(n)]
            total_weight = sum(weights)

            for i, event in enumerate(touchpoints):
                event_weights[event] += weights[i] / total_weight

        total = sum(event_weights.values())
        results = []
        for event, weight in sorted(event_weights.items(), key=lambda x: x[1], reverse=True):
            results.append({
                'event': event,
                'attributed_conversions': round(weight, 2),
                'attribution_weight': round(weight / total * 100, 2) if total > 0 else 0,
                'model': '时间衰减'
            })

        return pd.DataFrame(results)

    def position_based_attribution(self, 
                                     first_weight: float = 0.4,
                                     last_weight: float = 0.4,
                                     middle_weight: float = 0.2) -> pd.DataFrame:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        event_weights = defaultdict(float)
        for path in self.conversion_paths:
            if len(path) <= 1:
                continue
            touchpoints = path[:-1]
            n = len(touchpoints)

            if n == 1:
                event_weights[touchpoints[0]] += 1.0
            elif n == 2:
                event_weights[touchpoints[0]] += 0.5
                event_weights[touchpoints[1]] += 0.5
            else:
                event_weights[touchpoints[0]] += first_weight
                event_weights[touchpoints[-1]] += last_weight
                middle_total = middle_weight / (n - 2)
                for i in range(1, n - 1):
                    event_weights[touchpoints[i]] += middle_total

        total = sum(event_weights.values())
        results = []
        for event, weight in sorted(event_weights.items(), key=lambda x: x[1], reverse=True):
            results.append({
                'event': event,
                'attributed_conversions': round(weight, 2),
                'attribution_weight': round(weight / total * 100, 2) if total > 0 else 0,
                'model': '位置归因'
            })

        return pd.DataFrame(results)

    def markov_chain_attribution(self) -> pd.DataFrame:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        all_paths = self.conversion_paths + self.non_conversion_paths

        removal_effects = self._compute_removal_effects(all_paths)

        total_effect = sum(removal_effects.values())
        results = []
        for event, effect in sorted(removal_effects.items(), key=lambda x: x[1], reverse=True):
            results.append({
                'event': event,
                'attributed_conversions': round(effect, 2),
                'attribution_weight': round(effect / total_effect * 100, 2) if total_effect > 0 else 0,
                'removal_effect': round(effect, 4),
                'model': '马尔可夫链'
            })

        return pd.DataFrame(results)

    def _compute_removal_effects(self, all_paths: List[List[str]]) -> Dict[str, float]:
        transition_matrix = self._build_transition_matrix(all_paths)
        base_conversion_rate = self._compute_conversion_rate(transition_matrix)

        removal_effects = {}
        events_to_test = [e for e in self.all_events if e != self.conversion_event]

        for event in events_to_test:
            modified_matrix = self._remove_event(transition_matrix, event)
            modified_conversion_rate = self._compute_conversion_rate(modified_matrix)

            if base_conversion_rate > 0:
                removal_effects[event] = 1 - (modified_conversion_rate / base_conversion_rate)
            else:
                removal_effects[event] = 0

        return removal_effects

    def _build_transition_matrix(self, all_paths: List[List[str]]) -> Dict:
        transitions = defaultdict(Counter)
        states = set()

        states.add('start')
        states.add('conversion')
        states.add('null')

        for path in all_paths:
            events = path
            is_conversion = self.conversion_event in events

            prev = 'start'
            for i, event in enumerate(events):
                if event == self.conversion_event:
                    transitions[prev]['conversion'] += 1
                    break
                transitions[prev][event] += 1
                states.add(event)
                prev = event

            if not is_conversion:
                if events:
                    transitions[events[-1]]['null'] += 1
                else:
                    transitions['start']['null'] += 1

        return transitions

    def _compute_conversion_rate(self, transition_matrix: Dict) -> float:
        total_starts = sum(transition_matrix.get('start', {}).values())
        if total_starts == 0:
            return 0.0

        conversions = transition_matrix.get('start', {}).get('conversion', 0)

        def compute_path_prob(current, visited=None):
            if visited is None:
                visited = set()

            if current == 'conversion':
                return 1.0
            if current == 'null' or current in visited:
                return 0.0

            visited.add(current)
            total = sum(transition_matrix.get(current, {}).values())
            if total == 0:
                return 0.0

            prob = 0.0
            for next_state, count in transition_matrix.get(current, {}).items():
                transition_prob = count / total
                prob += transition_prob * compute_path_prob(next_state, visited.copy())

            return prob

        return compute_path_prob('start')

    def _remove_event(self, transition_matrix: Dict, event: str) -> Dict:
        modified = copy.deepcopy(transition_matrix)

        if event in modified:
            redistributed = modified[event]
            del modified[event]

            for source in modified:
                if event in modified[source]:
                    event_out_weight = modified[source][event]
                    del modified[source][event]
                    total_remaining = sum(modified[source].values())
                    if total_remaining > 0:
                        for target in modified[source]:
                            modified[source][target] += (
                                event_out_weight * modified[source][target] / total_remaining
                            )

        return modified

    def compare_models(self) -> pd.DataFrame:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        models = {
            '首次触达': self.first_touch_attribution(),
            '末次触达': self.last_touch_attribution(),
            '线性归因': self.linear_attribution(),
            '时间衰减': self.time_decay_attribution(),
            '位置归因': self.position_based_attribution(),
            '马尔可夫链': self.markov_chain_attribution()
        }

        all_results = []
        for model_name, model_df in models.items():
            if not model_df.empty:
                for _, row in model_df.iterrows():
                    all_results.append({
                        'event': row['event'],
                        'model': model_name,
                        'attribution_weight': row['attribution_weight'],
                        'attributed_conversions': row['attributed_conversions']
                    })

        return pd.DataFrame(all_results)

    def get_path_contribution(self, target_event: str) -> pd.DataFrame:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        path_contributions = Counter()

        for path in self.conversion_paths:
            if target_event not in path:
                continue

            idx = path.index(target_event)
            prefix = ' -> '.join(path[:idx + 1])

            remaining_events = path[idx + 1:]
            if self.conversion_event in remaining_events:
                path_contributions[prefix] += 1

        if not path_contributions:
            return pd.DataFrame()

        total = sum(path_contributions.values())
        results = []
        for path, count in path_contributions.most_common(20):
            results.append({
                'path_to_event': path,
                'conversions_after': count,
                'contribution_rate': round(count / total * 100, 2)
            })

        return pd.DataFrame(results)

    def get_conversion_funnel_attribution(self) -> pd.DataFrame:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        event_conversion_rates = {}
        event_appearances = Counter()

        for path in self.conversion_paths:
            for event in set(path[:-1]):
                event_appearances[event] += 1

        for path in self.non_conversion_paths:
            for event in set(path):
                event_appearances[event] += 0

        total_conversions = len(self.conversion_paths)
        total_paths = len(self.conversion_paths) + len(self.non_conversion_paths)

        for event in self.all_events:
            if event == self.conversion_event:
                continue

            conv_with_event = sum(
                1 for path in self.conversion_paths if event in path
            )
            non_conv_with_event = sum(
                1 for path in self.non_conversion_paths if event in path
            )

            total_with_event = conv_with_event + non_conv_with_event
            conv_rate = conv_with_event / total_with_event if total_with_event > 0 else 0

            overall_conv_rate = total_conversions / total_paths if total_paths > 0 else 0

            lift = conv_rate / overall_conv_rate if overall_conv_rate > 0 else 0

            event_conversion_rates[event] = {
                'conversions_with_event': conv_with_event,
                'non_conversions_with_event': non_conv_with_event,
                'total_with_event': total_with_event,
                'conversion_rate': round(conv_rate * 100, 2),
                'overall_conversion_rate': round(overall_conv_rate * 100, 2),
                'lift': round(lift, 2)
            }

        results = []
        for event, stats in sorted(
            event_conversion_rates.items(),
            key=lambda x: x[1]['lift'],
            reverse=True
        ):
            results.append({
                'event': event,
                **stats
            })

        return pd.DataFrame(results)
