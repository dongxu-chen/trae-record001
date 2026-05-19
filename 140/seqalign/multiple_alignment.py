import numpy as np
from collections import defaultdict
from .needleman_wunsch import NeedlemanWunsch


class ClustalW:
    def __init__(self, match=1, mismatch=-1, gap_open=-2, gap_extend=-1):
        self.match = match
        self.mismatch = mismatch
        self.gap_open = gap_open
        self.gap_extend = gap_extend
        self.sequences = []
        self.sequence_names = []
        self.aligned_sequences = []
        self.distance_matrix = None
        self.guide_tree = None

    def _calculate_pairwise_distance(self, seq1, seq2):
        aligner = NeedlemanWunsch(
            match=self.match,
            mismatch=self.mismatch,
            gap_open=self.gap_open,
            gap_extend=self.gap_extend,
            use_affine=True
        )
        aligned1, aligned2, score = aligner.align(seq1, seq2)
        
        matches = sum(1 for a, b in zip(aligned1, aligned2) if a == b and a != '-')
        aligned_length = len([a for a in aligned1 if a != '-']) + len([b for b in aligned2 if b != '-'])
        identity = matches / max(len(seq1), len(seq2))
        
        distance = 1 - identity
        return distance

    def _build_distance_matrix(self):
        n = len(self.sequences)
        self.distance_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                dist = self._calculate_pairwise_distance(self.sequences[i], self.sequences[j])
                self.distance_matrix[i, j] = dist
                self.distance_matrix[j, i] = dist
        
        return self.distance_matrix

    def _neighbor_joining_tree(self, distance_matrix):
        n = distance_matrix.shape[0]
        nodes = list(range(n))
        tree = {i: [] for i in range(n)}
        new_node_id = n
        
        while len(nodes) > 2:
            Q = np.zeros((len(nodes), len(nodes)))
            for i in range(len(nodes)):
                for j in range(len(nodes)):
                    if i != j:
                        sum_i = sum(distance_matrix[i, k] for k in range(len(nodes)) if k != i)
                        sum_j = sum(distance_matrix[j, k] for k in range(len(nodes)) if k != j)
                        Q[i, j] = (len(nodes) - 2) * distance_matrix[i, j] - sum_i - sum_j
            
            min_val = float('inf')
            min_i, min_j = 0, 1
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    if Q[i, j] < min_val:
                        min_val = Q[i, j]
                        min_i, min_j = i, j
            
            sum_i = sum(distance_matrix[min_i, k] for k in range(len(nodes)) if k != min_i)
            sum_j = sum(distance_matrix[min_j, k] for k in range(len(nodes)) if k != min_j)
            
            dist_i_new = 0.5 * distance_matrix[min_i, min_j] + (sum_i - sum_j) / (2 * (len(nodes) - 2))
            dist_j_new = distance_matrix[min_i, min_j] - dist_i_new
            
            tree[new_node_id] = [
                (nodes[min_i], max(0, dist_i_new)),
                (nodes[min_j], max(0, dist_j_new))
            ]
            
            new_distances = np.zeros((len(nodes) - 1, len(nodes) - 1))
            new_nodes = [nodes[k] for k in range(len(nodes)) if k != min_i and k != min_j]
            new_nodes.append(new_node_id)
            
            for i in range(len(new_nodes) - 1):
                for j in range(i + 1, len(new_nodes) - 1):
                    old_i = nodes.index(new_nodes[i])
                    old_j = nodes.index(new_nodes[j])
                    new_distances[i, j] = distance_matrix[old_i, old_j]
                    new_distances[j, i] = new_distances[i, j]
            
            for i in range(len(new_nodes) - 1):
                old_i = nodes.index(new_nodes[i])
                dist = 0.5 * (distance_matrix[old_i, min_i] + distance_matrix[old_i, min_j] - distance_matrix[min_i, min_j])
                new_distances[i, -1] = dist
                new_distances[-1, i] = dist
            
            distance_matrix = new_distances
            nodes = new_nodes
            new_node_id += 1
        
        if len(nodes) == 2:
            tree[new_node_id] = [
                (nodes[0], distance_matrix[0, 1] / 2),
                (nodes[1], distance_matrix[0, 1] / 2)
            ]
        
        root = new_node_id
        self.guide_tree = (tree, root)
        return self.guide_tree

    def _get_alignment_order(self, tree, root):
        order = []
        
        def traverse(node):
            if node not in tree or len(tree[node]) == 0:
                order.append(node)
            else:
                for child, _ in tree[node]:
                    traverse(child)
        
        traverse(root)
        return order

    def _align_profile_to_profile(self, profile1, profile2):
        n1 = len(profile1)
        n2 = len(profile2)
        len1 = len(profile1[0]) if n1 > 0 else 0
        len2 = len(profile2[0]) if n2 > 0 else 0
        
        dp = np.zeros((len1 + 1, len2 + 1))
        traceback = np.zeros((len1 + 1, len2 + 1), dtype=int)
        
        for i in range(1, len1 + 1):
            dp[i, 0] = dp[i-1, 0] + self.gap_open
        
        for j in range(1, len2 + 1):
            dp[0, j] = dp[0, j-1] + self.gap_open
        
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                match_score = 0
                for seq1 in profile1:
                    for seq2 in profile2:
                        a1, a2 = seq1[i-1], seq2[j-1]
                        if a1 != '-' and a2 != '-':
                            match_score += self.match if a1 == a2 else self.mismatch
                match_score /= (n1 * n2) if n1 * n2 > 0 else 1
                
                match = dp[i-1, j-1] + match_score
                gap_in_2 = dp[i-1, j] + self.gap_open
                gap_in_1 = dp[i, j-1] + self.gap_open
                
                max_val = max(match, gap_in_2, gap_in_1)
                dp[i, j] = max_val
                
                if max_val == match:
                    traceback[i, j] = 0
                elif max_val == gap_in_2:
                    traceback[i, j] = 1
                else:
                    traceback[i, j] = 2
        
        i, j = len1, len2
        aligned_profile1 = ['' for _ in range(n1)]
        aligned_profile2 = ['' for _ in range(n2)]
        
        while i > 0 or j > 0:
            if traceback[i, j] == 0:
                for k in range(n1):
                    aligned_profile1[k] = profile1[k][i-1] + aligned_profile1[k]
                for k in range(n2):
                    aligned_profile2[k] = profile2[k][j-1] + aligned_profile2[k]
                i -= 1
                j -= 1
            elif traceback[i, j] == 1:
                for k in range(n1):
                    aligned_profile1[k] = profile1[k][i-1] + aligned_profile1[k]
                for k in range(n2):
                    aligned_profile2[k] = '-' + aligned_profile2[k]
                i -= 1
            else:
                for k in range(n1):
                    aligned_profile1[k] = '-' + aligned_profile1[k]
                for k in range(n2):
                    aligned_profile2[k] = profile2[k][j-1] + aligned_profile2[k]
                j -= 1
        
        return aligned_profile1 + aligned_profile2

    def align(self, sequences, names=None):
        self.sequences = sequences
        if names is None:
            self.sequence_names = [f'seq_{i}' for i in range(len(sequences))]
        else:
            self.sequence_names = names
        
        n = len(sequences)
        if n == 0:
            return []
        if n == 1:
            self.aligned_sequences = sequences
            return sequences
        
        self._build_distance_matrix()
        tree, root = self._neighbor_joining_tree(self.distance_matrix.copy())
        
        profiles = {i: [sequences[i]] for i in range(n)}
        
        def build_alignment(node):
            if node in profiles:
                return profiles[node]
            
            children = tree.get(node, [])
            if len(children) == 2:
                child1, _ = children[0]
                child2, _ = children[1]
                prof1 = build_alignment(child1)
                prof2 = build_alignment(child2)
                return self._align_profile_to_profile(prof1, prof2)
            elif len(children) == 1:
                child, _ = children[0]
                return build_alignment(child)
            return []
        
        self.aligned_sequences = build_alignment(root)
        
        order = self._get_alignment_order(tree, root)
        name_map = {i: self.sequence_names[i] for i in range(n)}
        ordered_aligned = []
        ordered_names = []
        
        for idx in order:
            if idx < n:
                pos_in_aligned = order.index(idx)
                if pos_in_aligned < len(self.aligned_sequences):
                    ordered_aligned.append(self.aligned_sequences[pos_in_aligned])
                    ordered_names.append(name_map[idx])
        
        self.aligned_sequences = ordered_aligned
        self.sequence_names = ordered_names
        
        return self.aligned_sequences

    def get_conservation(self):
        if not self.aligned_sequences:
            return []
        
        n_seqs = len(self.aligned_sequences)
        length = len(self.aligned_sequences[0])
        conservation = []
        
        for pos in range(length):
            residues = [seq[pos] for seq in self.aligned_sequences if seq[pos] != '-']
            if not residues:
                conservation.append(0.0)
            else:
                most_common = max(set(residues), key=residues.count)
                conservation.append(residues.count(most_common) / len(residues))
        
        return conservation

    def print_alignment(self, line_width=60):
        if not self.aligned_sequences:
            print("No alignment performed yet.")
            return
        
        n = len(self.aligned_sequences)
        max_name_len = max(len(name) for name in self.sequence_names)
        
        print(f"\nClustalW Multiple Sequence Alignment ({n} sequences)")
        print("=" * 80)
        
        conservation = self.get_conservation()
        
        for start in range(0, len(self.aligned_sequences[0]), line_width):
            end = min(start + line_width, len(self.aligned_sequences[0]))
            
            for i in range(n):
                print(f"{self.sequence_names[i]:<{max_name_len}}  {self.aligned_sequences[i][start:end]}")
            
            consensus = []
            for pos in range(start, end):
                residues = [seq[pos] for seq in self.aligned_sequences if seq[pos] != '-']
                if residues and conservation[pos] >= 0.7:
                    consensus.append(max(set(residues), key=residues.count))
                elif residues and conservation[pos] >= 0.4:
                    consensus.append(':')
                else:
                    consensus.append(' ')
            
            print(f"{'':<{max_name_len}}  {''.join(consensus)}")
            print()


class ProgressiveMSA:
    def __init__(self, **kwargs):
        self.clustal = ClustalW(**kwargs)
    
    def align(self, sequences, names=None):
        return self.clustal.align(sequences, names)
    
    def get_alignment(self):
        return self.clustal.aligned_sequences
    
    def get_names(self):
        return self.clustal.sequence_names
    
    def get_conservation(self):
        return self.clustal.get_conservation()
    
    def print_alignment(self, line_width=60):
        self.clustal.print_alignment(line_width)
