import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import json
import os
from collections import defaultdict

try:
    from sentence_transformers import SentenceTransformer, util
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    print("Warning: sentence-transformers not installed. Using fallback method.")

from config import config


class AnswerSimilarityModel(nn.Module):
    def __init__(self, embedding_dim: int = 768, hidden_dim: int = 512):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 256)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.encoder(x), p=2, dim=1)


class StructuredAnswer:
    def __init__(self, question_id: str, question_type: str, 
                 answer: Any, question_text: str = "", 
                 correct_answer: Optional[Any] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.question_id = question_id
        self.question_type = question_type
        self.answer = answer
        self.question_text = question_text
        self.correct_answer = correct_answer
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'question_id': self.question_id,
            'question_type': self.question_type,
            'answer': self.answer,
            'question_text': self.question_text,
            'correct_answer': self.correct_answer,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }
    
    def get_normalized_answer(self) -> str:
        if isinstance(self.answer, list):
            return ' '.join(sorted([str(a).strip().lower() for a in self.answer]))
        elif isinstance(self.answer, bool):
            return 'true' if self.answer else 'false'
        else:
            return str(self.answer).strip().lower()


class QuestionTypeConfig:
    SINGLE_CHOICE = 'single'
    MULTIPLE_CHOICE = 'multiple'
    TRUE_FALSE = 'true_false'
    FILL_BLANK = 'fill_blank'
    SHORT_ANSWER = 'short_answer'
    ESSAY = 'text'
    NUMERIC = 'numeric'
    
    WEIGHTS = {
        SINGLE_CHOICE: 1.0,
        MULTIPLE_CHOICE: 1.0,
        TRUE_FALSE: 1.0,
        FILL_BLANK: 0.8,
        SHORT_ANSWER: 0.9,
        ESSAY: 0.7,
        NUMERIC: 1.0
    }
    
    SIMILARITY_METHODS = {
        SINGLE_CHOICE: 'exact_match',
        MULTIPLE_CHOICE: 'set_match',
        TRUE_FALSE: 'exact_match',
        FILL_BLANK: 'text_similarity',
        SHORT_ANSWER: 'text_similarity',
        ESSAY: 'semantic_similarity',
        NUMERIC: 'numeric_similarity'
    }


