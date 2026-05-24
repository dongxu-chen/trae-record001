import networkx as nx
from typing import List, Dict, Any, Optional, Set
from deadlock_parser import Deadlock, Transaction, Lock
import json
import hashlib
from collections import defaultdict


class DeadlockGraphGenerator:
    def __init__(self):
        self.graph = nx.DiGraph()

    def generate_graph(self, deadlocks: List[Deadlock]) -> nx.DiGraph:
        self.graph.clear()

        for idx, deadlock in enumerate(deadlocks):
            self._add_deadlock_to_graph(deadlock, idx)

        return self.graph

    def _add_deadlock_to_graph(self, deadlock: Deadlock, deadlock_idx: int):
        deadlock_id = f"deadlock_{deadlock_idx}"
        timestamp = deadlock.timestamp.isoformat() if deadlock.timestamp else "unknown"

        self.graph.add_node(
            deadlock_id,
            type='deadlock',
            label=f"死锁 #{deadlock_idx + 1}",
            timestamp=timestamp,
            victims=deadlock.victim_txns
        )

        txn_nodes = {}
        for txn in deadlock.transactions:
            txn_node_id = f"txn_{deadlock_idx}_{txn.txn_id}"
            txn_nodes[txn.txn_id] = txn_node_id

            self.graph.add_node(
                txn_node_id,
                type='transaction',
                label=f"事务 {txn.txn_id}",
                txn_id=txn.txn_id,
                status=txn.status,
                is_victim=txn.txn_id in deadlock.victim_txns,
                sql_statements=txn.sql_statements,
                wait_time=txn.wait_time
            )

            self.graph.add_edge(
                deadlock_id,
                txn_node_id,
                type='involved',
                label='涉及'
            )

        for txn in deadlock.transactions:
            if txn.waiting_lock:
                self._add_wait_edge(txn, txn_nodes, deadlock_idx, deadlock.transactions)

            for lock in txn.holding_locks:
                self._add_lock_hold_edge(txn, lock, txn_nodes, deadlock_idx)

    def _add_wait_edge(self, waiting_txn: Transaction, txn_nodes: Dict[str, str],
                       deadlock_idx: int, all_transactions: List[Transaction]):
        waiting_lock = waiting_txn.waiting_lock
        if not waiting_lock:
            return

        waiting_txn_node = txn_nodes[waiting_txn.txn_id]
        lock_id = self._generate_lock_id(waiting_lock, deadlock_idx)

        lock_node_id = f"lock_{lock_id}"
        if lock_node_id not in self.graph:
            self.graph.add_node(
                lock_node_id,
                type='lock',
                label=f"{waiting_lock.lock_mode} on {waiting_lock.table_name}",
                lock_type=waiting_lock.lock_type,
                lock_mode=waiting_lock.lock_mode,
                table=waiting_lock.table_name,
                index=waiting_lock.index_name
            )

        self.graph.add_edge(
            waiting_txn_node,
            lock_node_id,
            type='waiting_for',
            label='等待',
            weight=2
        )

        for holder_txn in all_transactions:
            if holder_txn.txn_id == waiting_txn.txn_id:
                continue

            for held_lock in holder_txn.holding_locks:
                if self._locks_conflict(waiting_lock, held_lock):
                    holder_txn_node = txn_nodes[holder_txn.txn_id]
                    self.graph.add_edge(
                        lock_node_id,
                        holder_txn_node,
                        type='held_by',
                        label='被持有',
                        weight=2
                    )

    def _add_lock_hold_edge(self, txn: Transaction, lock: Lock,
                            txn_nodes: Dict[str, str], deadlock_idx: int):
        txn_node = txn_nodes[txn.txn_id]
        lock_id = self._generate_lock_id(lock, deadlock_idx)

        lock_node_id = f"lock_{lock_id}"
        if lock_node_id not in self.graph:
            self.graph.add_node(
                lock_node_id,
                type='lock',
                label=f"{lock.lock_mode} on {lock.table_name}",
                lock_type=lock.lock_type,
                lock_mode=lock.lock_mode,
                table=lock.table_name,
                index=lock.index_name
            )

        self.graph.add_edge(
            txn_node,
            lock_node_id,
            type='holds',
            label='持有',
            weight=1
        )

    def _generate_lock_id(self, lock: Lock, deadlock_idx: int) -> str:
        lock_str = f"{deadlock_idx}_{lock.lock_type}_{lock.lock_mode}_{lock.table_name}_{lock.index_name or 'no_index'}_{lock.record_info or 'no_record'}"
        return hashlib.md5(lock_str.encode()).hexdigest()[:12]

    def _locks_conflict(self, waiting_lock: Lock, held_lock: Lock) -> bool:
        if waiting_lock.table_name != held_lock.table_name:
            return False

        if waiting_lock.index_name and held_lock.index_name:
            if waiting_lock.index_name != held_lock.index_name:
                return False

        if waiting_lock.record_info and held_lock.record_info:
            if waiting_lock.record_info != held_lock.record_info:
                return False

        conflicting_modes = {
            ('X', 'S'), ('X', 'X'), ('X', 'IS'), ('X', 'IX'),
            ('S', 'X'), ('S', 'IX'),
            ('IS', 'X'),
            ('IX', 'X'), ('IX', 'S'),
            ('X,GAP', 'S'), ('X,GAP', 'X'),
            ('S,GAP', 'X')
        }

        w_mode = waiting_lock.lock_mode.upper()
        h_mode = held_lock.lock_mode.upper()

        if w_mode == h_mode and 'X' in w_mode:
            return True

        for (a, b) in conflicting_modes:
            if (a in w_mode and b in h_mode) or (a in h_mode and b in w_mode):
                return True

        return False

    def to_cytoscape_json(self, graph: Optional[nx.DiGraph] = None) -> Dict[str, Any]:
        if graph is None:
            graph = self.graph

        elements = []

        node_colors = {
            'deadlock': '#e74c3c',
            'transaction': '#3498db',
            'transaction_victim': '#e67e22',
            'lock': '#2ecc71'
        }

        edge_colors = {
            'involved': '#95a5a6',
            'waiting_for': '#e74c3c',
            'held_by': '#2ecc71',
            'holds': '#3498db'
        }

        for node_id, node_data in graph.nodes(data=True):
            node_type = node_data.get('type', 'unknown')
            color = node_colors.get(node_type, '#95a5a6')

            if node_type == 'transaction' and node_data.get('is_victim'):
                color = node_colors['transaction_victim']

            elements.append({
                'data': {
                    'id': node_id,
                    'label': node_data.get('label', node_id),
                    'type': node_type,
                    'color': color,
                    **{k: v for k, v in node_data.items() if k not in ['label', 'type']}
                }
            })

        for source, target, edge_data in graph.edges(data=True):
            edge_type = edge_data.get('type', 'unknown')
            color = edge_colors.get(edge_type, '#95a5a6')

            elements.append({
                'data': {
                    'id': f"{source}->{target}",
                    'source': source,
                    'target': target,
                    'label': edge_data.get('label', ''),
                    'type': edge_type,
                    'color': color,
                    'weight': edge_data.get('weight', 1)
                }
            })

        return {'elements': elements}

    def tarjan_scc(self, graph: Optional[nx.DiGraph] = None) -> List[List[str]]:
        """
        Tarjan强连通分量算法
        时间复杂度: O(V + E)，线性时间
        返回所有强连通分量，每个分量是节点列表
        """
        if graph is None:
            graph = self.graph

        index_counter = [0]
        stack = []
        lowlink = {}
        index = {}
        on_stack = defaultdict(bool)
        result = []

        nodes = list(graph.nodes())

        def strongconnect(node):
            index[node] = index_counter[0]
            lowlink[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True

            for successor in graph.successors(node):
                if successor not in index:
                    strongconnect(successor)
                    lowlink[node] = min(lowlink[node], lowlink[successor])
                elif on_stack[successor]:
                    lowlink[node] = min(lowlink[node], index[successor])

            if lowlink[node] == index[node]:
                scc = []
                while True:
                    successor = stack.pop()
                    on_stack[successor] = False
                    scc.append(successor)
                    if successor == node:
                        break
                result.append(scc)

        for node in nodes:
            if node not in index:
                strongconnect(node)

        return result

    def detect_cycles(self, graph: Optional[nx.DiGraph] = None) -> List[List[str]]:
        """
        使用Tarjan算法检测循环依赖
        只有大小>1的强连通分量才包含环
        """
        if graph is None:
            graph = self.graph

        sccs = self.tarjan_scc(graph)

        cycles = []
        for scc in sccs:
            if len(scc) > 1:
                has_txn_nodes = any(
                    graph.nodes[n].get('type') == 'transaction'
                    for n in scc
                )
                if has_txn_nodes:
                    cycles.append(scc)

        return cycles

    def detect_cycles_with_details(self, graph: Optional[nx.DiGraph] = None) -> List[Dict[str, Any]]:
        """
        检测循环依赖并返回详细信息
        """
        if graph is None:
            graph = self.graph

        cycles = self.detect_cycles(graph)
        detailed_cycles = []

        for cycle in cycles:
            txn_nodes = [n for n in cycle if graph.nodes[n].get('type') == 'transaction']
            lock_nodes = [n for n in cycle if graph.nodes[n].get('type') == 'lock']

            subgraph = graph.subgraph(cycle)

            cycle_path = self._find_cycle_path(subgraph, cycle)

            detailed_cycles.append({
                'nodes': cycle,
                'transaction_nodes': txn_nodes,
                'lock_nodes': lock_nodes,
                'transaction_count': len(txn_nodes),
                'lock_count': len(lock_nodes),
                'cycle_path': cycle_path,
                'is_deadlock': len(txn_nodes) >= 2,
                'description': self._generate_cycle_description(graph, cycle)
            })

        return detailed_cycles

    def _find_cycle_path(self, subgraph: nx.DiGraph, nodes: List[str]) -> List[str]:
        """
        在强连通分量中找到一个具体的环路径
        """
        if len(nodes) < 2:
            return nodes

        for start_node in nodes:
            try:
                cycle = nx.find_cycle(subgraph, source=start_node, orientation='original')
                if cycle:
                    path = [cycle[0][0]]
                    for edge in cycle:
                        path.append(edge[1])
                    return path
            except nx.NetworkXNoCycle:
                continue

        return nodes

    def _generate_cycle_description(self, graph: nx.DiGraph, cycle: List[str]) -> str:
        """
        生成环的文字描述
        """
        txn_names = []
        for node in cycle:
            node_data = graph.nodes[node]
            if node_data.get('type') == 'transaction':
                name = node_data.get('label', node)
                if node_data.get('is_victim'):
                    name += ' (被回滚)'
                txn_names.append(name)

        if len(txn_names) >= 2:
            return ' → '.join(txn_names) + ' → ' + txn_names[0]
        elif len(txn_names) == 1:
            return f"单个事务自依赖: {txn_names[0]}"
        else:
            return '锁依赖环'

    def get_graph_statistics(self, graph: Optional[nx.DiGraph] = None) -> Dict[str, Any]:
        if graph is None:
            graph = self.graph

        cycles = self.detect_cycles_with_details(graph)
        sccs = self.tarjan_scc(graph)
        scc_count = sum(1 for scc in sccs if len(scc) > 1)

        txn_count = sum(1 for n in graph.nodes if graph.nodes[n].get('type') == 'transaction')
        lock_count = sum(1 for n in graph.nodes if graph.nodes[n].get('type') == 'lock')
        deadlock_count = sum(1 for n in graph.nodes if graph.nodes[n].get('type') == 'deadlock')

        stats = {
            'nodes': graph.number_of_nodes(),
            'nodes_count': graph.number_of_nodes(),
            'edges': graph.number_of_edges(),
            'edges_count': graph.number_of_edges(),
            'transactions': txn_count,
            'locks': lock_count,
            'deadlocks': deadlock_count,
            'cycles_count': len(cycles),
            'scc_count': scc_count,
            'cycles': cycles,
            'is_connected': nx.is_weakly_connected(graph) if graph.nodes else False,
            'strongly_connected_components': len(self.tarjan_scc(graph)),
            'algorithm': 'tarjan_scc'
        }

        for _, node_data in graph.nodes(data=True):
            node_type = node_data.get('type', '')
            if node_type == 'transaction':
                stats['transactions'] += 1
            elif node_type == 'lock':
                stats['locks'] += 1
            elif node_type == 'deadlock':
                stats['deadlocks'] += 1

        return stats
