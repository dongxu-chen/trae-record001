import numpy as np
from sequence_alignment import NeedlemanWunsch, GAP
from substitution_matrices import SubstitutionMatrix

class SequenceDatabase:
    def __init__(self, seq_type='protein'):
        self.sequences = {}
        self.seq_type = seq_type
        self.sub_matrix = SubstitutionMatrix('blosum62' if seq_type == 'protein' else 'dna', seq_type)
    
    def add_sequence(self, name, sequence):
        self.sequences[name] = sequence.upper()
    
    def add_sequences(self, seq_dict):
        for name, seq in seq_dict.items():
            self.add_sequence(name, seq)
    
    def get_sequence(self, name):
        return self.sequences.get(name)
    
    def get_all_sequences(self):
        return self.sequences
    
    def search(self, query_seq, top_k=5, gap_penalty=-2):
        query_seq = query_seq.upper()
        scores = []
        
        for name, seq in self.sequences.items():
            nw = NeedlemanWunsch(
                query_seq, seq, gap_penalty=gap_penalty,
                matrix_type='blosum62' if self.seq_type == 'protein' else 'dna',
                seq_type=self.seq_type,
                use_rolling=True, find_all_solutions=False
            )
            nw.align()
            if nw.alignment_results:
                result = nw.alignment_results[0]
                scores.append((name, result.score, result.aligned_seq1, result.aligned_seq2, nw))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    
    def search_local(self, query_seq, top_k=5, gap_penalty=-2):
        from sequence_alignment import SmithWaterman
        query_seq = query_seq.upper()
        scores = []
        
        for name, seq in self.sequences.items():
            sw = SmithWaterman(
                query_seq, seq, gap_penalty=gap_penalty,
                matrix_type='blosum62' if self.seq_type == 'protein' else 'dna',
                seq_type=self.seq_type,
                use_rolling=True, find_all_solutions=False
            )
            sw.align()
            if sw.alignment_results:
                result = sw.alignment_results[0]
                scores.append((name, result.score, result.aligned_seq1, result.aligned_seq2, sw))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    
    def save_to_fasta(self, filename):
        with open(filename, 'w') as f:
            for name, seq in self.sequences.items():
                f.write(f">{name}\n")
                for i in range(0, len(seq), 60):
                    f.write(f"{seq[i:i+60]}\n")
    
    def load_from_fasta(self, filename):
        current_name = None
        current_seq = []
        
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('>'):
                    if current_name:
                        self.sequences[current_name] = ''.join(current_seq)
                    current_name = line[1:].split()[0]
                    current_seq = []
                elif line:
                    current_seq.append(line)
        
        if current_name:
            self.sequences[current_name] = ''.join(current_seq)

