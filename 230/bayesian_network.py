import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict, deque
from itertools import product
import random
from typing import Dict, List, Tuple, Set, Optional, Union


class Node:
    def __init__(self, name: str, states: List[str]):
        self.name = name
        self.states = states
        self.state_to_idx = {state: idx for idx, state in enumerate(states)}
        self.n_states = len(states)

    def __repr__(self):
        return f"Node({self.name}, states={self.states})"


class CPT:
    def __init__(self, node: Node, parents: List[Node] = None):
        self.node = node
        self.parents = parents if parents else []
        self.table = None
        self._initialize_table()

    def _initialize_table(self):
        parent_dims = [p.n_states for p in self.parents]
        shape = tuple(parent_dims) + (self.node.n_states,)
        self.table = np.zeros(shape)

    def set_probability(self, parent_assignments: Dict[str, str],
                        node_state: str, prob: float):
        parent_indices = []
        for parent in self.parents:
            if parent.name not in parent_assignments:
                raise ValueError(f"Missing assignment for parent {parent.name}")
            parent_indices.append(parent.state_to_idx[parent_assignments[parent.name]])

        node_idx = self.node.state_to_idx[node_state]
        self.table[tuple(parent_indices) + (node_idx,)] = prob

    def get_probability(self, parent_assignments: Dict[str, str],
                        node_state: str) -> float:
        parent_indices = []
        for parent in self.parents:
            if parent.name not in parent_assignments:
                raise ValueError(f"Missing assignment for parent {parent.name}")
            parent_indices.append(parent.state_to_idx[parent_assignments[parent.name]])

        node_idx = self.node.state_to_idx[node_state]
        return self.table[tuple(parent_indices) + (node_idx,)]

    def normalize(self):
        parent_dims = [p.n_states for p in self.parents]
        for idx in product(*[range(d) for d in parent_dims]):
            row = self.table[idx]
            row_sum = row.sum()
            if row_sum > 0:
                self.table[idx] = row / row_sum

    def __repr__(self):
        return f"CPT(node={self.node.name}, parents={[p.name for p in self.parents]})"