class SimilarityAnalyzer:
    def __init__(self, model_name: str = 'paraphrase-MiniLM-L6-v2', use_cuda: bool = False):
        self.device = torch.device('cuda' if use_cuda and torch.cuda.is_available() else 'cpu')
        self.threshold = config.SIMILARITY_THRESHOLD
        
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.embedder = SentenceTransformer(model_name)
                self.embedder.to(self.device)
                self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
            except Exception as e:
                print(f"Error loading SentenceTransformer: {e}. Using fallback.")
                self.embedder = None
                self.embedding_dim = 300
        else:
            self.embedder = None
            self.embedding_dim = 300
        
        self.siamese_model = AnswerSimilarityModel(embedding_dim=self.embedding_dim).to(self.device)
        self.siamese_model.eval()
        
        self._vocab = defaultdict(int)
        self._word_vectors = {}
        self._init_fallback_vectors()
        
        self._similarity_cache: Dict[str, float] = {}
        
        self._question_type_config = QuestionTypeConfig()
    
    def _init_fallback_vectors(self) -> None:
        if not HAS_SENTENCE_TRANSFORMERS or self.embedder is None:
            np.random.seed(42)
            vocab_size = 10000
            self._fallback_embeddings = np.random.randn(vocab_size, self.embedding_dim)
    
    def _get_embedding_transformers(self, text: str) -> Optional[np.ndarray]:
        if self.embedder is None:
            return None
        
        try:
            with torch.no_grad():
                embedding = self.embedder.encode(text, convert_to_tensor=True, device=self.device)
            return embedding.cpu().numpy()
        except Exception as e:
            print(f"Error getting embedding from transformers: {e}")
            return None
    
    def _get_embedding_fallback(self, text: str) -> np.ndarray:
        words = text.lower().split()
        if not words:
            return np.zeros(self.embedding_dim)
        
        word_indices = []
        for word in words:
            if word not in self._vocab:
                self._vocab[word] = len(self._vocab) % 10000
            word_indices.append(self._vocab[word])
        
        if not word_indices:
            return np.zeros(self.embedding_dim)
        
        vectors = self._fallback_embeddings[word_indices]
        return np.mean(vectors, axis=0)
    
    def get_embedding(self, text: str) -> np.ndarray:
        if not text or not isinstance(text, str):
            return np.zeros(self.embedding_dim)
        
        embedding = self._get_embedding_transformers(text)
        if embedding is not None:
            return embedding
        
        return self._get_embedding_fallback(text)
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def exact_match_similarity(self, answer1: Any, answer2: Any) -> float:
        if isinstance(answer1, list) and isinstance(answer2, list):
            return 1.0 if sorted(answer1) == sorted(answer2) else 0.0
        elif isinstance(answer1, bool) and isinstance(answer2, bool):
            return 1.0 if answer1 == answer2 else 0.0
        elif isinstance(answer1, (int, float)) and isinstance(answer2, (int, float)):
            return 1.0 if abs(answer1 - answer2) < 1e-9 else 0.0
        else:
            return 1.0 if str(answer1).strip().lower() == str(answer2).strip().lower() else 0.0
    
    def set_match_similarity(self, answer1: List[Any], answer2: List[Any]) -> float:
        try:
            set1 = set([str(a).strip().lower() for a in answer1])
            set2 = set([str(a).strip().lower() for a in answer2])
            
            if not set1 or not set2:
                return 0.0
            
            intersection = len(set1 & set2)
            union = len(set1 | set2)
            
            return intersection / union if union > 0 else 0.0
        except Exception:
            return 0.0
    
    def numeric_similarity(self, answer1: Any, answer2: Any, tolerance: float = 0.01) -> float:
        try:
            num1 = float(answer1)
            num2 = float(answer2)
            
            if abs(num1) < 1e-10 and abs(num2) < 1e-10:
                return 1.0
            
            relative_diff = abs(num1 - num2) / max(abs(num1), abs(num2))
            return max(0.0, 1.0 - relative_diff / tolerance)
        except (ValueError, TypeError):
            return 0.0
    
    def text_similarity(self, text1: str, text2: str) -> float:
        if text1 == text2:
            return 1.0
        elif not text1 or not text2:
            return 0.0
        
        t1 = str(text1).strip().lower()
        t2 = str(text2).strip().lower()
        
        if t1 == t2:
            return 1.0
        
        embed1 = self.get_embedding(t1)
        embed2 = self.get_embedding(t2)
        cosine_sim = self.cosine_similarity(embed1, embed2)
        
        words1 = set(t1.split())
        words2 = set(t2.split())
        if words1 and words2:
            overlap = len(words1 & words2) / len(words1 | words2)
            cosine_sim = 0.7 * cosine_sim + 0.3 * overlap
        
        return cosine_sim
    
    def semantic_similarity(self, text1: str, text2: str) -> float:
        if text1 == text2:
            return 1.0
        elif not text1 or not text2:
            return 0.0
        
        t1 = str(text1).strip()
        t2 = str(text2).strip()
        
        if HAS_SENTENCE_TRANSFORMERS and self.embedder is not None:
            try:
                with torch.no_grad():
                    embeddings = self.embedder.encode([t1, t2], convert_to_tensor=True, device=self.device)
                    similarity = util.cos_sim(embeddings[0], embeddings[1]).item()
                return max(0.0, min(1.0, similarity))
            except Exception as e:
                print(f"Error in semantic similarity: {e}")
        
        return self.text_similarity(text1, text2)
    
    def calculate_similarity(self, answer1: Any, answer2: Any, 
                              question_type: str = 'text',
                              use_cache: bool = True) -> float:
        if use_cache:
            key = f"{question_type}:{hash(str(answer1))}:{hash(str(answer2))}"
            if key in self._similarity_cache:
                return self._similarity_cache[key]
        
        method = self._question_type_config.SIMILARITY_METHODS.get(question_type, 'text_similarity')
        
        if method == 'exact_match':
            similarity = self.exact_match_similarity(answer1, answer2)
        elif method == 'set_match':
            if isinstance(answer1, list) and isinstance(answer2, list):
                similarity = self.set_match_similarity(answer1, answer2)
            else:
                similarity = self.exact_match_similarity(answer1, answer2)
        elif method == 'numeric_similarity':
            similarity = self.numeric_similarity(answer1, answer2)
        elif method == 'semantic_similarity':
            similarity = self.semantic_similarity(str(answer1), str(answer2))
        else:
            similarity = self.text_similarity(str(answer1), str(answer2))
        
        if use_cache:
            key = f"{question_type}:{hash(str(answer1))}:{hash(str(answer2))}"
            self._similarity_cache[key] = similarity
        
        return similarity
    
    def calculate_question_pair_similarity(self, 
                                           structured1: StructuredAnswer,
                                           structured2: StructuredAnswer) -> Dict[str, Any]:
        if structured1.question_id != structured2.question_id:
            return {'error': 'Question IDs do not match'}
        
        question_type = structured1.question_type
        weight = self._question_type_config.WEIGHTS.get(question_type, 1.0)
        
        raw_similarity = self.calculate_similarity(
            structured1.answer,
            structured2.answer,
            question_type
        )
        
        weighted_similarity = raw_similarity * weight
        
        return {
            'question_id': structured1.question_id,
            'question_type': question_type,
            'question_text': structured1.question_text,
            'raw_similarity': raw_similarity,
            'weighted_similarity': weighted_similarity,
            'weight': weight,
            'is_suspicious': raw_similarity >= self.threshold,
            'method': self._question_type_config.SIMILARITY_METHODS.get(question_type, 'text_similarity'),
            'answer1': structured1.answer,
            'answer2': structured2.answer,
            'answer1_normalized': structured1.get_normalized_answer(),
            'answer2_normalized': structured2.get_normalized_answer(),
            'timestamp': datetime.now().isoformat()
        }
    
    def analyze_student_pair(self, student1_id: str, 
                              student2_id: str,
                              answers1: List[StructuredAnswer],
                              answers2: List[StructuredAnswer]) -> Dict[str, Any]:
        question_similarities = []
        suspicious_questions = []
        total_weight = 0.0
        weighted_sum = 0.0
        
        answers1_map = {a.question_id: a for a in answers1}
        answers2_map = {a.question_id: a for a in answers2}
        
        common_question_ids = set(answers1_map.keys()) & set(answers2_map.keys())
        
        for qid in common_question_ids:
            a1 = answers1_map[qid]
            a2 = answers2_map[qid]
            
            result = self.calculate_question_pair_similarity(a1, a2)
            
            if 'error' not in result:
                question_similarities.append(result)
                total_weight += result['weight']
                weighted_sum += result['weighted_similarity']
                
                if result['is_suspicious']:
                    suspicious_questions.append(result)
        
        overall_similarity = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        return {
            'student1_id': student1_id,
            'student2_id': student2_id,
            'common_question_count': len(common_question_ids),
            'total_weight': total_weight,
            'overall_similarity': overall_similarity,
            'max_similarity': max([s['raw_similarity'] for s in question_similarities]) if question_similarities else 0.0,
            'avg_similarity': np.mean([s['raw_similarity'] for s in question_similarities]) if question_similarities else 0.0,
            'suspicious_count': len(suspicious_questions),
            'suspicious_ratio': len(suspicious_questions) / len(common_question_ids) if common_question_ids else 0.0,
            'is_suspicious': overall_similarity >= self.threshold or len(suspicious_questions) >= 3,
            'question_similarities': question_similarities,
            'suspicious_questions': suspicious_questions,
            'analyzed_at': datetime.now().isoformat()
        }
    
    def analyze_exam_answers_structured(self, 
                                         exam_submissions: List[Dict[str, Any]]) -> Dict[str, Any]:
        structured_submissions: Dict[str, List[StructuredAnswer]] = defaultdict(list)
        
        for submission in exam_submissions:
            student_id = submission.get('student_id')
            if not student_id:
                continue
            
            answers = submission.get('answers', [])
            if isinstance(answers, dict):
                for qid, ans_data in answers.items():
                    if isinstance(ans_data, dict):
                        structured = StructuredAnswer(
                            question_id=qid,
                            question_type=ans_data.get('question_type', 'text'),
                            answer=ans_data.get('answer', ''),
                            question_text=ans_data.get('question_text', ''),
                            correct_answer=ans_data.get('correct_answer'),
                            metadata=ans_data.get('metadata')
                        )
                    else:
                        structured = StructuredAnswer(
                            question_id=qid,
                            question_type='text',
                            answer=ans_data
                        )
                    structured_submissions[student_id].append(structured)
            elif isinstance(answers, list):
                for ans_data in answers:
                    if isinstance(ans_data, dict):
                        structured = StructuredAnswer(
                            question_id=ans_data.get('question_id', ''),
                            question_type=ans_data.get('question_type', 'text'),
                            answer=ans_data.get('answer', ''),
                            question_text=ans_data.get('question_text', ''),
                            correct_answer=ans_data.get('correct_answer'),
                            metadata=ans_data.get('metadata')
                        )
                        structured_submissions[student_id].append(structured)
        
        student_ids = list(structured_submissions.keys())
        pair_results = []
        suspicious_pairs = []
        student_risk_scores: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'similar_scores': [],
            'suspicious_count': 0,
            'total_comparisons': 0
        })
        
        for i in range(len(student_ids)):
            for j in range(i + 1, len(student_ids)):
                sid1 = student_ids[i]
                sid2 = student_ids[j]
                
                pair_result = self.analyze_student_pair(
                    sid1, sid2,
                    structured_submissions[sid1],
                    structured_submissions[sid2]
                )
                
                pair_results.append(pair_result)
                
                if pair_result['is_suspicious']:
                    suspicious_pairs.append(pair_result)
                    
                    for sid in [sid1, sid2]:
                        student_risk_scores[sid]['similar_scores'].append(pair_result['overall_similarity'])
                        student_risk_scores[sid]['suspicious_count'] += pair_result['suspicious_count']
                        student_risk_scores[sid]['total_comparisons'] += 1
        
        overall_stats = self._calculate_overall_stats(pair_results, suspicious_pairs)
        student_risk = self._calculate_student_risks(student_risk_scores, structured_submissions)
        
        return {
            'exam_id': exam_submissions[0].get('exam_id') if exam_submissions else '',
            'analyzed_at': datetime.now().isoformat(),
            'analysis_type': 'structured_per_question',
            'total_students': len(student_ids),
            'total_pairs_analyzed': len(pair_results),
            'suspicious_pairs_count': len(suspicious_pairs),
            'threshold': self.threshold,
            'overall_stats': overall_stats,
            'pair_results': pair_results,
            'suspicious_pairs': suspicious_pairs,
            'student_risk_scores': student_risk,
            'per_question_analysis': self._get_per_question_analysis(structured_submissions)
        }
    
    def _calculate_overall_stats(self, pair_results: List[Dict], 
                                  suspicious_pairs: List[Dict]) -> Dict[str, Any]:
        if not pair_results:
            return {
                'avg_overall_similarity': 0.0,
                'max_overall_similarity': 0.0,
                'avg_suspicious_ratio': 0.0,
                'avg_suspicious_count': 0.0
            }
        
        return {
            'avg_overall_similarity': float(np.mean([p['overall_similarity'] for p in pair_results])),
            'max_overall_similarity': float(max([p['overall_similarity'] for p in pair_results])),
            'avg_suspicious_ratio': float(np.mean([p['suspicious_ratio'] for p in pair_results])),
            'avg_suspicious_count': float(np.mean([p['suspicious_count'] for p in pair_results])),
            'question_type_breakdown': self._get_question_type_breakdown(pair_results)
        }
    
    def _get_question_type_breakdown(self, pair_results: List[Dict]) -> Dict[str, Any]:
        type_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {'count': 0, 'total_similarity': 0.0})
        
        for pair in pair_results:
            for q_sim in pair.get('question_similarities', []):
                qtype = q_sim['question_type']
                type_stats[qtype]['count'] += 1
                type_stats[qtype]['total_similarity'] += q_sim['raw_similarity']
        
        breakdown = {}
        for qtype, stats in type_stats.items():
            breakdown[qtype] = {
                'count': stats['count'],
                'avg_similarity': stats['total_similarity'] / stats['count'] if stats['count'] > 0 else 0.0
            }
        
        return breakdown
    
    def _calculate_student_risks(self, 
                                  student_risk_scores: Dict[str, Dict[str, Any]],
                                  structured_submissions: Dict[str, List[StructuredAnswer]]) -> Dict[str, Dict[str, Any]]:
        result = {}
        
        for student_id, risk_data in student_risk_scores.items():
            scores = risk_data['similar_scores']
            total_answers = len(structured_submissions.get(student_id, []))
            
            if scores:
                avg_sim = float(np.mean(scores))
                max_sim = float(max(scores))
                suspicious_count = risk_data['suspicious_count']
                total_comparisons = risk_data['total_comparisons']
                
                if max_sim >= 0.95 or suspicious_count >= 5:
                    risk_level = 'critical'
                elif max_sim >= 0.85 or suspicious_count >= 3:
                    risk_level = 'high'
                elif max_sim >= 0.7 or suspicious_count >= 1:
                    risk_level = 'medium'
                else:
                    risk_level = 'low'
            else:
                avg_sim = 0.0
                max_sim = 0.0
                suspicious_count = 0
                total_comparisons = 0
                risk_level = 'low'
            
            result[student_id] = {
                'avg_similarity': avg_sim,
                'max_similarity': max_sim,
                'suspicious_count': suspicious_count,
                'total_comparisons': total_comparisons,
                'total_answers': total_answers,
                'risk_level': risk_level
            }
        
        return result
    
    def _get_per_question_analysis(self, 
                                     structured_submissions: Dict[str, List[StructuredAnswer]]) -> Dict[str, Any]:
        question_answers: Dict[str, List[Tuple[str, Any, str]]] = defaultdict(list)
        
        for student_id, answers in structured_submissions.items():
            for ans in answers:
                question_answers[ans.question_id].append((
                    student_id, ans.answer, ans.question_type
                ))
        
        question_stats = {}
        for qid, answers in question_answers.items():
            if len(answers) < 2:
                continue
            
            similarities = []
            for i in range(len(answers)):
                for j in range(i + 1, len(answers)):
                    sim = self.calculate_similarity(
                        answers[i][1], answers[j][1],
                        answers[i][2]
                    )
                    similarities.append(sim)
            
            if similarities:
                question_stats[qid] = {
                    'answer_count': len(answers),
                    'avg_similarity': float(np.mean(similarities)),
                    'max_similarity': float(max(similarities)),
                    'high_similarity_pairs': sum(1 for s in similarities if s >= self.threshold),
                    'question_type': answers[0][2]
                }
        
        return question_stats
    
    def analyze_exam_answers(self, exam_submissions: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.analyze_exam_answers_structured(exam_submissions)
    
    def check_answer_against_reference(self, student_answer: Any, 
                                        reference_answers: List[Any],
                                        question_type: str = 'text') -> Dict[str, Any]:
        max_similarity = 0.0
        most_similar = None
        
        for ref in reference_answers:
            sim = self.calculate_similarity(student_answer, ref, question_type)
            if sim > max_similarity:
                max_similarity = sim
                most_similar = ref
        
        return {
            'max_similarity': max_similarity,
            'most_similar_reference': most_similar,
            'is_suspicious': max_similarity >= self.threshold,
            'question_type': question_type
        }
    
    def calculate_jaccard_similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def calculate_levenshtein_ratio(self, text1: str, text2: str) -> float:
        if len(text1) == 0 and len(text2) == 0:
            return 1.0
        
        if len(text1) == 0 or len(text2) == 0:
            return 0.0
        
        m = len(text1)
        n = len(text2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if text1[i-1] == text2[j-1] else 1
                dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
        
        max_len = max(m, n)
        return 1.0 - dp[m][n] / max_len
    
    def comprehensive_similarity(self, answer1: Any, answer2: Any, 
                                  question_type: str = 'text') -> Dict[str, float]:
        if question_type in ['single', 'multiple', 'true_false', 'numeric']:
            sim = self.calculate_similarity(answer1, answer2, question_type)
            return {
                'similarity': sim,
                'is_suspicious': sim >= self.threshold
            }
        
        text1, text2 = str(answer1), str(answer2)
        cosine_sim = self.calculate_similarity(text1, text2, 'text')
        jaccard_sim = self.calculate_jaccard_similarity(text1, text2)
        levenshtein_sim = self.calculate_levenshtein_ratio(text1, text2)
        semantic_sim = self.semantic_similarity(text1, text2)
        
        combined = 0.4 * semantic_sim + 0.3 * cosine_sim + 0.2 * jaccard_sim + 0.1 * levenshtein_sim
        
        return {
            'cosine_similarity': cosine_sim,
            'jaccard_similarity': jaccard_sim,
            'levenshtein_similarity': levenshtein_sim,
            'semantic_similarity': semantic_sim,
            'combined_similarity': combined,
            'is_suspicious': combined >= self.threshold
        }
    
    def batch_get_embeddings(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([])
        
        if HAS_SENTENCE_TRANSFORMERS and self.embedder is not None:
            try:
                with torch.no_grad():
                    embeddings = self.embedder.encode(texts, convert_to_tensor=True, device=self.device)
                return embeddings.cpu().numpy()
            except Exception as e:
                print(f"Error in batch embedding: {e}")
        
        embeddings = []
        for text in texts:
            embeddings.append(self.get_embedding(text))
        return np.array(embeddings)
    
    def clear_cache(self) -> None:
        self._similarity_cache.clear()
    
    def save_report(self, analysis_result: Dict[str, Any], filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
    
    def set_threshold(self, threshold: float) -> None:
        self.threshold = max(0.0, min(1.0, threshold))