class ProgressiveAlignment:
    def __init__(self, seq_type='protein', gap_penalty=-2, matrix_type='blosum62'):
        self.seq_type = seq_type
        self.gap_penalty = gap_penalty
        self.matrix_type = matrix_type
        self.sub_matrix = SubstitutionMatrix(matrix_type, seq_type)
        self.aligned_sequences = {}
        self.guide_tree = None
        self.sequence_names = []
        self.sequences = {}
        self.consensus = None
    
    def add_sequences(self, seq_dict):
        self.sequences = {name: seq.upper() for name, seq in seq_dict.items()}
        self.sequence_names = list(self.sequences.keys())
    
    def _compute_distance_matrix(self):
        n = len(self.sequence_names)
        dist_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                seq1 = self.sequences[self.sequence_names[i]]
                seq2 = self.sequences[self.sequence_names[j]]
                
                nw = NeedlemanWunsch(
                    seq1, seq2, gap_penalty=self.gap_penalty,
                    matrix_type=self.matrix_type, seq_type=self.seq_type,
                    use_rolling=True, find_all_solutions=False
                )
                nw.align()
                
                if nw.alignment_results:
                    result = nw.alignment_results[0]
                    aligned1 = result.aligned_seq1
                    aligned2 = result.aligned_seq2
                    
                    identity = sum(1 for a, b in zip(aligned1, aligned2) 
                                  if a == b and a != GAP)
                    length = len(aligned1)
                    similarity = identity / length if length > 0 else 0
                    distance = 1 - similarity
                else:
                    distance = 1.0
                
                dist_matrix[i, j] = distance
                dist_matrix[j, i] = distance
        
        return dist_matrix
    
    def _build_guide_tree(self, dist_matrix):
        n = len(self.sequence_names)
        clusters = {i: [self.sequence_names[i]] for i in range(n)}
        tree = []
        active = list(range(n))
        
        while len(active) > 1:
            min_dist = float('inf')
            best_i, best_j = -1, -1
            
            for idx_i in range(len(active)):
                for idx_j in range(idx_i + 1, len(active)):
                    i = active[idx_i]
                    j = active[idx_j]
                    if dist_matrix[i, j] < min_dist:
                        min_dist = dist_matrix[i, j]
                        best_i, best_j = i, j
            
            new_cluster = clusters[best_i] + clusters[best_j]
            new_idx = max(active) + 1
            clusters[new_idx] = new_cluster
            tree.append((best_i, best_j, new_idx, min_dist))
            
            active.remove(best_i)
            active.remove(best_j)
            active.append(new_idx)
            
            n_new = n + 1
            if n_new > dist_matrix.shape[0]:
                new_dist = np.zeros((n_new, n_new))
                new_dist[:dist_matrix.shape[0], :dist_matrix.shape[1]] = dist_matrix
                dist_matrix = new_dist
            
            for k in active:
                if k != new_idx:
                    dist_i = dist_matrix[best_i, k]
                    dist_j = dist_matrix[best_j, k]
                    avg_dist = (len(clusters[best_i]) * dist_i + len(clusters[best_j]) * dist_j) / len(new_cluster)
                    dist_matrix[new_idx, k] = avg_dist
                    dist_matrix[k, new_idx] = avg_dist
        
        return tree, clusters
    
    def _align_profile_to_profile(self, profile1, profile2):
        len1 = len(profile1[next(iter(profile1))])
        len2 = len(profile2[next(iter(profile2))])
        
        score_matrix = np.zeros((len1 + 1, len2 + 1))
        traceback = np.zeros((len1 + 1, len2 + 1), dtype=int)
        
        for i in range(1, len1 + 1):
            score_matrix[i, 0] = i * self.gap_penalty
            traceback[i, 0] = 1
        
        for j in range(1, len2 + 1):
            score_matrix[0, j] = j * self.gap_penalty
            traceback[0, j] = 2
        
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                match_score = 0
                count = 0
                for name1, seq1 in profile1.items():
                    for name2, seq2 in profile2.items():
                        if seq1[i-1] != GAP and seq2[j-1] != GAP:
                            match_score += self.sub_matrix.get_score(seq1[i-1], seq2[j-1])
                            count += 1
                if count > 0:
                    match_score /= count
                
                diag = score_matrix[i-1, j-1] + match_score
                up = score_matrix[i-1, j] + self.gap_penalty
                left = score_matrix[i, j-1] + self.gap_penalty
                
                max_score = max(diag, up, left)
                score_matrix[i, j] = max_score
                
                if max_score == diag:
                    traceback[i, j] = 0
                elif max_score == up:
                    traceback[i, j] = 1
                else:
                    traceback[i, j] = 2
        
        i, j = len1, len2
        aligned_profile1 = {name: [] for name in profile1}
        aligned_profile2 = {name: [] for name in profile2}
        
        while i > 0 or j > 0:
            direction = traceback[i, j]
            
            if direction == 0:
                for name in profile1:
                    aligned_profile1[name].append(profile1[name][i-1])
                for name in profile2:
                    aligned_profile2[name].append(profile2[name][j-1])
                i -= 1
                j -= 1
            elif direction == 1:
                for name in profile1:
                    aligned_profile1[name].append(profile1[name][i-1])
                for name in profile2:
                    aligned_profile2[name].append(GAP)
                i -= 1
            else:
                for name in profile1:
                    aligned_profile1[name].append(GAP)
                for name in profile2:
                    aligned_profile2[name].append(profile2[name][j-1])
                j -= 1
        
        merged = {}
        for name, chars in aligned_profile1.items():
            merged[name] = ''.join(reversed(chars))
        for name, chars in aligned_profile2.items():
            merged[name] = ''.join(reversed(chars))
        
        return merged
    
    def align(self):
        if len(self.sequences) < 2:
            self.aligned_sequences = self.sequences.copy()
            return self.aligned_sequences
        
        if len(self.sequences) == 2:
            names = self.sequence_names
            nw = NeedlemanWunsch(
                self.sequences[names[0]], self.sequences[names[1]],
                gap_penalty=self.gap_penalty,
                matrix_type=self.matrix_type,
                seq_type=self.seq_type,
                use_rolling=True, find_all_solutions=False
            )
            nw.align()
            if nw.alignment_results:
                result = nw.alignment_results[0]
                self.aligned_sequences = {
                    names[0]: result.aligned_seq1,
                    names[1]: result.aligned_seq2
                }
            return self.aligned_sequences
        
        dist_matrix = self._compute_distance_matrix()
        tree, clusters = self._build_guide_tree(dist_matrix)
        self.guide_tree = tree
        
        profiles = {}
        for name in self.sequence_names:
            profiles[name] = {name: self.sequences[name]}
        
        for (i, j, new_idx, dist) in tree:
            cluster_i = clusters[i]
            cluster_j = clusters[j]
            
            if len(cluster_i) == 1 and cluster_i[0] in profiles:
                profile1 = profiles[cluster_i[0]]
            else:
                profile1 = profiles.get(i, {name: self.aligned_sequences.get(name, self.sequences[name]) for name in cluster_i})
            
            if len(cluster_j) == 1 and cluster_j[0] in profiles:
                profile2 = profiles[cluster_j[0]]
            else:
                profile2 = profiles.get(j, {name: self.aligned_sequences.get(name, self.sequences[name]) for name in cluster_j})
            
            merged_profile = self._align_profile_to_profile(profile1, profile2)
            profiles[new_idx] = merged_profile
            self.aligned_sequences.update(merged_profile)
        
        final_cluster = max(clusters.keys())
        if final_cluster in profiles:
            self.aligned_sequences = profiles[final_cluster]
        
        self._compute_consensus()
        return self.aligned_sequences
    
    def _compute_consensus(self):
        if not self.aligned_sequences:
            return None
        
        aligned_length = len(next(iter(self.aligned_sequences.values())))
        consensus = []
        
        for pos in range(aligned_length):
            residues = {}
            for seq in self.aligned_sequences.values():
                aa = seq[pos]
                residues[aa] = residues.get(aa, 0) + 1
            
            if residues:
                best_aa = max(residues.items(), key=lambda x: x[1])[0]
                consensus.append(best_aa)
        
        self.consensus = ''.join(consensus)
        return self.consensus
    
    def get_conservation_scores(self):
        if not self.aligned_sequences:
            return []
        
        aligned_length = len(next(iter(self.aligned_sequences.values())))
        n_seqs = len(self.aligned_sequences)
        scores = []
        
        for pos in range(aligned_length):
            residues = {}
            gap_count = 0
            for seq in self.aligned_sequences.values():
                aa = seq[pos]
                if aa == GAP:
                    gap_count += 1
                else:
                    residues[aa] = residues.get(aa, 0) + 1
            
            if n_seqs - gap_count > 0:
                max_count = max(residues.values()) if residues else 0
                identity = max_count / n_seqs
                
                similarity = 0
                for aa1, count1 in residues.items():
                    for aa2, count2 in residues.items():
                        if aa1 != GAP and aa2 != GAP:
                            if self.sub_matrix.get_score(aa1, aa2) > 0:
                                similarity += count1 * count2 / (n_seqs * n_seqs)
                
                conservation = (identity + similarity) / 2
            else:
                conservation = 0
            
            scores.append(conservation)
        
        return scores
    
    def get_conserved_regions(self, threshold=0.7, min_length=3):
        scores = self.get_conservation_scores()
        regions = []
        start = None
        
        for i, score in enumerate(scores):
            if score >= threshold:
                if start is None:
                    start = i
            else:
                if start is not None and i - start >= min_length:
                    regions.append((start, i - 1))
                start = None
        
        if start is not None and len(scores) - start >= min_length:
            regions.append((start, len(scores) - 1))
        
        return regions
    
    def get_statistics(self):
        if not self.aligned_sequences:
            return {}
        
        aligned_length = len(next(iter(self.aligned_sequences.values())))
        n_seqs = len(self.aligned_sequences)
        
        conservation_scores = self.get_conservation_scores()
        avg_conservation = sum(conservation_scores) / len(conservation_scores)
        
        identity_positions = sum(1 for s in conservation_scores if s >= 0.99)
        conserved_positions = sum(1 for s in conservation_scores if s >= 0.7)
        
        total_gaps = sum(seq.count(GAP) for seq in self.aligned_sequences.values())
        total_chars = aligned_length * n_seqs
        gap_percentage = total_gaps / total_chars * 100
        
        conserved_regions = self.get_conserved_regions()
        
        return {
            'n_sequences': n_seqs,
            'aligned_length': aligned_length,
            'average_conservation': avg_conservation,
            'identity_positions': identity_positions,
            'conserved_positions': conserved_positions,
            'gap_percentage': gap_percentage,
            'n_conserved_regions': len(conserved_regions),
            'conserved_regions': conserved_regions,
            'consensus': self.consensus
        }
