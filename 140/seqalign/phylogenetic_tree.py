import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict


class PhylogeneticTree:
    def __init__(self):
        self.tree = None
        self.root = None
        self.labels = None
        self.distances = None

    def neighbor_joining(self, distance_matrix, labels=None):
        n = distance_matrix.shape[0]
        if labels is None:
            labels = [f'seq_{i}' for i in range(n)]
        
        self.labels = labels.copy()
        D = distance_matrix.copy()
        
        nodes = list(range(n))
        node_labels = {i: labels[i] for i in range(n)}
        tree = {i: [] for i in range(n)}
        new_node_id = n
        
        while len(nodes) > 2:
            Q = np.zeros((len(nodes), len(nodes)))
            for i in range(len(nodes)):
                for j in range(len(nodes)):
                    if i != j:
                        sum_i = sum(D[i, k] for k in range(len(nodes)) if k != i)
                        sum_j = sum(D[j, k] for k in range(len(nodes)) if k != j)
                        Q[i, j] = (len(nodes) - 2) * D[i, j] - sum_i - sum_j
            
            min_val = float('inf')
            min_i, min_j = 0, 1
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    if Q[i, j] < min_val:
                        min_val = Q[i, j]
                        min_i, min_j = i, j
            
            sum_i = sum(D[min_i, k] for k in range(len(nodes)) if k != min_i)
            sum_j = sum(D[min_j, k] for k in range(len(nodes)) if k != min_j)
            
            dist_i_new = 0.5 * D[min_i, min_j] + (sum_i - sum_j) / (2 * (len(nodes) - 2))
            dist_j_new = D[min_i, min_j] - dist_i_new
            
            tree[new_node_id] = [
                (nodes[min_i], max(0, dist_i_new)),
                (nodes[min_j], max(0, dist_j_new))
            ]
            
            new_D = np.zeros((len(nodes) - 1, len(nodes) - 1))
            new_nodes = [nodes[k] for k in range(len(nodes)) if k != min_i and k != min_j]
            new_nodes.append(new_node_id)
            
            for i in range(len(new_nodes) - 1):
                for j in range(i + 1, len(new_nodes) - 1):
                    old_i = nodes.index(new_nodes[i])
                    old_j = nodes.index(new_nodes[j])
                    new_D[i, j] = D[old_i, old_j]
                    new_D[j, i] = new_D[i, j]
            
            for i in range(len(new_nodes) - 1):
                old_i = nodes.index(new_nodes[i])
                dist = 0.5 * (D[old_i, min_i] + D[old_i, min_j] - D[min_i, min_j])
                new_D[i, -1] = dist
                new_D[-1, i] = dist
            
            D = new_D
            nodes = new_nodes
            new_node_id += 1
        
        if len(nodes) == 2:
            tree[new_node_id] = [
                (nodes[0], D[0, 1] / 2),
                (nodes[1], D[0, 1] / 2)
            ]
            root = new_node_id
        else:
            root = nodes[0]
        
        self.tree = tree
        self.root = root
        return tree, root

    def get_newick_format(self, node=None, parent_dist=0):
        if node is None:
            node = self.root
        
        if node not in self.tree or len(self.tree[node]) == 0:
            label = self.labels[node] if node < len(self.labels) else f'node_{node}'
            return f'{label}:{parent_dist:.4f}'
        
        children = []
        for child, dist in self.tree[node]:
            children.append(self.get_newick_format(child, dist))
        
        return '(' + ','.join(children) + f'):{parent_dist:.4f}'

    def calculate_node_positions(self):
        if self.tree is None:
            return {}
        
        depths = {}
        def calculate_depth(node, depth):
            depths[node] = depth
            for child, dist in self.tree.get(node, []):
                calculate_depth(child, depth + dist)
        
        calculate_depth(self.root, 0)
        
        leaves = [n for n in range(len(self.labels))]
        y_positions = {leaf: i for i, leaf in enumerate(leaves)}
        
        for node in sorted(self.tree.keys(), reverse=True):
            children = self.tree.get(node, [])
            if children:
                child_ys = [y_positions.get(child, 0) for child, _ in children]
                y_positions[node] = sum(child_ys) / len(child_ys)
        
        positions = {}
        for node in depths:
            positions[node] = (depths[node], y_positions.get(node, 0))
        
        return positions

    def draw_tree(self, ax=None, figsize=(10, 8), show_labels=True, 
                  show_distances=False, title='Phylogenetic Tree (Neighbor-Joining)'):
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        
        positions = self.calculate_node_positions()
        
        def draw_node(node):
            x, y = positions[node]
            
            for child, dist in self.tree.get(node, []):
                cx, cy = positions[child]
                ax.plot([x, cx], [y, y], 'k-', linewidth=1.5)
                ax.plot([cx, cx], [y, cy], 'k-', linewidth=1.5)
                
                if show_distances and dist > 0:
                    ax.text((x + cx) / 2, y + 0.1, f'{dist:.2f}', 
                           fontsize=8, ha='center', va='bottom')
                
                draw_node(child)
            
            if show_labels and node < len(self.labels):
                ax.text(x + 0.02, y, self.labels[node], 
                       fontsize=10, ha='left', va='center',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='lightblue', alpha=0.6))
            
            ax.plot(x, y, 'o', color='darkblue', markersize=4)
        
        draw_node(self.root)
        
        ax.set_title(title, fontsize=14, pad=20)
        ax.set_xlabel('Evolutionary Distance', fontsize=12)
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        return ax

    def plot(self, **kwargs):
        fig, ax = plt.subplots(figsize=kwargs.get('figsize', (10, 8)))
        self.draw_tree(ax=ax, **kwargs)
        plt.tight_layout()
        plt.show()
        return fig


