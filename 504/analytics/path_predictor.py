import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional
import json


class MarkovChainPredictor:
    def __init__(self, order: int = 1):
        self.order = order
        self.transition_counts = defaultdict(Counter)
        self.transition_probs = {}
        self.state_counts = Counter()
        self.states = set()
        self._is_fitted = False

    def fit(self, paths_df: pd.DataFrame) -> 'MarkovChainPredictor':
        self.transition_counts = defaultdict(Counter)
        self.state_counts = Counter()
        self.states = set()

        for _, row in paths_df.iterrows():
            path = row['path']
            events = path.split(' -> ')
            weight = row.get('count', 1)

            for i in range(len(events)):
                self.states.add(events[i])
                self.state_counts[events[i]] += weight

            if self.order == 1:
                for i in range(len(events) - 1):
                    source = events[i]
                    target = events[i + 1]
                    self.transition_counts[source][target] += weight
            else:
                for i in range(len(events) - 1):
                    if i + self.order <= len(events):
                        source = tuple(events[i:i + self.order])
                        target = events[i + self.order] if i + self.order < len(events) else None
                        if target:
                            self.transition_counts[source][target] += weight

        self._compute_probabilities()
        self._is_fitted = True
        return self

    def _compute_probabilities(self):
        self.transition_probs = {}
        for source, targets in self.transition_counts.items():
            total = sum(targets.values())
            if total > 0:
                self.transition_probs[source] = {
                    target: count / total for target, count in targets.items()
                }

    def predict_next(self, current_state: str, top_k: int = 5) -> List[Dict]:
        if not self._is_fitted:
            raise ValueError("模型未训练，请先调用 fit()")

        source = current_state if self.order == 1 else current_state

        if source not in self.transition_probs:
            return self._predict_by_global_freq(top_k)

        probs = self.transition_probs[source]
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)

        results = []
        for i, (next_event, prob) in enumerate(sorted_probs[:top_k]):
            results.append({
                'rank': i + 1,
                'next_event': next_event,
                'probability': round(prob * 100, 2),
                'confidence': self._compute_confidence(source, prob)
            })

        return results

    def predict_sequence(self, current_state: str, steps: int = 3, 
                          top_k: int = 3) -> List[Dict]:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        results = []
        current = current_state

        for step in range(steps):
            predictions = self.predict_next(current, top_k=top_k)
            if not predictions:
                break

            step_result = {
                'step': step + 1,
                'from_state': current,
                'predictions': predictions,
                'most_likely': predictions[0]['next_event'] if predictions else None,
                'most_likely_prob': predictions[0]['probability'] if predictions else 0
            }
            results.append(step_result)
            current = predictions[0]['next_event']

        return results

    def _predict_by_global_freq(self, top_k: int = 5) -> List[Dict]:
        total = sum(self.state_counts.values())
        if total == 0:
            return []

        sorted_states = sorted(
            self.state_counts.items(), key=lambda x: x[1], reverse=True
        )

        results = []
        for i, (event, count) in enumerate(sorted_states[:top_k]):
            results.append({
                'rank': i + 1,
                'next_event': event,
                'probability': round(count / total * 100, 2),
                'confidence': 'low'
            })

        return results

    def _compute_confidence(self, source: str, prob: float) -> str:
        total_from_source = sum(self.transition_counts[source].values())
        if total_from_source < 10:
            return 'low'
        elif prob > 0.5:
            return 'high'
        elif prob > 0.2:
            return 'medium'
        else:
            return 'low'

    def get_state_entropy(self, state: str) -> float:
        if state not in self.transition_probs:
            return 0.0

        probs = list(self.transition_probs[state].values())
        entropy = -sum(p * np.log2(p) for p in probs if p > 0)
        return round(entropy, 4)

    def get_all_entropies(self) -> pd.DataFrame:
        data = []
        for state in self.states:
            entropy = self.get_state_entropy(state)
            outgoing = len(self.transition_counts.get(state, {}))
            total_transitions = sum(self.transition_counts.get(state, {}).values())
            data.append({
                'state': state,
                'entropy': entropy,
                'outgoing_transitions': outgoing,
                'total_transitions': total_transitions,
                'predictability': round(max(0, 1 - entropy / np.log2(max(outgoing, 2))), 4)
            })

        return pd.DataFrame(data).sort_values('entropy', ascending=False)

    def get_prediction_tree(self, root_state: str, max_depth: int = 3,
                             top_k: int = 3, min_prob: float = 0.05) -> Dict:
        tree = {
            'name': root_state,
            'children': [],
            'prob': 1.0
        }

        def build_tree(node, state, depth, cumulative_prob):
            if depth >= max_depth or cumulative_prob < min_prob:
                return

            predictions = self.predict_next(state, top_k=top_k)
            for pred in predictions:
                child_prob = cumulative_prob * (pred['probability'] / 100)
                if child_prob < min_prob:
                    continue

                child = {
                    'name': pred['next_event'],
                    'prob': round(child_prob * 100, 2),
                    'transition_prob': pred['probability'],
                    'confidence': pred['confidence'],
                    'children': []
                }
                node['children'].append(child)
                build_tree(child, pred['next_event'], depth + 1, child_prob)

        build_tree(tree, root_state, 0, 1.0)
        return tree

    def get_transition_matrix(self) -> pd.DataFrame:
        states_list = sorted(self.states)
        matrix = pd.DataFrame(0.0, index=states_list, columns=states_list)

        for source, targets in self.transition_probs.items():
            if isinstance(source, tuple):
                continue
            for target, prob in targets.items():
                if target in matrix.columns:
                    matrix.loc[source, target] = round(prob, 4)

        return matrix

    def predict_with_sequence_context(self, event_sequence: List[str], 
                                        top_k: int = 5) -> List[Dict]:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        if len(event_sequence) >= self.order and self.order > 1:
            context = tuple(event_sequence[-self.order:])
            if context in self.transition_probs:
                probs = self.transition_probs[context]
                sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
                return [
                    {
                        'rank': i + 1,
                        'next_event': target,
                        'probability': round(prob * 100, 2),
                        'context': ' -> '.join(context)
                    }
                    for i, (target, prob) in enumerate(sorted_probs[:top_k])
                ]

        if event_sequence:
            return self.predict_next(event_sequence[-1], top_k)

        return self._predict_by_global_freq(top_k)
