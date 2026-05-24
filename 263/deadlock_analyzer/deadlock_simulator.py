#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
死锁回放模拟模块
模拟事务执行，修改事务顺序验证死锁是否消除
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import networkx as nx
from deadlock_parser import Deadlock, Transaction, Lock


@dataclass
class SimulatedOperation:
    txn_id: str
    operation_type: str
    table_name: str
    lock_mode: str
    sql: str
    index_name: Optional[str] = None
    record_info: Optional[str] = None
    timestamp: float = 0.0
    is_waiting: bool = False
    is_completed: bool = False


@dataclass
class SimulationStep:
    step_number: int
    time: float
    operations: List[SimulatedOperation]
    description: str
    is_deadlock: bool = False
    wait_graph: Optional[Dict[str, Any]] = None


@dataclass
class SimulationResult:
    original_deadlock: bool
    optimized_deadlock: bool
    original_steps: List[SimulationStep]
    optimized_steps: List[SimulationStep]
    original_cycle: Optional[List[str]]
    optimized_cycle: Optional[List[str]]
    optimization_applied: str
    is_fixed: bool
    recommendations: List[str]
    statistics: Dict[str, Any] = field(default_factory=dict)
    original_has_deadlock: bool = False
    optimized_has_deadlock: bool = False
    optimized_wait_time: float = 0.0
    optimization_note: str = ''

    def __post_init__(self):
        self.original_has_deadlock = self.original_deadlock
        self.optimized_has_deadlock = self.optimized_deadlock
        if not self.optimization_note and self.optimization_applied:
            self.optimization_note = self.optimization_applied
        if self.optimized_steps:
            total_wait = sum(
                sum(op.timestamp for op in step.operations if op.is_waiting)
                for step in self.optimized_steps
            )
            self.optimized_wait_time = round(total_wait, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_deadlock": self.original_deadlock,
            "optimized_deadlock": self.optimized_deadlock,
            "original_has_deadlock": self.original_has_deadlock,
            "optimized_has_deadlock": self.optimized_has_deadlock,
            "optimized_wait_time": self.optimized_wait_time,
            "optimization_note": self.optimization_note,
            "original_cycle": self.original_cycle,
            "optimized_cycle": self.optimized_cycle,
            "optimization_applied": self.optimization_applied,
            "is_fixed": self.is_fixed,
            "recommendations": self.recommendations,
            "statistics": self.statistics,
            "original_steps_count": len(self.original_steps),
            "optimized_steps_count": len(self.optimized_steps)
        }


