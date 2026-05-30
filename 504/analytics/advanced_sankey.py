import pandas as pd
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class SankeyNode:
    name: str
    group: Optional[str] = None
    is_collapsed: bool = False
    is_aggregate: bool = False
    children: List[str] = field(default_factory=list)
    value: int = 0


@dataclass
class SankeyLink:
    source: str
    target: str
    value: int
    is_aggregate: bool = False


class AdvancedSankeyAnalyzer:
    def __init__(self):
        self.EVENT_GROUPS = {
            'page_view': ['page_view_home', 'page_view_product', 'page_view_category', 'page_view_search'],
            'engagement': ['search', 'filter', 'sort', 'click_product'],
            'cart': ['add_to_cart', 'remove_from_cart', 'view_cart', 'update_cart'],
            'checkout': ['checkout_start', 'checkout_complete', 'enter_shipping', 'enter_payment'],
            'purchase': ['purchase', 'purchase_complete', 'order_confirmation'],
            'account': ['login', 'logout', 'register', 'view_account', 'edit_profile']
        }
        
        self.GROUP_COLORS = {
            'page_view': '#5470c6',
            'engagement': '#91cc75',
            'cart': '#fac858',
            'checkout': '#ee6666',
            'purchase': '#73c0de',
            'account': '#3ba272',
            'other': '#9a60b4'
        }

    def get_event_group(self, event_name: str) -> str:
        for group, events in self.EVENT_GROUPS.items():
            if event_name in events:
                return group
        return 'other'

    def build_transitions_from_paths(self, paths_df: pd.DataFrame, 
                                      max_depth: int = 5) -> Dict[Tuple[str, str], int]:
        transitions = defaultdict(int)
        
        for _, row in paths_df.iterrows():
            path = row['path']
            count = row['count']
            events = path.split(' -> ')
            
            for i in range(min(len(events) - 1, max_depth - 1)):
                source = events[i]
                target = events[i + 1]
                transitions[(source, target)] += count
        
        return transitions

    def aggregate_low_frequency_paths(self, transitions: Dict[Tuple[str, str], int],
                                        threshold_pct: float = 1.0,
                                        group_by_category: bool = True) -> Dict:
        total_volume = sum(transitions.values())
        threshold = total_volume * threshold_pct / 100
        
        high_freq_transitions = {}
        low_freq_transitions = defaultdict(int)
        
        for (source, target), count in transitions.items():
            if count >= threshold:
                high_freq_transitions[(source, target)] = count
            else:
                if group_by_category:
                    source_group = self.get_event_group(source)
                    target_group = self.get_event_group(target)
                    low_freq_transitions[(source_group, target_group)] += count
                else:
                    low_freq_transitions[('其他', '其他')] += count
        
        aggregated_transitions = high_freq_transitions.copy()
        aggregated_transitions.update(low_freq_transitions)
        
        return {
            'transitions': aggregated_transitions,
            'low_freq_aggregated': dict(low_freq_transitions),
            'threshold_used': threshold
        }

    def create_grouped_sankey_data(self, paths_df: pd.DataFrame,
                                    max_depth: int = 5,
                                    low_freq_threshold: float = 1.0,
                                    collapse_groups: Optional[List[str]] = None,
                                    group_by_category: bool = True) -> Dict:
        raw_transitions = self.build_transitions_from_paths(paths_df, max_depth)
        
        aggregation_result = self.aggregate_low_frequency_paths(
            raw_transitions, low_freq_threshold, group_by_category
        )
        transitions = aggregation_result['transitions']
        
        nodes_set = set()
        for (source, target) in transitions.keys():
            nodes_set.add(source)
            nodes_set.add(target)
        
        nodes: List[SankeyNode] = []
        node_to_group = {}
        
        for node_name in nodes_set:
            group = self.get_event_group(node_name) if group_by_category else None
            is_collapsed = collapse_groups and group in collapse_groups
            is_aggregate = node_name in self.EVENT_GROUPS or node_name == '其他'
            
            children = []
            if group:
                children = [e for e in self.EVENT_GROUPS.get(group, []) if e in nodes_set]
            
            total_value = sum(
                count for (source, target), count in transitions.items()
                if source == node_name or target == node_name
            )
            
            nodes.append(SankeyNode(
                name=node_name,
                group=group,
                is_collapsed=is_collapsed,
                is_aggregate=is_aggregate,
                children=children,
                value=total_value
            ))
            node_to_group[node_name] = group
        
        links: List[SankeyLink] = []
        for (source, target), value in transitions.items():
            is_agg = (
                source in self.EVENT_GROUPS or 
                target in self.EVENT_GROUPS or 
                source == '其他' or 
                target == '其他'
            )
            links.append(SankeyLink(
                source=source,
                target=target,
                value=value,
                is_aggregate=is_agg
            ))
        
        node_list = sorted(nodes, key=lambda x: x.value, reverse=True)
        
        return {
            'nodes': [
                {
                    'name': n.name,
                    'group': n.group,
                    'is_collapsed': n.is_collapsed,
                    'is_aggregate': n.is_aggregate,
                    'children': n.children,
                    'value': n.value,
                    'itemStyle': {'color': self.GROUP_COLORS.get(n.group, '#9a60b4')}
                }
                for n in node_list
            ],
            'links': [
                {
                    'source': l.source,
                    'target': l.target,
                    'value': l.value,
                    'is_aggregate': l.is_aggregate,
                    'lineStyle': {
                        'color': self.GROUP_COLORS.get(self.get_event_group(l.source), '#9a60b4'),
                        'opacity': 0.4 if l.is_aggregate else 0.6
                    }
                }
                for l in links
            ],
            'groups': list(set(node_to_group.values())),
            'group_stats': self._get_group_stats(nodes, self.GROUP_COLORS),
            'aggregation_info': {
                'low_frequency_count': len(aggregation_result['low_freq_aggregated']),
                'threshold_pct': low_freq_threshold
            }
        }

    def _get_group_stats(self, nodes: List[SankeyNode], colors: Dict[str, str]) -> Dict:
        group_stats = defaultdict(lambda: {'count': 0, 'value': 0})
        
        for node in nodes:
            if node.group:
                group_stats[node.group]['count'] += 1
                group_stats[node.group]['value'] += node.value
        
        return {
            group: {
                'node_count': stats['count'],
                'total_value': stats['value'],
                'color': colors.get(group, '#9a60b4')
            }
            for group, stats in group_stats.items()
        }

    def get_expandable_groups(self, sankey_data: Dict) -> List[str]:
        return [
            group for group, stats in sankey_data.get('group_stats', {}).items()
            if stats['node_count'] > 1
        ]

    def expand_group(self, sankey_data: Dict, group_name: str) -> Dict:
        group_events = self.EVENT_GROUPS.get(group_name, [])
        
        nodes = sankey_data['nodes']
        links = sankey_data['links']
        
        new_nodes = []
        new_links = []
        
        group_node = next((n for n in nodes if n['name'] == group_name), None)
        if not group_node:
            return sankey_data
        
        for event in group_events:
            new_nodes.append({
                'name': event,
                'group': group_name,
                'is_collapsed': False,
                'is_aggregate': False,
                'children': [],
                'value': group_node['value'] // len(group_events) if group_events else group_node['value'],
                'itemStyle': {'color': self.GROUP_COLORS.get(group_name, '#9a60b4')}
            })
        
        for node in nodes:
            if node['name'] != group_name:
                new_nodes.append(node)
        
        for link in links:
            if link['source'] == group_name:
                for event in group_events:
                    new_links.append({
                        'source': event,
                        'target': link['target'],
                        'value': link['value'] // len(group_events) if group_events else link['value'],
                        'is_aggregate': False,
                        'lineStyle': {'color': self.GROUP_COLORS.get(group_name, '#9a60b4'), 'opacity': 0.6}
                    })
            elif link['target'] == group_name:
                for event in group_events:
                    new_links.append({
                        'source': link['source'],
                        'target': event,
                        'value': link['value'] // len(group_events) if group_events else link['value'],
                        'is_aggregate': False,
                        'lineStyle': {'color': self.GROUP_COLORS.get(self.get_event_group(link['source']), '#9a60b4'), 'opacity': 0.6}
                    })
            else:
                new_links.append(link)
        
        return {
            'nodes': new_nodes,
            'links': new_links,
            'groups': sankey_data['groups'],
            'group_stats': sankey_data['group_stats']
        }
