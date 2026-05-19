import numpy as np
from collections import defaultdict, namedtuple
from .needleman_wunsch import NeedlemanWunsch

BlastHit = namedtuple('BlastHit', ['query_id', 'subject_id', 'query_start', 
                                   'query_end', 'subject_start', 'subject_end',
                                   'alignment_score', 'identity', 'e_value',
                                   'aligned_query', 'aligned_subject'])


class LocalBLAST:
    def __init__(self, word_size=3, score_threshold=11, extend_threshold=0,
                 match=1, mismatch=-1, gap_open=-2, gap_extend=-1):
        self.word_size = word_size
        self.score_threshold = score_threshold
        self.extend_threshold = extend_threshold
        self.match = match
        self.mismatch = mismatch
        self.gap_open = gap_open
        self.gap_extend = gap_extend
        self.subject_database = {}
        self.word_index = defaultdict(list)
        
        self.blosum62 = {
            ('A', 'A'): 4, ('A', 'C'): 0, ('A', 'D'): -2, ('A', 'E'): -1,
            ('A', 'F'): -2, ('A', 'G'): 0, ('A', 'H'): -2, ('A', 'I'): -1,
            ('A', 'K'): -1, ('A', 'L'): -1, ('A', 'M'): -1, ('A', 'N'): -2,
            ('A', 'P'): -1, ('A', 'Q'): -1, ('A', 'R'): -1, ('A', 'S'): 1,
            ('A', 'T'): 0, ('A', 'V'): 0, ('A', 'W'): -3, ('A', 'Y'): -2,
            ('C', 'C'): 9, ('C', 'D'): -3, ('C', 'E'): -4, ('C', 'F'): -2,
            ('C', 'G'): -3, ('C', 'H'): -3, ('C', 'I'): -1, ('C', 'K'): -3,
            ('C', 'L'): -1, ('C', 'M'): -1, ('C', 'N'): -3, ('C', 'P'): -3,
            ('C', 'Q'): -3, ('C', 'R'): -3, ('C', 'S'): -1, ('C', 'T'): -1,
            ('C', 'V'): -1, ('C', 'W'): -2, ('C', 'Y'): -2,
            ('D', 'D'): 6, ('D', 'E'): 2, ('D', 'F'): -3, ('D', 'G'): -1,
            ('D', 'H'): -1, ('D', 'I'): -3, ('D', 'K'): -1, ('D', 'L'): -4,
            ('D', 'M'): -3, ('D', 'N'): 1, ('D', 'P'): -1, ('D', 'Q'): 0,
            ('D', 'R'): -2, ('D', 'S'): 0, ('D', 'T'): -1, ('D', 'V'): -3,
            ('D', 'W'): -4, ('D', 'Y'): -3,
            ('E', 'E'): 5, ('E', 'F'): -3, ('E', 'G'): -2, ('E', 'H'): 0,
            ('E', 'I'): -3, ('E', 'K'): 1, ('E', 'L'): -3, ('E', 'M'): -2,
            ('E', 'N'): 0, ('E', 'P'): -1, ('E', 'Q'): 2, ('E', 'R'): 0,
            ('E', 'S'): 0, ('E', 'T'): -1, ('E', 'V'): -2, ('E', 'W'): -3,
            ('E', 'Y'): -2,
            ('F', 'F'): 6, ('F', 'G'): -3, ('F', 'H'): 0, ('F', 'I'): 0,
            ('F', 'K'): -3, ('F', 'L'): 0, ('F', 'M'): 0, ('F', 'N'): -3,
            ('F', 'P'): -4, ('F', 'Q'): -3, ('F', 'R'): -3, ('F', 'S'): -2,
            ('F', 'T'): -2, ('F', 'V'): -1, ('F', 'W'): 1, ('F', 'Y'): 3,
            ('G', 'G'): 6, ('G', 'H'): -2, ('G', 'I'): -4, ('G', 'K'): -2,
            ('G', 'L'): -4, ('G', 'M'): -3, ('G', 'N'): 0, ('G', 'P'): -2,
            ('G', 'Q'): -2, ('G', 'R'): -2, ('G', 'S'): 0, ('G', 'T'): -2,
            ('G', 'V'): -3, ('G', 'W'): -2, ('G', 'Y'): -3,
            ('H', 'H'): 8, ('H', 'I'): -3, ('H', 'K'): -1, ('H', 'L'): -3,
            ('H', 'M'): -2, ('H', 'N'): 1, ('H', 'P'): -2, ('H', 'Q'): 0,
            ('H', 'R'): 0, ('H', 'S'): -1, ('H', 'T'): -2, ('H', 'V'): -3,
            ('H', 'W'): -2, ('H', 'Y'): 2,
            ('I', 'I'): 4, ('I', 'K'): -3, ('I', 'L'): 2, ('I', 'M'): 1,
            ('I', 'N'): -3, ('I', 'P'): -3, ('I', 'Q'): -3, ('I', 'R'): -3,
            ('I', 'S'): -2, ('I', 'T'): -1, ('I', 'V'): 3, ('I', 'W'): -3,
            ('I', 'Y'): -1,
            ('K', 'K'): 5, ('K', 'L'): -2, ('K', 'M'): -1, ('K', 'N'): 0,
            ('K', 'P'): -1, ('K', 'Q'): 1, ('K', 'R'): 2, ('K', 'S'): 0,
            ('K', 'T'): -1, ('K', 'V'): -2, ('K', 'W'): -3, ('K', 'Y'): -2,
            ('L', 'L'): 4, ('L', 'M'): 2, ('L', 'N'): -3, ('L', 'P'): -3,
            ('L', 'Q'): -2, ('L', 'R'): -2, ('L', 'S'): -2, ('L', 'T'): -1,
            ('L', 'V'): 1, ('L', 'W'): -2, ('L', 'Y'): -1,
            ('M', 'M'): 5, ('M', 'N'): -2, ('M', 'P'): -2, ('M', 'Q'): 0,
            ('M', 'R'): -1, ('M', 'S'): -1, ('M', 'T'): -1, ('M', 'V'): 1,
            ('M', 'W'): -1, ('M', 'Y'): -1,
            ('N', 'N'): 6, ('N', 'P'): -2, ('N', 'Q'): 0, ('N', 'R'): 0,
            ('N', 'S'): 1, ('N', 'T'): 0, ('N', 'V'): -3, ('N', 'W'): -4,
            ('N', 'Y'): -2,
            ('P', 'P'): 7, ('P', 'Q'): -1, ('P', 'R'): -2, ('P', 'S'): -1,
            ('P', 'T'): -1, ('P', 'V'): -2, ('P', 'W'): -4, ('P', 'Y'): -3,
            ('Q', 'Q'): 5, ('Q', 'R'): 1, ('Q', 'S'): 0, ('Q', 'T'): -1,
            ('Q', 'V'): -2, ('Q', 'W'): -2, ('Q', 'Y'): -1,
            ('R', 'R'): 5, ('R', 'S'): -1, ('R', 'T'): -1, ('R', 'V'): -3,
            ('R', 'W'): -3, ('R', 'Y'): -2,
            ('S', 'S'): 4, ('S', 'T'): 1, ('S', 'V'): -2, ('S', 'W'): -3,
            ('S', 'Y'): -2,
            ('T', 'T'): 5, ('T', 'V'): 0, ('T', 'W'): -2, ('T', 'Y'): -2,
            ('V', 'V'): 4, ('V', 'W'): -3, ('V', 'Y'): -1,
            ('W', 'W'): 11, ('W', 'Y'): 2, ('Y', 'Y'): 7,
        }
        
        for (a, b), score in list(self.blosum62.items()):
            if (b, a) not in self.blosum62:
                self.blosum62[(b, a)] = score

    def _get_score(self, a, b):
        if (a, b) in self.blosum62:
            return self.blosum62[(a, b)]
        return self.match if a == b else self.mismatch

    def build_database(self, sequences, sequence_ids=None):
        if sequence_ids is None:
            sequence_ids = [f'seq_{i}' for i in range(len(sequences))]
        
        self.subject_database = dict(zip(sequence_ids, sequences))
        
        self.word_index.clear()
        for seq_id, sequence in self.subject_database.items():
            for i in range(len(sequence) - self.word_size + 1):
                word = sequence[i:i+self.word_size]
                self.word_index[word].append((seq_id, i))
        
        return len(self.subject_database)

    def _find_seeds(self, query_sequence):
        seeds = []
        for i in range(len(query_sequence) - self.word_size + 1):
            query_word = query_sequence[i:i+self.word_size]
            
            for (subject_id, subject_pos) in self.word_index.get(query_word, []):
                seeds.append({
                    'query_pos': i,
                    'subject_id': subject_id,
                    'subject_pos': subject_pos,
                    'word': query_word
                })
        
        return seeds

    def _extend_hit(self, query, subject, query_start, subject_start):
        best_score = 0
        best_q_start = query_start
        best_q_end = query_start + self.word_size
        best_s_start = subject_start
        best_s_end = subject_start + self.word_size
        
        current_score = sum(self._get_score(query[query_start + i], 
                                            subject[subject_start + i])
                           for i in range(self.word_size))
        
        if current_score < self.score_threshold:
            return None
        
        max_left = min(query_start, subject_start)
        for left in range(1, max_left + 1):
            q_pos = query_start - left
            s_pos = subject_start - left
            current_score += self._get_score(query[q_pos], subject[s_pos])
            
            if current_score > best_score:
                best_score = current_score
                best_q_start = q_pos
                best_s_start = s_pos
            
            if current_score < best_score + self.extend_threshold:
                break
        
        max_right = min(len(query) - (query_start + self.word_size),
                       len(subject) - (subject_start + self.word_size))
        current_score = best_score
        for right in range(self.word_size, self.word_size + max_right):
            q_pos = query_start + right
            s_pos = subject_start + right
            current_score += self._get_score(query[q_pos], subject[s_pos])
            
            if current_score > best_score:
                best_score = current_score
                best_q_end = q_pos + 1
                best_s_end = s_pos + 1
            
            if current_score < best_score + self.extend_threshold:
                break
        
        return {
            'query_start': best_q_start,
            'query_end': best_q_end,
            'subject_start': best_s_start,
            'subject_end': best_s_end,
            'score': best_score
        }

    def _calculate_e_value(self, score, query_length):
        k = 0.1
        lambda_param = 0.267
        db_length = sum(len(seq) for seq in self.subject_database.values())
        e_value = k * db_length * query_length * np.exp(-lambda_param * score)
        return e_value

    def search(self, query_sequence, query_id='query', max_hits=50):
        seeds = self._find_seeds(query_sequence)
        
        hits = {}
        for seed in seeds:
            subject_id = seed['subject_id']
            subject_seq = self.subject_database[subject_id]
            
            extended = self._extend_hit(query_sequence, subject_seq,
                                         seed['query_pos'], seed['subject_pos'])
            
            if extended is not None:
                hit_key = (subject_id, extended['query_start'], extended['subject_start'])
                if hit_key not in hits or extended['score'] > hits[hit_key]['score']:
                    hits[hit_key] = {
                        **extended,
                        'subject_id': subject_id
                    }
        
        hit_list = []
        for hit in hits.values():
            q_aligned = query_sequence[hit['query_start']:hit['query_end']]
            s_aligned = self.subject_database[hit['subject_id']][hit['subject_start']:hit['subject_end']]
            
            matches = sum(1 for a, b in zip(q_aligned, s_aligned) if a == b)
            identity = matches / len(q_aligned) if len(q_aligned) > 0 else 0
            
            e_value = self._calculate_e_value(hit['score'], len(query_sequence))
            
            hit_list.append(BlastHit(
                query_id=query_id,
                subject_id=hit['subject_id'],
                query_start=hit['query_start'],
                query_end=hit['query_end'],
                subject_start=hit['subject_start'],
                subject_end=hit['subject_end'],
                alignment_score=hit['score'],
                identity=identity,
                e_value=e_value,
                aligned_query=q_aligned,
                aligned_subject=s_aligned
            ))
        
        hit_list.sort(key=lambda x: (-x.alignment_score, x.e_value))
        return hit_list[:max_hits]

    def print_search_results(self, hits):
        print(f"\nBLAST Search Results: {len(hits)} hits found")
        print("=" * 80)
        print(f"{'Subject ID':<15} {'Score':>8} {'E-value':>12} {'Identity':>10} "
              f"{'Query Pos':>15} {'Subject Pos':>15}")
        print("-" * 80)
        
        for hit in hits:
            print(f"{hit.subject_id:<15} {hit.alignment_score:>8} {hit.e_value:>12.2e} "
                  f"{hit.identity:>10.1%} "
                  f"{hit.query_start+1}-{hit.query_end:>10} "
                  f"{hit.subject_start+1}-{hit.subject_end:>10}")
        
        print("\nAlignment Details:")
        print("-" * 80)
        for hit in hits[:5]:
            print(f"\n> {hit.subject_id}")
            print(f"  Query:  {hit.aligned_query}")
            match_line = ''.join('|' if a == b else ' ' 
                                for a, b in zip(hit.aligned_query, hit.aligned_subject))
            print(f"          {match_line}")
            print(f"  Sbjct:  {hit.aligned_subject}")