class BayesianNetwork:
    def __init__(self, name: str = "BayesianNetwork"):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Tuple[str, str]] = []
        self.cpts: Dict[str, CPT] = {}
        self.parents: Dict[str, List[str]] = defaultdict(list)
        self.children: Dict[str, List[str]] = defaultdict(list)
        self.graph = nx.DiGraph()

    def add_node(self, name: str, states: List[str]):
        if name in self.nodes:
            raise ValueError(f"Node {name} already exists")
        node = Node(name, states)
        self.nodes[name] = node
        self.graph.add_node(name)
        self.cpts[name] = CPT(node)

    def add_edge(self, parent: str, child: str):
        if parent not in self.nodes or child not in self.nodes:
            raise ValueError("Both nodes must exist in the network")

        self.edges.append((parent, child))
        self.parents[child].append(parent)
        self.children[parent].append(child)
        self.graph.add_edge(parent, child)

        if self._has_cycle():
            self.edges.pop()
            self.parents[child].pop()
            self.children[parent].pop()
            self.graph.remove_edge(parent, child)
            raise ValueError("Adding this edge would create a cycle")

        self._rebuild_cpt(child)

    def _has_cycle(self) -> bool:
        try:
            nx.find_cycle(self.graph)
            return True
        except nx.NetworkXNoCycle:
            return False

    def _rebuild_cpt(self, node_name: str):
        node = self.nodes[node_name]
        parent_nodes = [self.nodes[p] for p in self.parents[node_name]]
        old_cpt = self.cpts[node_name]
        new_cpt = CPT(node, parent_nodes)

        if old_cpt.table is not None and old_cpt.table.size > 0:
            parent_dims = [p.n_states for p in parent_nodes]
            for idx in product(*[range(d) for d in parent_dims]):
                new_cpt.table[idx] = old_cpt.table[idx]

        self.cpts[node_name] = new_cpt

    def set_cpt(self, node_name: str, cpt_data: Dict):
        if node_name not in self.nodes:
            raise ValueError(f"Node {node_name} does not exist")

        cpt = self.cpts[node_name]

        if isinstance(cpt_data, np.ndarray):
            if cpt_data.shape != cpt.table.shape:
                raise ValueError(f"CPT shape mismatch: expected {cpt.table.shape}, got {cpt_data.shape}")
            cpt.table = cpt_data.copy()
        else:
            for key, prob in cpt_data.items():
                if isinstance(key, tuple):
                    parent_vals, node_state = key[:-1], key[-1]
                    parent_assignments = {self.parents[node_name][i]: parent_vals[i]
                                          for i in range(len(parent_vals))}
                else:
                    parent_assignments = {}
                    node_state = key
                cpt.set_probability(parent_assignments, node_state, prob)

        cpt.normalize()

    def get_cpt(self, node_name: str) -> CPT:
        return self.cpts[node_name]

    def topological_order(self) -> List[str]:
        return list(nx.topological_sort(self.graph))

    def sample(self, n_samples: int = 1) -> List[Dict[str, str]]:
        samples = []
        topo_order = self.topological_order()

        for _ in range(n_samples):
            assignment = {}
            for node_name in topo_order:
                node = self.nodes[node_name]
                cpt = self.cpts[node_name]

                parent_assignments = {p: assignment[p] for p in self.parents[node_name]}
                parent_indices = [self.nodes[p].state_to_idx[assignment[p]]
                                  for p in self.parents[node_name]]

                probs = cpt.table[tuple(parent_indices)] if parent_indices else cpt.table

                state_idx = np.random.choice(node.n_states, p=probs)
                assignment[node_name] = node.states[state_idx]

            samples.append(assignment)

        return samples

    def variable_elimination(self, query: List[str],
                             evidence: Dict[str, str] = None,
                             heuristic: str = 'min_degree') -> Dict[str, Dict[str, float]]:
        evidence = evidence or {}

        factors = self._create_factors(evidence)
        elimination_order = self._get_elimination_order(query, evidence, heuristic)

        for var in elimination_order:
            if var not in query and var not in evidence:
                factors = self._sum_out(var, factors)

        final_factor = self._multiply_factors(factors)
        result = self._normalize_factor(final_factor, query)

        return result

    def _create_factors(self, evidence: Dict[str, str]) -> List[Dict]:
        factors = []
        for node_name in self.nodes:
            node = self.nodes[node_name]
            cpt = self.cpts[node_name]

            scope = self.parents[node_name] + [node_name]
            factor = {
                'scope': scope,
                'table': cpt.table.copy()
            }

            for ev_name, ev_state in evidence.items():
                if ev_name in scope:
                    factor = self._reduce_factor(factor, ev_name, ev_state)

            if len(factor['scope']) > 0:
                factors.append(factor)

        return factors

    def _reduce_factor(self, factor: Dict, var_name: str, state: str) -> Dict:
        if var_name not in factor['scope']:
            return factor

        var_idx = factor['scope'].index(var_name)
        var = self.nodes[var_name]
        state_idx = var.state_to_idx[state]

        new_scope = [v for v in factor['scope'] if v != var_name]
        new_table = np.take(factor['table'], state_idx, axis=var_idx)

        return {'scope': new_scope, 'table': new_table}

    def _get_elimination_order(self, query: List[str], evidence: Dict[str, str],
                               heuristic: str = 'min_degree') -> List[str]:
        all_vars = set(self.nodes.keys())
        query_set = set(query)
        evidence_set = set(evidence.keys())
        eliminate_vars = list(all_vars - query_set - evidence_set)

        if heuristic == 'random':
            random.shuffle(eliminate_vars)
            return eliminate_vars
        elif heuristic == 'min_degree':
            return self._min_degree_heuristic(eliminate_vars, query, evidence)
        elif heuristic == 'min_fill':
            return self._min_fill_heuristic(eliminate_vars, query, evidence)
        else:
            return eliminate_vars

    def _min_degree_heuristic(self, eliminate_vars: List[str],
                              query: List[str], evidence: Dict[str, str]) -> List[str]:
        adjacency = defaultdict(set)
        for node_name in self.nodes:
            if node_name in evidence:
                continue
            parents = [p for p in self.parents[node_name] if p not in evidence]
            children = [c for c in self.children[node_name] if c not in evidence]
            for p in parents:
                adjacency[node_name].add(p)
                adjacency[p].add(node_name)
            for c in children:
                adjacency[node_name].add(c)
                adjacency[c].add(node_name)

        remaining = set(eliminate_vars)
        order = []

        while remaining:
            min_degree = float('inf')
            best_var = None

            for var in remaining:
                active_neighbors = adjacency[var] & (remaining | set(query) - set(evidence.keys()))
                degree = len(active_neighbors)
                if degree < min_degree:
                    min_degree = degree
                    best_var = var

            order.append(best_var)
            remaining.remove(best_var)

            neighbors = adjacency[best_var]
            for n1 in neighbors:
                for n2 in neighbors:
                    if n1 != n2:
                        adjacency[n1].add(n2)
                        adjacency[n2].add(n1)

        return order

    def _min_fill_heuristic(self, eliminate_vars: List[str],
                            query: List[str], evidence: Dict[str, str]) -> List[str]:
        adjacency = defaultdict(set)
        for node_name in self.nodes:
            if node_name in evidence:
                continue
            parents = [p for p in self.parents[node_name] if p not in evidence]
            children = [c for c in self.children[node_name] if c not in evidence]
            for p in parents:
                adjacency[node_name].add(p)
                adjacency[p].add(node_name)
            for c in children:
                adjacency[node_name].add(c)
                adjacency[c].add(node_name)

        remaining = set(eliminate_vars)
        order = []

        while remaining:
            min_fill = float('inf')
            best_var = None

            for var in remaining:
                neighbors = adjacency[var] & (remaining | set(query) - set(evidence.keys()))
                fill_count = 0
                neighbor_list = list(neighbors)
                for i in range(len(neighbor_list)):
                    for j in range(i + 1, len(neighbor_list)):
                        if neighbor_list[j] not in adjacency[neighbor_list[i]]:
                            fill_count += 1

                if fill_count < min_fill:
                    min_fill = fill_count
                    best_var = var

            order.append(best_var)
            remaining.remove(best_var)

            neighbors = adjacency[best_var]
            for n1 in neighbors:
                for n2 in neighbors:
                    if n1 != n2:
                        adjacency[n1].add(n2)
                        adjacency[n2].add(n1)

        return order

    def _sum_out(self, var: str, factors: List[Dict]) -> List[Dict]:
        var_factors = [f for f in factors if var in f['scope']]
        other_factors = [f for f in factors if var not in f['scope']]

        if not var_factors:
            return factors

        product = self._multiply_factors(var_factors)

        var_idx = product['scope'].index(var)
        new_scope = [v for v in product['scope'] if v != var]
        new_table = np.sum(product['table'], axis=var_idx)

        other_factors.append({'scope': new_scope, 'table': new_table})
        return other_factors

    def _multiply_factors(self, factors: List[Dict]) -> Dict:
        if not factors:
            return {'scope': [], 'table': np.array([1.0])}

        result = factors[0]
        for factor in factors[1:]:
            result = self._multiply_two_factors(result, factor)

        return result

    def _multiply_two_factors(self, f1: Dict, f2: Dict) -> Dict:
        common_vars = list(set(f1['scope']) & set(f2['scope']))

        if not common_vars:
            new_scope = f1['scope'] + f2['scope']
            new_table = np.outer(f1['table'].flatten(), f2['table'].flatten())
            shape1 = f1['table'].shape
            shape2 = f2['table'].shape
            new_table = new_table.reshape(shape1 + shape2)
            return {'scope': new_scope, 'table': new_table}

        all_vars = f1['scope'].copy()
        for var in f2['scope']:
            if var not in all_vars:
                all_vars.append(var)

        f1_expanded = self._expand_factor(f1, all_vars)
        f2_expanded = self._expand_factor(f2, all_vars)

        new_table = f1_expanded['table'] * f2_expanded['table']
        return {'scope': all_vars, 'table': new_table}

    def _expand_factor(self, factor: Dict, target_scope: List[str]) -> Dict:
        new_shape = []
        transpose_order = []
        current_dims = {}

        for i, var in enumerate(factor['scope']):
            current_dims[var] = i

        for var in target_scope:
            if var in current_dims:
                transpose_order.append(current_dims[var])
            else:
                transpose_order.append(-1)

        new_table = factor['table'].transpose(transpose_order)

        for i, var in enumerate(target_scope):
            if var not in current_dims:
                new_table = np.expand_dims(new_table, axis=i)
                new_table = np.repeat(new_table, self.nodes[var].n_states, axis=i)
            new_shape.append(self.nodes[var].n_states)

        return {'scope': target_scope, 'table': new_table.reshape(tuple(new_shape))}

    def _normalize_factor(self, factor: Dict, query: List[str]) -> Dict[str, Dict[str, float]]:
        result = {}

        for q_var in query:
            other_vars = [v for v in factor['scope'] if v != q_var]
            if other_vars:
                axes = tuple(factor['scope'].index(v) for v in other_vars)
                marginal = np.sum(factor['table'], axis=axes)
            else:
                marginal = factor['table']

            marginal = marginal / marginal.sum()
            node = self.nodes[q_var]
            result[q_var] = {node.states[i]: float(marginal[i]) for i in range(node.n_states)}

        return result

    def gibbs_sampling(self, query: List[str], evidence: Dict[str, str] = None,
                       n_samples: int = 10000, burn_in: int = 1000,
                       n_chains: int = 3, check_convergence: bool = True,
                       gr_threshold: float = 1.05, max_iter: int = 10) -> Dict[str, Dict[str, float]]:
        evidence = evidence or {}

        if check_convergence and n_chains < 2:
            raise ValueError("Gelman-Rubin诊断需要至少2条链")

        non_evidence = [v for v in self.nodes.keys() if v not in evidence]

        chains_samples = []
        chains_assignments = []

        for chain_idx in range(n_chains):
            assignment = evidence.copy()
            for var in non_evidence:
                node = self.nodes[var]
                assignment[var] = node.states[np.random.randint(node.n_states)]
            chains_assignments.append(assignment.copy())
            chains_samples.append([])

        total_samples = n_samples
        iteration = 0

        while iteration < max_iter:
            iteration += 1

            for chain_idx in range(n_chains):
                assignment = chains_assignments[chain_idx]
                samples = []

                for sample_idx in range(total_samples + burn_in):
                    for var in non_evidence:
                        prob_dist = self._gibbs_probability(var, assignment)
                        state = np.random.choice(list(prob_dist.keys()), p=list(prob_dist.values()))
                        assignment[var] = state

                    if sample_idx >= burn_in:
                        samples.append({q_var: assignment[q_var] for q_var in query})

                chains_samples[chain_idx].extend(samples)
                chains_assignments[chain_idx] = assignment

            if check_convergence:
                gr_stats = self._gelman_rubin_diagnostic(chains_samples, query)
                converged = all(gr < gr_threshold for gr in gr_stats.values())

                if converged:
                    break
                else:
                    total_samples = n_samples * 2

        all_samples = []
        for chain in chains_samples:
            all_samples.extend(chain)

        counts = defaultdict(lambda: defaultdict(int))
        for sample in all_samples:
            for q_var in query:
                counts[q_var][sample[q_var]] += 1

        result = {}
        for q_var in query:
            total = sum(counts[q_var].values())
            node = self.nodes[q_var]
            result[q_var] = {state: counts[q_var].get(state, 0) / total
                             for state in node.states}

        return result

    def _gelman_rubin_diagnostic(self, chains_samples: List[List[Dict]],
                                 query: List[str]) -> Dict[str, float]:
        n_chains = len(chains_samples)
        if n_chains < 2:
            return {var: float('inf') for var in query}

        n_per_chain = len(chains_samples[0])
        if n_per_chain < 2:
            return {var: float('inf') for var in query}

        gr_stats = {}

        for var in query:
            node = self.nodes[var]
            state_to_idx = node.state_to_idx

            chains_numeric = []
            for chain in chains_samples:
                numeric = [state_to_idx[s[var]] for s in chain]
                chains_numeric.append(numeric)

            chains_numeric = np.array(chains_numeric)

            chain_means = np.mean(chains_numeric, axis=1)
            chain_vars = np.var(chains_numeric, axis=1, ddof=1)

            grand_mean = np.mean(chain_means)

            B = n_per_chain / (n_chains - 1) * np.sum((chain_means - grand_mean) ** 2)
            W = np.mean(chain_vars)

            var_hat = (n_per_chain - 1) / n_per_chain * W + B / n_per_chain

            if W == 0:
                gr_stats[var] = 1.0
            else:
                gr_stats[var] = np.sqrt(var_hat / W)

        return gr_stats

    def _gibbs_probability(self, var: str, assignment: Dict[str, str]) -> Dict[str, float]:
        node = self.nodes[var]
        probs = {}

        for state in node.states:
            test_assignment = assignment.copy()
            test_assignment[var] = state

            prob = 1.0

            parent_assignments = {p: test_assignment[p] for p in self.parents[var]}
            cpt = self.cpts[var]
            prob *= cpt.get_probability(parent_assignments, state)

            for child in self.children[var]:
                child_cpt = self.cpts[child]
                child_parent_assignments = {p: test_assignment[p] for p in self.parents[child]}
                child_state = test_assignment[child]
                prob *= child_cpt.get_probability(child_parent_assignments, child_state)

            probs[state] = prob

        total = sum(probs.values())
        if total > 0:
            probs = {k: v / total for k, v in probs.items()}
        else:
            probs = {k: 1.0 / len(probs) for k in probs}

        return probs

    def fit(self, data: List[Dict[str, str]], smoothing: float = 1.0,
            use_em: bool = None, max_em_iter: int = 100,
            em_tolerance: float = 1e-6, verbose: bool = False):
        has_missing = any(
            any(node_name not in sample for node_name in self.nodes)
            for sample in data
        )

        if use_em is None:
            use_em = has_missing

        if use_em:
            self._fit_em(data, smoothing, max_em_iter, em_tolerance, verbose)
        else:
            self._fit_complete(data, smoothing)

    def _fit_complete(self, data: List[Dict[str, str]], smoothing: float = 1.0):
        for node_name in self.nodes:
            self._learn_node_cpt_complete(node_name, data, smoothing)

    def _learn_node_cpt_complete(self, node_name: str, data: List[Dict[str, str]], smoothing: float):
        node = self.nodes[node_name]
        parents = self.parents[node_name]
        cpt = self.cpts[node_name]

        parent_dims = [self.nodes[p].n_states for p in parents]
        counts = np.ones(tuple(parent_dims) + (node.n_states,)) * smoothing

        for sample in data:
            if node_name not in sample:
                continue

            parent_indices = []
            valid = True
            for p in parents:
                if p not in sample:
                    valid = False
                    break
                parent_indices.append(self.nodes[p].state_to_idx[sample[p]])

            if not valid:
                continue

            node_idx = node.state_to_idx[sample[node_name]]
            counts[tuple(parent_indices) + (node_idx,)] += 1

        for idx in product(*[range(d) for d in parent_dims]):
            row = counts[idx]
            row_sum = row.sum()
            if row_sum > 0:
                cpt.table[idx] = row / row_sum

    def _fit_em(self, data: List[Dict[str, str]], smoothing: float = 1.0,
                max_em_iter: int = 100, em_tolerance: float = 1e-6, verbose: bool = False):
        n_samples = len(data)
        for node_name in self.nodes:
            cpt = self.cpts[node_name]
            cpt.normalize()
            if np.all(cpt.table == 0):
                parent_dims = [self.nodes[p].n_states for p in self.parents[node_name]]
                cpt.table = np.ones(tuple(parent_dims) + (self.nodes[node_name].n_states,))
                cpt.normalize()

        prev_log_likelihood = float('-inf')

        for em_iter in range(max_em_iter):
            expected_counts = {}
            for node_name in self.nodes:
                node = self.nodes[node_name]
                parents = self.parents[node_name]
                parent_dims = [self.nodes[p].n_states for p in parents]
                expected_counts[node_name] = np.ones(tuple(parent_dims) + (node.n_states,)) * smoothing

            log_likelihood = 0.0

            for sample in data:
                evidence = {k: v for k, v in sample.items() if v is not None}
                missing_vars = [v for v in self.nodes if v not in evidence]

                if not missing_vars:
                    log_likelihood += np.log(self._get_joint_probability(sample))
                    for node_name in self.nodes:
                        node = self.nodes[node_name]
                        parents = self.parents[node_name]
                        parent_indices = [self.nodes[p].state_to_idx[sample[p]] for p in parents]
                        node_idx = node.state_to_idx[sample[node_name]]
                        expected_counts[node_name][tuple(parent_indices) + (node_idx,)] += 1
                else:
                    posteriors = self._infer_missing_distribution(evidence, missing_vars)
                    
                    for assignment, prob in posteriors.items():
                        full_sample = evidence.copy()
                        for i, var in enumerate(missing_vars):
                            full_sample[var] = assignment[i]
                        
                        log_likelihood += prob * np.log(max(self._get_joint_probability(full_sample), 1e-10))

                        for node_name in self.nodes:
                            node = self.nodes[node_name]
                            parents = self.parents[node_name]
                            parent_indices = [self.nodes[p].state_to_idx[full_sample[p]] for p in parents]
                            node_idx = node.state_to_idx[full_sample[node_name]]
                            expected_counts[node_name][tuple(parent_indices) + (node_idx,)] += prob

            for node_name in self.nodes:
                node = self.nodes[node_name]
                parents = self.parents[node_name]
                cpt = self.cpts[node_name]
                counts = expected_counts[node_name]

                parent_dims = [self.nodes[p].n_states for p in parents]
                for idx in product(*[range(d) for d in parent_dims]):
                    row = counts[idx]
                    row_sum = row.sum()
                    if row_sum > 0:
                        cpt.table[idx] = row / row_sum

            ll_change = log_likelihood - prev_log_likelihood
            if verbose:
                print(f"EM迭代 {em_iter + 1}, 对数似然: {log_likelihood:.4f}, 变化: {ll_change:.6f}")

            if em_iter > 0 and abs(ll_change) < em_tolerance:
                if verbose:
                    print(f"EM算法在第 {em_iter + 1} 次迭代收敛")
                break

            prev_log_likelihood = log_likelihood

    def _get_joint_probability(self, assignment: Dict[str, str]) -> float:
        prob = 1.0
        for node_name in self.topological_order():
            node = self.nodes[node_name]
            cpt = self.cpts[node_name]
            parent_assignments = {p: assignment[p] for p in self.parents[node_name]}
            prob *= cpt.get_probability(parent_assignments, assignment[node_name])
        return max(prob, 1e-10)

    def _infer_missing_distribution(self, evidence: Dict[str, str],
                                     missing_vars: List[str]) -> Dict[Tuple[str, ...], float]:
        if not missing_vars:
            return {(): 1.0}

        result = self.variable_elimination(missing_vars, evidence)

        distributions = []
        for var in missing_vars:
            states = self.nodes[var].states
            probs = [result[var][s] for s in states]
            distributions.append(list(zip(states, probs)))

        joint_dist = {}
        for combo in product(*[range(len(d[0])) for d in distributions]):
            assignment = tuple(distributions[i][combo[i]][0] for i in range(len(missing_vars)))
            prob = 1.0
            for i in range(len(missing_vars)):
                prob *= distributions[i][combo[i]][1]
            joint_dist[assignment] = prob

        total = sum(joint_dist.values())
        if total > 0:
            joint_dist = {k: v / total for k, v in joint_dist.items()}

        return joint_dist

    def visualize(self, figsize: Tuple[int, int] = (10, 8),
                  node_size: int = 2000, font_size: int = 12):
        plt.figure(figsize=figsize)

        pos = nx.spring_layout(self.graph, k=2, iterations=50)

        nx.draw_networkx_nodes(self.graph, pos, node_size=node_size,
                               node_color='lightblue', alpha=0.9,
                               edgecolors='black', linewidths=2)
        nx.draw_networkx_edges(self.graph, pos, edge_color='gray',
                               arrows=True, arrowsize=20, width=2)

        node_labels = {}
        for node_name in self.nodes:
            node = self.nodes[node_name]
            label = f"{node_name}\n({', '.join(node.states)})"
            node_labels[node_name] = label

        nx.draw_networkx_labels(self.graph, pos, node_labels,
                                font_size=font_size, font_weight='bold')

        plt.title(f"Bayesian Network: {self.name}", fontsize=16, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        return plt.gcf()

    def __repr__(self):
        return (f"BayesianNetwork({self.name}, "
                f"nodes={list(self.nodes.keys())}, "
                f"edges={self.edges})")

    def compute_bic_score(self, data: List[Dict[str, str]]) -> float:
        n_samples = len(data)
        bic = 0.0

        for node_name in self.nodes:
            node = self.nodes[node_name]
            parents = self.parents[node_name]
            cpt = self.cpts[node_name]

            parent_dims = [self.nodes[p].n_states for p in parents]
            parent_combinations = np.prod(parent_dims) if parent_dims else 1

            ll_contribution = 0.0
            for sample in data:
                if node_name not in sample:
                    continue

                parent_indices = []
                valid = True
                for p in parents:
                    if p not in sample:
                        valid = False
                        break
                    parent_indices.append(self.nodes[p].state_to_idx[sample[p]])

                if not valid:
                    continue

                node_idx = node.state_to_idx[sample[node_name]]
                prob = cpt.table[tuple(parent_indices) + (node_idx,)]
                ll_contribution += np.log(max(prob, 1e-10))

            n_params = parent_combinations * (node.n_states - 1)
            bic += ll_contribution - 0.5 * n_params * np.log(n_samples)

        return bic

    def compute_bdeu_score(self, data: List[Dict[str, str]], ess: float = 1.0) -> float:
        score = 0.0

        for node_name in self.nodes:
            node = self.nodes[node_name]
            parents = self.parents[node_name]

            parent_dims = [self.nodes[p].n_states for p in parents]
            parent_combinations = int(np.prod(parent_dims)) if parent_dims else 1

            counts = np.zeros(tuple(parent_dims) + (node.n_states,))

            for sample in data:
                if node_name not in sample:
                    continue

                parent_indices = []
                valid = True
                for p in parents:
                    if p not in sample:
                        valid = False
                        break
                    parent_indices.append(self.nodes[p].state_to_idx[sample[p]])

                if not valid:
                    continue

                node_idx = node.state_to_idx[sample[node_name]]
                counts[tuple(parent_indices) + (node_idx,)] += 1

            alpha_ij = ess / (parent_combinations * node.n_states)
            alpha_i = ess / parent_combinations

            for parent_idx in range(parent_combinations):
                parent_tuple = np.unravel_index(parent_idx, parent_dims) if parent_dims else ()
                N_ij = counts[parent_tuple]
                N_i = N_ij.sum()

                from scipy.special import gammaln

                term1 = gammaln(alpha_i) - gammaln(alpha_i + N_i)
                term2 = np.sum(gammaln(alpha_ij + N_ij) - gammaln(alpha_ij))
                score += term1 + term2

        return score

    def learn_structure_k2(self, data: List[Dict[str, str]],
                            node_order: List[str] = None,
                            max_parents: int = 3,
                            score: str = 'bic',
                            ess: float = 1.0) -> None:
        if node_order is None:
            node_order = list(self.nodes.keys())

        for node_name in node_order:
            self.parents[node_name] = []
            self._rebuild_cpt(node_name)

        for i, child in enumerate(node_order):
            best_score = float('-inf')
            best_parents = []

            candidate_parents = node_order[:i]

            while len(best_parents) < max_parents and len(candidate_parents) > 0:
                improved = False

                for p in candidate_parents:
                    if p in best_parents:
                        continue

                    test_parents = best_parents + [p]

                    temp_parents = self.parents[child].copy()
                    self.parents[child] = test_parents
                    self._rebuild_cpt(child)

                    self._learn_node_cpt_complete(child, data, 0.0)

                    if score == 'bic':
                        current_score = self.compute_bic_score(data)
                    else:
                        current_score = self.compute_bdeu_score(data, ess)

                    if current_score > best_score:
                        best_score = current_score
                        best_parents = test_parents
                        improved = True

                    self.parents[child] = temp_parents
                    self._rebuild_cpt(child)

                if not improved:
                    break

            self.parents[child] = best_parents
            self._rebuild_cpt(child)

        self.edges = []
        for child, parents in self.parents.items():
            for p in parents:
                self.edges.append((p, child))

        self.graph = nx.DiGraph()
        self.graph.add_nodes_from(self.nodes.keys())
        self.graph.add_edges_from(self.edges)

        for child in self.parents:
            self._learn_node_cpt_complete(child, data, 1.0)

    def learn_structure_hill_climb(self, data: List[Dict[str, str]],
                                    max_iter: int = 100,
                                    score: str = 'bic',
                                    ess: float = 1.0,
                                    verbose: bool = False) -> None:
        for node_name in self.nodes:
            self.parents[node_name] = []
            self._rebuild_cpt(node_name)

        self.edges = []
        self.graph = nx.DiGraph()
        self.graph.add_nodes_from(self.nodes.keys())

        for node_name in self.nodes:
            self._learn_node_cpt_complete(node_name, data, 1.0)

        if score == 'bic':
            best_score = self.compute_bic_score(data)
        else:
            best_score = self.compute_bdeu_score(data, ess)

        for iteration in range(max_iter):
            best_new_score = best_score
            best_operation = None

            node_list = list(self.nodes.keys())

            for i, node_x in enumerate(node_list):
                for j, node_y in enumerate(node_list):
                    if i == j:
                        continue

                    if (node_x, node_y) in self.edges:
                        temp_parents = self.parents[node_y].copy()
                        self.parents[node_y].remove(node_x)
                        self.edges.remove((node_x, node_y))
                        self.graph.remove_edge(node_x, node_y)
                        self._rebuild_cpt(node_y)

                        for n in self.nodes:
                            self._learn_node_cpt_complete(n, data, 1.0)

                        if score == 'bic':
                            current_score = self.compute_bic_score(data)
                        else:
                            current_score = self.compute_bdeu_score(data, ess)

                        if current_score > best_new_score:
                            best_new_score = current_score
                            best_operation = ('remove', node_x, node_y)

                        self.parents[node_y] = temp_parents
                        self.edges.append((node_x, node_y))
                        self.graph.add_edge(node_x, node_y)
                        self._rebuild_cpt(node_y)

                    else:
                        if (node_y, node_x) in self.edges:
                            temp_parents_x = self.parents[node_x].copy()
                            temp_parents_y = self.parents[node_y].copy()
                            self.parents[node_x].remove(node_y)
                            self.parents[node_y].append(node_x)
                            self.edges.remove((node_y, node_x))
                            self.edges.append((node_x, node_y))
                            self.graph.remove_edge(node_y, node_x)
                            self.graph.add_edge(node_x, node_y)
                            self._rebuild_cpt(node_x)
                            self._rebuild_cpt(node_y)

                            if not self._has_cycle():
                                for n in self.nodes:
                                    self._learn_node_cpt_complete(n, data, 1.0)

                                if score == 'bic':
                                    current_score = self.compute_bic_score(data)
                                else:
                                    current_score = self.compute_bdeu_score(data, ess)

                                if current_score > best_new_score:
                                    best_new_score = current_score
                                    best_operation = ('reverse', node_y, node_x)

                            self.parents[node_x] = temp_parents_x
                            self.parents[node_y] = temp_parents_y
                            self.edges.remove((node_x, node_y))
                            self.edges.append((node_y, node_x))
                            self.graph.remove_edge(node_x, node_y)
                            self.graph.add_edge(node_y, node_x)
                            self._rebuild_cpt(node_x)
                            self._rebuild_cpt(node_y)

                        else:
                            self.parents[node_y].append(node_x)
                            self.edges.append((node_x, node_y))
                            self.graph.add_edge(node_x, node_y)
                            self._rebuild_cpt(node_y)

                            if not self._has_cycle():
                                for n in self.nodes:
                                    self._learn_node_cpt_complete(n, data, 1.0)

                                if score == 'bic':
                                    current_score = self.compute_bic_score(data)
                                else:
                                    current_score = self.compute_bdeu_score(data, ess)

                                if current_score > best_new_score:
                                    best_new_score = current_score
                                    best_operation = ('add', node_x, node_y)

                            self.parents[node_y].remove(node_x)
                            self.edges.remove((node_x, node_y))
                            self.graph.remove_edge(node_x, node_y)
                            self._rebuild_cpt(node_y)

            if best_operation is None or best_new_score <= best_score:
                if verbose:
                    print(f"爬山法在第 {iteration + 1} 次迭代收敛")
                break

            op, x, y = best_operation
            if verbose:
                print(f"迭代 {iteration + 1}: {op} 边 {x}->{y}, 分数: {best_new_score:.4f}")

            if op == 'add':
                self.parents[y].append(x)
                self.edges.append((x, y))
                self.graph.add_edge(x, y)
                self._rebuild_cpt(y)
            elif op == 'remove':
                self.parents[y].remove(x)
                self.edges.remove((x, y))
                self.graph.remove_edge(x, y)
                self._rebuild_cpt(y)
            elif op == 'reverse':
                self.parents[x].remove(y)
                self.parents[y].append(x)
                self.edges.remove((y, x))
                self.edges.append((x, y))
                self.graph.remove_edge(y, x)
                self.graph.add_edge(x, y)
                self._rebuild_cpt(x)
                self._rebuild_cpt(y)

            best_score = best_new_score

            for n in self.nodes:
                self._learn_node_cpt_complete(n, data, 1.0)

    def do_intervention(self, intervention: Dict[str, str]) -> 'BayesianNetwork':
        intervened = BayesianNetwork(f"{self.name}_intervened")

        for node_name, node in self.nodes.items():
            intervened.add_node(node_name, node.states)

        for parent, child in self.edges:
            if child not in intervention:
                intervened.add_edge(parent, child)

        for node_name in intervened.nodes:
            if node_name in intervention:
                state_idx = intervened.nodes[node_name].state_to_idx[intervention[node_name]]
                cpt = intervened.cpts[node_name]
                cpt.table[:] = 0.0
                cpt.table[..., state_idx] = 1.0
            else:
                old_cpt = self.cpts[node_name]
                new_cpt = intervened.cpts[node_name]
                new_cpt.table = old_cpt.table.copy()

        return intervened

    def causal_effect(self, treatment: str,
                      treatment_value: str,
                      outcome: str,
                      outcome_value: str = None,
                      evidence: Dict[str, str] = None) -> float:
        evidence = evidence or {}

        intervened = self.do_intervention({treatment: treatment_value})
        result = intervened.variable_elimination([outcome], evidence)

        if outcome_value is not None:
            return result[outcome][outcome_value]
        else:
            return result[outcome]

    def average_causal_effect(self, treatment: str,
                              treatment_value1: str,
                              treatment_value2: str,
                              outcome: str,
                              outcome_value: str,
                              evidence: Dict[str, str] = None) -> float:
        eff1 = self.causal_effect(treatment, treatment_value1, outcome, outcome_value, evidence)
        eff2 = self.causal_effect(treatment, treatment_value2, outcome, outcome_value, evidence)
        return eff1 - eff2

    def sensitivity_analysis(self, query: List[str],
                             evidence: Dict[str, str] = None,
                             target_node: str = None,
                             perturbation: float = 0.1,
                             method: str = 'one_at_a_time') -> Dict:
        evidence = evidence or {}
        original_result = self.variable_elimination(query, evidence)

        if target_node is not None:
            nodes_to_test = [target_node]
        else:
            nodes_to_test = list(self.nodes.keys())

        sensitivity_results = {}

        if method == 'one_at_a_time':
            for node_name in nodes_to_test:
                node_sensitivity = {}
                original_cpt = self.cpts[node_name].table.copy()

                for q_var in query:
                    original_prob = original_result[q_var]
                    max_change = 0.0

                    parent_dims = [self.nodes[p].n_states for p in self.parents[node_name]]
                    for parent_idx in product(*[range(d) for d in parent_dims]):
                        for state_idx in range(self.nodes[node_name].n_states):
                            perturbed_cpt = original_cpt.copy()
                            idx = parent_idx + (state_idx,)
                            perturbed_cpt[idx] = np.clip(
                                perturbed_cpt[idx] + perturbation,
                                0.01, 0.99
                            )
                            row_sum = perturbed_cpt[parent_idx].sum()
                            perturbed_cpt[parent_idx] /= row_sum

                            self.cpts[node_name].table = perturbed_cpt
                            new_result = self.variable_elimination(query, evidence)

                            for state, prob in new_result[q_var].items():
                                change = abs(prob - original_prob[state])
                                max_change = max(max_change, change)

                            self.cpts[node_name].table = original_cpt.copy()

                    node_sensitivity[q_var] = max_change

                sensitivity_results[node_name] = node_sensitivity
                self.cpts[node_name].table = original_cpt

        elif method == 'derivative':
            for node_name in nodes_to_test:
                node_sensitivity = {}
                original_cpt = self.cpts[node_name].table.copy()

                for q_var in query:
                    original_prob = original_result[q_var]
                    derivative_estimates = []

                    parent_dims = [self.nodes[p].n_states for p in self.parents[node_name]]
                    for parent_idx in product(*[range(d) for d in parent_dims]):
                        for state_idx in range(self.nodes[node_name].n_states):
                            eps = 1e-4
                            perturbed_cpt = original_cpt.copy()
                            idx = parent_idx + (state_idx,)

                            original_val = perturbed_cpt[idx]
                            perturbed_cpt[idx] = np.clip(original_val + eps, 0.01, 0.99)
                            row_sum = perturbed_cpt[parent_idx].sum()
                            perturbed_cpt[parent_idx] /= row_sum

                            self.cpts[node_name].table = perturbed_cpt
                            new_result = self.variable_elimination(query, evidence)

                            for state in original_prob:
                                dP = (new_result[q_var][state] - original_prob[state]) / eps
                                derivative_estimates.append(abs(dP))

                            self.cpts[node_name].table = original_cpt.copy()

                    node_sensitivity[q_var] = np.mean(derivative_estimates) if derivative_estimates else 0.0

                sensitivity_results[node_name] = node_sensitivity
                self.cpts[node_name].table = original_cpt

        return {
            'original_result': original_result,
            'sensitivity': sensitivity_results,
            'perturbation': perturbation,
            'method': method
        }
