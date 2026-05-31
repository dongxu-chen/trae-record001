import re
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass, field


@dataclass
class RougeScore:
    rouge1: float = 0.0
    rouge2: float = 0.0
    rougel: float = 0.0
    rouge1_precision: float = 0.0
    rouge2_precision: float = 0.0
    rougel_precision: float = 0.0
    rouge1_recall: float = 0.0
    rouge2_recall: float = 0.0
    rougel_recall: float = 0.0


@dataclass
class EvaluationResult:
    rouge_scores: RougeScore
    factual_consistency: float = 0.0
    relevance_score: float = 0.0
    coverage_score: float = 0.0
    overall_score: float = 0.0
    key_points_covered: List[Dict] = field(default_factory=list)
    missing_key_points: List[Dict] = field(default_factory=list)


class RougeEvaluator:
    def __init__(self):
        self.stopwords = self._load_stopwords()

    def _load_stopwords(self) -> set:
        try:
            import nltk
            from nltk.corpus import stopwords
            return set(stopwords.words('english'))
        except:
            return {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
                'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were'
            }

    def _tokenize(self, text: str, remove_stopwords: bool = False) -> List[str]:
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = text.split()
        tokens = [t.strip() for t in tokens if t.strip()]
        
        if remove_stopwords:
            tokens = [t for t in tokens if t not in self.stopwords]
        
        return tokens

    def _get_ngrams(self, tokens: List[str], n: int) -> Counter:
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i + n])
            ngrams.append(ngram)
        return Counter(ngrams)

    def _lcs_length(self, x: List[str], y: List[str]) -> int:
        m, n = len(x), len(y)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if x[i - 1] == y[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        
        return dp[m][n]

    def _compute_precision_recall_f1(
        self,
        overlap: int,
        pred_count: int,
        ref_count: int
    ) -> Tuple[float, float, float]:
        precision = overlap / pred_count if pred_count > 0 else 0.0
        recall = overlap / ref_count if ref_count > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return precision, recall, f1

    def compute_rouge_n(
        self,
        candidate: str,
        reference: str,
        n: int = 1
    ) -> Tuple[float, float, float]:
        cand_tokens = self._tokenize(candidate)
        ref_tokens = self._tokenize(reference)
        
        if n == 1:
            cand_ngrams = Counter(cand_tokens)
            ref_ngrams = Counter(ref_tokens)
        else:
            cand_ngrams = self._get_ngrams(cand_tokens, n)
            ref_ngrams = self._get_ngrams(ref_tokens, n)
        
        overlap = sum((cand_ngrams & ref_ngrams).values())
        
        precision, recall, f1 = self._compute_precision_recall_f1(
            overlap,
            sum(cand_ngrams.values()),
            sum(ref_ngrams.values())
        )
        
        return precision, recall, f1

    def compute_rouge_l(
        self,
        candidate: str,
        reference: str
    ) -> Tuple[float, float, float]:
        cand_tokens = self._tokenize(candidate)
        ref_tokens = self._tokenize(reference)
        
        lcs_len = self._lcs_length(cand_tokens, ref_tokens)
        
        precision, recall, f1 = self._compute_precision_recall_f1(
            lcs_len,
            len(cand_tokens),
            len(ref_tokens)
        )
        
        return precision, recall, f1

    def evaluate(
        self,
        candidate: str,
        reference: str,
        references: Optional[List[str]] = None
    ) -> RougeScore:
        if references is None:
            references = [reference]
        
        all_rouge1 = []
        all_rouge2 = []
        all_rougel = []
        
        for ref in references:
            p1, r1, f1_1 = self.compute_rouge_n(candidate, ref, 1)
            p2, r2, f1_2 = self.compute_rouge_n(candidate, ref, 2)
            pl, rl, f1_l = self.compute_rouge_l(candidate, ref)
            
            all_rouge1.append((p1, r1, f1_1))
            all_rouge2.append((p2, r2, f1_2))
            all_rougel.append((pl, rl, f1_l))
        
        avg_rouge1_p = sum(p for p, _, _ in all_rouge1) / len(all_rouge1)
        avg_rouge1_r = sum(r for _, r, _ in all_rouge1) / len(all_rouge1)
        avg_rouge1_f1 = sum(f for _, _, f in all_rouge1) / len(all_rouge1)
        
        avg_rouge2_p = sum(p for p, _, _ in all_rouge2) / len(all_rouge2)
        avg_rouge2_r = sum(r for _, r, _ in all_rouge2) / len(all_rouge2)
        avg_rouge2_f1 = sum(f for _, _, f in all_rouge2) / len(all_rouge2)
        
        avg_rougel_p = sum(p for p, _, _ in all_rougel) / len(all_rougel)
        avg_rougel_r = sum(r for _, r, _ in all_rougel) / len(all_rougel)
        avg_rougel_f1 = sum(f for _, _, f in all_rougel) / len(all_rougel)
        
        return RougeScore(
            rouge1=avg_rouge1_f1,
            rouge2=avg_rouge2_f1,
            rougel=avg_rougel_f1,
            rouge1_precision=avg_rouge1_p,
            rouge2_precision=avg_rouge2_p,
            rougel_precision=avg_rougel_p,
            rouge1_recall=avg_rouge1_r,
            rouge2_recall=avg_rouge2_r,
            rougel_recall=avg_rougel_r
        )

    def evaluate_batch(
        self,
        candidates: List[str],
        references: List[List[str]]
    ) -> List[RougeScore]:
        results = []
        for candidate, refs in zip(candidates, references):
            result = self.evaluate(candidate, refs[0], refs)
            results.append(result)
        return results


class SummaryQualityEvaluator:
    def __init__(self):
        self.rouge_evaluator = RougeEvaluator()
        self.stopwords = self._load_stopwords()

    def _load_stopwords(self) -> set:
        try:
            import nltk
            from nltk.corpus import stopwords
            return set(stopwords.words('english'))
        except:
            return set()

    def _tokenize(self, text: str) -> List[str]:
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = text.split()
        return [t.strip() for t in tokens if t.strip() and t not in self.stopwords]

    def _extract_key_phrases(self, text: str, top_k: int = 10) -> List[str]:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            tfidf = TfidfVectorizer(stop_words='english', max_features=top_k, ngram_range=(1, 2))
            tfidf.fit([text])
            return list(tfidf.get_feature_names_out())
        except:
            tokens = self._tokenize(text)
            from collections import Counter
            return [word for word, _ in Counter(tokens).most_common(top_k)]

    def _compute_factual_consistency(
        self,
        summary: str,
        source_text: str
    ) -> float:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            tfidf = TfidfVectorizer(stop_words='english', ngram_range=(1, 3))
            tfidf_matrix = tfidf.fit_transform([source_text])
            feature_names = tfidf.get_feature_names_out()
            
            source_phrases = set()
            scores = tfidf_matrix.toarray()[0]
            for phrase, score in zip(feature_names, scores):
                if score > 0.1:
                    source_phrases.add(phrase)
            
            summary_lower = summary.lower()
            covered = sum(1 for p in source_phrases if p in summary_lower)
            total = len(source_phrases) if source_phrases else 1
            
            return min(1.0, covered / total)
        except Exception as e:
            print(f"Factual consistency error: {e}")
            return 0.5

    def _compute_relevance(
        self,
        summary: str,
        source_text: str
    ) -> float:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            tfidf = TfidfVectorizer(stop_words='english')
            tfidf_matrix = tfidf.fit_transform([source_text, summary])
            
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
        except Exception as e:
            print(f"Relevance error: {e}")
            return 0.5

    def _compute_coverage(
        self,
        summary: str,
        source_text: str
    ) -> Tuple[float, List[Dict], List[Dict]]:
        key_phrases = self._extract_key_phrases(source_text, top_k=15)
        
        summary_lower = summary.lower()
        covered = []
        missing = []
        
        for phrase in key_phrases:
            if phrase.lower() in summary_lower:
                covered.append({'phrase': phrase, 'found': True})
            else:
                missing.append({'phrase': phrase, 'found': False})
        
        coverage = len(covered) / len(key_phrases) if key_phrases else 0.0
        return coverage, covered, missing

    def _compute_human_correlation_estimate(
        self,
        rouge_scores: RougeScore,
        factual_consistency: float,
        relevance: float,
        coverage: float
    ) -> float:
        weights = {
            'rouge1': 0.20,
            'rouge2': 0.25,
            'rougel': 0.15,
            'factual': 0.25,
            'relevance': 0.08,
            'coverage': 0.07
        }
        
        score = (
            weights['rouge1'] * rouge_scores.rouge1 +
            weights['rouge2'] * rouge_scores.rouge2 +
            weights['rougel'] * rouge_scores.rougel +
            weights['factual'] * factual_consistency +
            weights['relevance'] * relevance +
            weights['coverage'] * coverage
        )
        
        return min(1.0, max(0.0, score))

    def comprehensive_evaluate(
        self,
        summary: str,
        source_text: str,
        reference_summary: Optional[str] = None
    ) -> EvaluationResult:
        if reference_summary is None:
            reference_summary = self._generate_reference_summary(source_text)
        
        rouge_scores = self.rouge_evaluator.evaluate(summary, reference_summary)
        
        factual_consistency = self._compute_factual_consistency(summary, source_text)
        relevance = self._compute_relevance(summary, source_text)
        coverage, covered, missing = self._compute_coverage(summary, source_text)
        
        overall_score = self._compute_human_correlation_estimate(
            rouge_scores,
            factual_consistency,
            relevance,
            coverage
        )
        
        return EvaluationResult(
            rouge_scores=rouge_scores,
            factual_consistency=factual_consistency,
            relevance_score=relevance,
            coverage_score=coverage,
            overall_score=overall_score,
            key_points_covered=covered,
            missing_key_points=missing
        )

    def _generate_reference_summary(self, source_text: str) -> str:
        sentences = re.split(r'(?<=[.!?。！？])\s+', source_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if len(sentences) <= 3:
            return source_text
        
        return ' '.join(sentences[:3])

    def get_quality_label(self, score: float) -> str:
        if score >= 0.8:
            return "Excellent"
        elif score >= 0.6:
            return "Good"
        elif score >= 0.4:
            return "Fair"
        elif score >= 0.2:
            return "Poor"
        else:
            return "Very Poor"
