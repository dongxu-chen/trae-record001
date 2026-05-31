import pandas as pd
import numpy as np
from scipy import stats


class CausalGraphAnalyzer:
    def __init__(self, df, treatment_col, outcome_col, covariates=None):
        self.df = df.copy()
        self.treatment_col = treatment_col
        self.outcome_col = outcome_col
        self.covariates = covariates or []
        self.nodes = []
        self.edges = []
        self.adjacency_matrix = None

    def partial_correlation(self, x, y, z=None):
        if z is None or len(z) == 0:
            return stats.pearsonr(x, y)[0]
        
        x_resid = self.residualize(x, z)
        y_resid = self.residualize(y, z)
        
        return stats.pearsonr(x_resid, y_resid)[0]

    def residualize(self, y, X):
        X = np.column_stack([np.ones(len(y)), X])
        beta = np.linalg.inv(X.T @ X) @ X.T @ y
        return y - X @ beta

    def pc_algorithm_skeleton(self, significance_level=0.05):
        nodes = [self.treatment_col, self.outcome_col] + self.covariates
        n_nodes = len(nodes)
        n = len(self.df)
        
        adj_matrix = np.ones((n_nodes, n_nodes), dtype=bool)
        np.fill_diagonal(adj_matrix, False)
        
        sep_sets = {}
        
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                x = self.df[nodes[i]].values
                y = self.df[nodes[j]].values
                
                corr = stats.pearsonr(x, y)[0]
                z_stat = np.sqrt(n - 3) * 0.5 * np.log((1 + corr) / (1 - corr))
                p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
                
                if p_value > significance_level:
                    adj_matrix[i, j] = adj_matrix[j, i] = False
                    sep_sets[(i, j)] = []
                    sep_sets[(j, i)] = []
        
        for depth in range(1, min(n_nodes - 2, 3)):
            for i in range(n_nodes):
                for j in range(i + 1, n_nodes):
                    if not adj_matrix[i, j]:
                        continue
                    
                    neighbors_i = [k for k in range(n_nodes) if adj_matrix[i, k] and k != j]
                    
                    if len(neighbors_i) < depth:
                        continue
                    
                    from itertools import combinations
                    for z_set in combinations(neighbors_i, depth):
                        x = self.df[nodes[i]].values
                        y = self.df[nodes[j]].values
                        z = [self.df[nodes[k]].values for k in z_set]
                        
                        try:
                            partial_corr = self.partial_correlation(x, y, np.column_stack(z) if z else None)
                            z_stat = np.sqrt(n - depth - 3) * 0.5 * np.log((1 + partial_corr) / (1 - partial_corr + 1e-10))
                            p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
                            
                            if p_value > significance_level:
                                adj_matrix[i, j] = adj_matrix[j, i] = False
                                sep_sets[(i, j)] = list(z_set)
                                sep_sets[(j, i)] = list(z_set)
                                break
                        except:
                            continue
        
        self.nodes = nodes
        self.adjacency_matrix = adj_matrix
        return adj_matrix, sep_sets

    def generate_edges(self, adj_matrix, sep_sets):
        edges = []
        n_nodes = len(self.nodes)
        
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                if adj_matrix[i, j]:
                    node_i = self.nodes[i]
                    node_j = self.nodes[j]
                    
                    has_causal_path = False
                    strength = abs(stats.pearsonr(
                        self.df[node_i].values,
                        self.df[node_j].values
                    )[0])
                    
                    if node_i == self.treatment_col and node_j == self.outcome_col:
                        edge_type = 'causal'
                        direction = 'forward'
                        has_causal_path = True
                    elif node_i == self.treatment_col:
                        edge_type = 'confounder' if node_j in self.covariates else 'treatment->outcome'
                        direction = 'forward'
                    elif node_j == self.outcome_col:
                        edge_type = 'confounder' if node_i in self.covariates else 'treatment->outcome'
                        direction = 'forward'
                    elif node_i in self.covariates and node_j in self.covariates:
                        edge_type = 'correlated'
                        direction = 'undirected'
                    else:
                        edge_type = 'correlated'
                        direction = 'undirected'
                    
                    edges.append({
                        'source': node_i,
                        'target': node_j,
                        'type': edge_type,
                        'direction': direction,
                        'strength': float(strength),
                        'has_causal_path': has_causal_path
                    })
        
        return edges

    def calculate_node_positions(self):
        nodes = [self.treatment_col, self.outcome_col] + self.covariates
        positions = {}
        
        positions[self.treatment_col] = {'x': 0.2, 'y': 0.5}
        positions[self.outcome_col] = {'x': 0.8, 'y': 0.5}
        
        n_covariates = len(self.covariates)
        if n_covariates > 0:
            for i, cov in enumerate(self.covariates):
                if i < n_covariates / 2:
                    positions[cov] = {
                        'x': 0.35 + (i / max(n_covariates, 1)) * 0.3,
                        'y': 0.2
                    }
                else:
                    positions[cov] = {
                        'x': 0.35 + ((i - n_covariates/2) / max(n_covariates, 1)) * 0.3,
                        'y': 0.8
                    }
        
        return positions

    def learn_causal_graph(self, significance_level=0.05):
        adj_matrix, sep_sets = self.pc_algorithm_skeleton(significance_level)
        edges = self.generate_edges(adj_matrix, sep_sets)
        positions = self.calculate_node_positions()
        
        node_colors = {}
        for node in self.nodes:
            if node == self.treatment_col:
                node_colors[node] = '#d4a855'
            elif node == self.outcome_col:
                node_colors[node] = '#1e3a5f'
            else:
                node_colors[node] = '#64748b'
        
        node_types = {}
        for node in self.nodes:
            if node == self.treatment_col:
                node_types[node] = 'treatment'
            elif node == self.outcome_col:
                node_types[node] = 'outcome'
            else:
                node_types[node] = 'covariate'
        
        nodes_data = [
            {
                'id': node,
                'label': node,
                'type': node_types[node],
                'color': node_colors[node],
                'position': positions[node],
                'size': 40 if node in [self.treatment_col, self.outcome_col] else 30
            }
            for node in self.nodes
        ]
        
        return {
            'nodes': nodes_data,
            'edges': edges,
            'adjacency_matrix': adj_matrix.tolist(),
            'significance_level': significance_level
        }

    def identify_backdoor_paths(self):
        if self.adjacency_matrix is None:
            self.pc_algorithm_skeleton()
        
        treatment_idx = self.nodes.index(self.treatment_col)
        outcome_idx = self.nodes.index(self.outcome_col)
        
        def find_paths(start, end, visited=None, path=None):
            if visited is None:
                visited = set()
            if path is None:
                path = []
            
            visited.add(start)
            path = path + [start]
            
            if start == end:
                return [path]
            
            paths = []
            for neighbor in range(len(self.nodes)):
                if self.adjacency_matrix[start][neighbor] and neighbor not in visited:
                    new_paths = find_paths(neighbor, end, visited.copy(), path.copy())
                    for p in new_paths:
                        paths.append(p)
            
            return paths
        
        all_paths = find_paths(treatment_idx, outcome_idx)
        
        backdoor_paths = []
        for path in all_paths:
            if len(path) > 2:
                backdoor_paths.append([self.nodes[i] for i in path])
        
        adjustment_sets = []
        for path in backdoor_paths:
            for node in path[1:-1]:
                if node not in adjustment_sets and node in self.covariates:
                    adjustment_sets.append(node)
        
        return {
            'backdoor_paths': backdoor_paths,
            'suggested_adjustment': list(set(adjustment_sets)),
            'total_paths': len(all_paths),
            'backdoor_path_count': len(backdoor_paths)
        }