class DeadlockSimulator:
    def __init__(self):
        self._lock_table: Dict[str, Dict[str, str]] = defaultdict(dict)
        self._wait_queue: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self._txn_locks: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self._time = 0.0

    def _reset(self):
        self._lock_table.clear()
        self._wait_queue.clear()
        self._txn_locks.clear()
        self._time = 0.0

    def simulate_deadlock(self, deadlock: Deadlock,
                          custom_order: Optional[Dict[str, int]] = None) -> SimulationResult:
        original_steps = self._simulate(deadlock)
        original_has_deadlock = self._detect_deadlock_in_steps(original_steps)
        original_cycle = self._extract_cycle_from_steps(original_steps) if original_has_deadlock else None

        optimized_order = custom_order or self._generate_optimized_order(deadlock)
        optimized_steps = self._simulate(deadlock, custom_order=optimized_order)
        optimized_has_deadlock = self._detect_deadlock_in_steps(optimized_steps)
        optimized_cycle = self._extract_cycle_from_steps(optimized_steps) if optimized_has_deadlock else None

        is_fixed = original_has_deadlock and not optimized_has_deadlock

        recommendations = self._generate_recommendations(
            deadlock, optimized_order, is_fixed, original_has_deadlock
        )

        return SimulationResult(
            original_deadlock=original_has_deadlock,
            optimized_deadlock=optimized_has_deadlock,
            original_steps=original_steps,
            optimized_steps=optimized_steps,
            original_cycle=original_cycle,
            optimized_cycle=optimized_cycle,
            optimization_applied=self._describe_optimization(deadlock, optimized_order),
            is_fixed=is_fixed,
            recommendations=recommendations,
            statistics={
                "original_locks": sum(1 for s in original_steps for op in s.operations if not op.is_waiting),
                "original_waits": sum(1 for s in original_steps for op in s.operations if op.is_waiting),
                "optimized_locks": sum(1 for s in optimized_steps for op in s.operations if not op.is_waiting),
                "optimized_waits": sum(1 for s in optimized_steps for op in s.operations if op.is_waiting),
                "deadlock_fixed": is_fixed,
                "total_transactions": len(deadlock.transactions)
            }
        )

    def _simulate(self, deadlock: Deadlock,
                  custom_order: Optional[Dict[str, int]] = None) -> List[SimulationStep]:
        self._reset()
        steps = []
        operations = self._extract_operations(deadlock)

        if custom_order:
            operations.sort(key=lambda op: (
                custom_order.get(op.txn_id, 0),
                op.timestamp
            ))

        step_number = 0
        for i, op in enumerate(operations):
            step_number += 1
            self._time = op.timestamp

            lock_key = f"{op.table_name}_{op.index_name or 'default'}_{op.record_info or 'default'}"

            can_acquire, conflict_txn = self._can_acquire_lock(lock_key, op.txn_id, op.lock_mode)

            if can_acquire:
                self._acquire_lock(lock_key, op.txn_id, op.lock_mode)
                op.is_completed = True
                description = f"事务 {op.txn_id} 成功获取 {op.lock_mode} 锁 on {op.table_name}"
            else:
                op.is_waiting = True
                self._add_to_wait_queue(lock_key, op.txn_id, op.lock_mode)
                description = f"事务 {op.txn_id} 等待 {op.lock_mode} 锁 on {op.table_name} (被 {conflict_txn} 持有)"

            wait_graph = self._build_wait_graph_for_step(operations[:i + 1])
            has_deadlock = self._detect_cycle_in_graph(wait_graph)

            step = SimulationStep(
                step_number=step_number,
                time=self._time,
                operations=[op],
                description=description,
                is_deadlock=has_deadlock,
                wait_graph={
                    "nodes": list(wait_graph.nodes()),
                    "edges": [{"from": e[0], "to": e[1]} for e in wait_graph.edges()]
                } if wait_graph.nodes() else None
            )
            steps.append(step)

            if has_deadlock:
                break

        return steps

    def _extract_operations(self, deadlock: Deadlock) -> List[SimulatedOperation]:
        operations = []
        time_offset = 0.0

        for txn in deadlock.transactions:
            txn_time = time_offset

            for lock in txn.holding_locks:
                op = SimulatedOperation(
                    txn_id=txn.txn_id,
                    operation_type='ACQUIRE',
                    table_name=lock.table_name,
                    lock_mode=lock.lock_mode,
                    sql=txn.sql_statements[0] if txn.sql_statements else '',
                    index_name=lock.index_name,
                    record_info=lock.record_info,
                    timestamp=txn_time
                )
                operations.append(op)
                txn_time += 0.1

            if txn.waiting_lock:
                op = SimulatedOperation(
                    txn_id=txn.txn_id,
                    operation_type='REQUEST',
                    table_name=txn.waiting_lock.table_name,
                    lock_mode=txn.waiting_lock.lock_mode,
                    sql=txn.sql_statements[-1] if txn.sql_statements else '',
                    index_name=txn.waiting_lock.index_name,
                    record_info=txn.waiting_lock.record_info,
                    timestamp=txn_time + 0.05
                )
                operations.append(op)

            time_offset += 0.5

        return operations

    def _can_acquire_lock(self, lock_key: str, txn_id: str, lock_mode: str) -> Tuple[bool, Optional[str]]:
        if lock_key not in self._lock_table:
            return True, None

        current_holder = self._lock_table[lock_key]
        if current_holder['txn_id'] == txn_id:
            return True, None

        if self._locks_compatible(current_holder['mode'], lock_mode):
            return True, None

        return False, current_holder['txn_id']

    def _locks_compatible(self, held_mode: str, requested_mode: str) -> bool:
        held = held_mode.upper()
        requested = requested_mode.upper()

        if 'IS' in held and 'IS' in requested:
            return True
        if 'IS' in held and requested == 'S':
            return True

        if 'S' in held and 'IS' in requested:
            return True
        if 'S' in held and 'S' in requested:
            return True

        return False

    def _acquire_lock(self, lock_key: str, txn_id: str, lock_mode: str):
        if lock_key in self._lock_table:
            current = self._lock_table[lock_key]
            if current['txn_id'] == txn_id:
                if 'X' in lock_mode:
                    current['mode'] = lock_mode
                return

        self._lock_table[lock_key] = {
            'txn_id': txn_id,
            'mode': lock_mode
        }
        self._txn_locks[txn_id].append((lock_key, lock_mode))

    def _add_to_wait_queue(self, lock_key: str, txn_id: str, lock_mode: str):
        self._wait_queue[lock_key].append((txn_id, lock_mode))

    def _build_wait_graph_for_step(self, operations: List[SimulatedOperation]) -> nx.DiGraph:
        graph = nx.DiGraph()

        lock_holders: Dict[str, str] = {}
        for op in operations:
            lock_key = f"{op.table_name}_{op.index_name or 'default'}_{op.record_info or 'default'}"
            if not op.is_waiting and op.is_completed:
                lock_holders[lock_key] = op.txn_id

        for op in operations:
            if op.is_waiting:
                lock_key = f"{op.table_name}_{op.index_name or 'default'}_{op.record_info or 'default'}"
                holder = lock_holders.get(lock_key)
                if holder:
                    graph.add_node(op.txn_id, type='transaction')
                    graph.add_node(holder, type='transaction')
                    graph.add_edge(op.txn_id, holder, type='waiting_for')

        return graph

    def _detect_cycle_in_graph(self, graph: nx.DiGraph) -> bool:
        if graph.number_of_nodes() < 2:
            return False

        try:
            cycles = list(nx.simple_cycles(graph))
            return any(len(cycle) >= 2 for cycle in cycles)
        except nx.NetworkXNoCycle:
            return False

    def _detect_deadlock_in_steps(self, steps: List[SimulationStep]) -> bool:
        return any(step.is_deadlock for step in steps)

    def _extract_cycle_from_steps(self, steps: List[SimulationStep]) -> Optional[List[str]]:
        for step in reversed(steps):
            if step.is_deadlock and step.wait_graph:
                nodes = step.wait_graph.get('nodes', [])
                edges = step.wait_graph.get('edges', [])
                if len(nodes) >= 2:
                    g = nx.DiGraph()
                    g.add_nodes_from(nodes)
                    for e in edges:
                        g.add_edge(e['from'], e['to'])
                    try:
                        cycles = list(nx.simple_cycles(g))
                        if cycles:
                            return cycles[0]
                    except nx.NetworkXNoCycle:
                        pass
        return None

    def _generate_optimized_order(self, deadlock: Deadlock) -> Dict[str, int]:
        table_access_order = self._analyze_table_access_order(deadlock)

        sorted_tables = sorted(table_access_order.keys())

        order = {}
        for txn in deadlock.transactions:
            txn_tables = self._get_txn_tables(txn)
            min_order = min(
                (sorted_tables.index(t) for t in txn_tables if t in sorted_tables),
                default=len(sorted_tables)
            )
            order[txn.txn_id] = min_order * 10 + hash(txn.txn_id) % 10

        return order

    def _analyze_table_access_order(self, deadlock: Deadlock) -> Dict[str, List[str]]:
        table_txns: Dict[str, List[str]] = defaultdict(list)

        for txn in deadlock.transactions:
            tables = self._get_txn_tables(txn)
            for table in tables:
                if txn.txn_id not in table_txns[table]:
                    table_txns[table].append(txn.txn_id)

        return dict(table_txns)

    def _get_txn_tables(self, txn: Transaction) -> List[str]:
        tables = []
        for lock in txn.holding_locks:
            if lock.table_name not in tables:
                tables.append(lock.table_name)
        if txn.waiting_lock and txn.waiting_lock.table_name not in tables:
            tables.append(txn.waiting_lock.table_name)
        return tables

    def _describe_optimization(self, deadlock: Deadlock, order: Dict[str, int]) -> str:
        sorted_txns = sorted(order.keys(), key=lambda x: order[x])

        descriptions = []
        for txn_id in sorted_txns:
            txn = next((t for t in deadlock.transactions if t.txn_id == txn_id), None)
            if txn:
                tables = self._get_txn_tables(txn)
                descriptions.append(f"{txn_id}: {', '.join(tables)}")

        return "统一表访问顺序: " + " → ".join(descriptions)

    def _generate_recommendations(self, deadlock: Deadlock,
                                   optimized_order: Dict[str, int],
                                   is_fixed: bool,
                                   has_deadlock: bool) -> List[str]:
        recommendations = []

        if is_fixed:
            recommendations.append("✅ 修改事务顺序成功消除死锁！")
            sorted_txns = sorted(optimized_order.keys(), key=lambda x: optimized_order[x])
            recommendations.append(f"建议的事务执行顺序: {' → '.join(sorted_txns)}")

            all_tables = set()
            for txn in deadlock.transactions:
                all_tables.update(self._get_txn_tables(txn))
            sorted_tables = sorted(all_tables)
            recommendations.append(f"建议的表访问顺序: {' → '.join(sorted_tables)}")

        elif has_deadlock:
            recommendations.append("⚠️  修改事务顺序未能完全消除死锁")
            recommendations.append("建议尝试以下方案:")
            recommendations.append("1. 缩小事务范围，减少锁持有时间")
            recommendations.append("2. 为查询添加合适的索引，减少锁范围")
            recommendations.append("3. 降低事务隔离级别到READ COMMITTED")
            recommendations.append("4. 考虑使用SELECT ... FOR UPDATE SKIP LOCKED")
            recommendations.append("5. 将大事务拆分为多个小事务")

            conflicts = self._analyze_conflicts(deadlock)
            if conflicts:
                recommendations.append("检测到的冲突点:")
                for conflict in conflicts[:3]:
                    recommendations.append(f"  - {conflict}")

        else:
            recommendations.append("ℹ️ 原始日志中未检测到死锁")

        recommendations.append("💡 可以尝试使用EXPLAIN分析模块检查SQL执行计划，添加合适的索引")

        return recommendations

    def _analyze_conflicts(self, deadlock: Deadlock) -> List[str]:
        conflicts = []

        for i, txn1 in enumerate(deadlock.transactions):
            for txn2 in deadlock.transactions[i + 1:]:
                if txn1.waiting_lock and txn2.waiting_lock:
                    txn1_tables = self._get_txn_tables(txn1)
                    txn2_tables = self._get_txn_tables(txn2)

                    common_tables = set(txn1_tables) & set(txn2_tables)
                    if common_tables:
                        order1 = [t for t in txn1_tables if t in common_tables]
                        order2 = [t for t in txn2_tables if t in common_tables]

                        if order1 and order2 and order1[0] != order2[0]:
                            conflicts.append(
                                f"事务 {txn1.txn_id} 和 {txn2.txn_id} 以相反顺序访问表: "
                                f"{order1[0]} vs {order2[0]}"
                            )

        return conflicts

    def generate_order_variations(self, deadlock: Deadlock) -> List[Dict[str, int]]:
        variations = []

        txn_ids = [t.txn_id for t in deadlock.transactions]

        if len(txn_ids) == 2:
            variations.append({txn_ids[0]: 0, txn_ids[1]: 1})
            variations.append({txn_ids[0]: 1, txn_ids[1]: 0})
            variations.append(self._generate_optimized_order(deadlock))

        elif len(txn_ids) >= 3:
            variations.append(self._generate_optimized_order(deadlock))
            for i, txn_id in enumerate(txn_ids):
                order = {t: i for i, t in enumerate(txn_ids)}
                order[txn_id] = 0
                variations.append(order)

        return variations

    def test_multiple_orders(self, deadlock: Deadlock) -> List[Dict[str, Any]]:
        variations = self.generate_order_variations(deadlock)
        results = []
        txn_ids = [txn.txn_id for txn in deadlock.transactions]
        original_order_dict = {tid: i for i, tid in enumerate(txn_ids)}

        for i, order_dict in enumerate(variations):
            result = self.simulate_deadlock(deadlock, custom_order=order_dict)
            is_original = (order_dict == original_order_dict)
            is_optimized = False
            
            sorted_txns = sorted(order_dict.items(), key=lambda x: x[1])
            transaction_order = [tid for tid, _ in sorted_txns]
            
            if i == 0:
                has_deadlock = result.original_deadlock
            else:
                has_deadlock = result.optimized_deadlock
            
            if not has_deadlock and not is_original:
                is_optimized = True
            
            results.append({
                "order_id": i,
                "order": order_dict,
                "transaction_order": transaction_order,
                "is_deadlock": has_deadlock,
                "has_deadlock": has_deadlock,
                "is_original": is_original,
                "is_optimized": is_optimized,
                "description": self._describe_optimization(deadlock, order_dict),
                "is_fixed": result.is_fixed if result.original_deadlock else None
            })

        return results