class DistanceCalculator:
    def __init__(self):
        pass
    
    def p_distance(self, seq1, seq2):
        differences = sum(1 for a, b in zip(seq1, seq2) if a != '-' and b != '-' and a != b)
        valid_positions = sum(1 for a, b in zip(seq1, seq2) if a != '-' and b != '-')
        return differences / valid_positions if valid_positions > 0 else 1.0
    
    def jukes_cantor_distance(self, seq1, seq2):
        p = self.p_distance(seq1, seq2)
        p = min(p, 0.749)
        return -0.75 * np.log(1 - 4 * p / 3)
    
    def kimura_2_parameter(self, seq1, seq2):
        transitions = sum(1 for a, b in zip(seq1, seq2) 
                         if {a, b} in [{'A', 'G'}, {'C', 'T'}])
        transversions = sum(1 for a, b in zip(seq1, seq2) 
                           if a != '-' and b != '-' and a != b 
                           and {a, b} not in [{'A', 'G'}, {'C', 'T'}])
        valid_positions = sum(1 for a, b in zip(seq1, seq2) if a != '-' and b != '-')
        
        p = transitions / valid_positions if valid_positions > 0 else 0
        q = transversions / valid_positions if valid_positions > 0 else 0
        
        p = min(p, 0.37)
        q = min(q, 0.37)
        
        if 1 - 2 * p - q <= 0:
            return float('inf')
        if 1 - 2 * q <= 0:
            return float('inf')
        
        return -0.5 * np.log(1 - 2 * p - q) - 0.25 * np.log(1 - 2 * q)
    
    def build_distance_matrix(self, sequences, method='p_distance'):
        n = len(sequences)
        matrix = np.zeros((n, n))
        
        method_func = getattr(self, method, self.p_distance)
        
        for i in range(n):
            for j in range(i + 1, n):
                dist = method_func(sequences[i], sequences[j])
                matrix[i, j] = dist
                matrix[j, i] = dist
        
        return matrix


class PhylogeneticAnalysis:
    def __init__(self):
        self.distance_calculator = DistanceCalculator()
        self.tree_builder = PhylogeneticTree()
        self.distance_matrix = None
        self.labels = None
    
    def build_tree(self, sequences, labels=None, distance_method='p_distance'):
        self.distance_matrix = self.distance_calculator.build_distance_matrix(
            sequences, distance_method
        )
        self.labels = labels
        
        self.tree_builder.neighbor_joining(self.distance_matrix, labels)
        return self.tree_builder
    
    def get_newick(self):
        return self.tree_builder.get_newick_format() + ';'
    
    def plot_tree(self, **kwargs):
        return self.tree_builder.plot(**kwargs)
