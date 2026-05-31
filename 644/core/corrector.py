import jieba
from pypinyin import lazy_pinyin, pinyin, Style

from .domain_dict import DomainDictionary
from .edit_distance import EditDistanceCorrector
from .language_model import NGramLanguageModel
from .feedback import UserFeedback
from .seed_corrections import SeedCorrections
from .user_preference import UserPreference
from .multilingual import MultilingualCorrector
from .evaluation import CorrectionEvaluator

class SearchCorrector:
    def __init__(self, config):
        self.config = config
        self.base_threshold = config.CORRECTION_THRESHOLD
        self.min_threshold = config.MIN_THRESHOLD
        self.max_threshold = config.MAX_THRESHOLD
        self.max_candidates = config.MAX_CANDIDATES
        
        self.domain_dict = DomainDictionary(config.DOMAIN_DICT_PATH)
        self.edit_corrector = EditDistanceCorrector(
            self.domain_dict, 
            max_distance=config.MAX_EDIT_DISTANCE
        )
        self.language_model = NGramLanguageModel(
            n=config.NGRAM_N,
            save_path=config.LANGUAGE_MODEL_PATH
        )
        self.feedback = UserFeedback(config.USER_FEEDBACK_PATH)
        self.seed_corrections = SeedCorrections(config.SEED_CORRECTIONS_PATH)
        self.user_preference = UserPreference(config.USER_PREFERENCE_PATH)
        self.multilingual = MultilingualCorrector(self.domain_dict)
        self.evaluator = CorrectionEvaluator(config.EVALUATION_PATH, self.domain_dict)
        
        self.pinyin_similarity_weight = config.PINYIN_SIMILARITY_WEIGHT
        self.personalization_weight = config.PERSONALIZATION_WEIGHT
        self.enable_multilingual = config.ENABLE_MULTILINGUAL
        
        self._init_language_model()
    
    def _init_language_model(self):
        if not self.language_model.load():
            corpus = self.domain_dict.get_all_words()
            self.language_model.train(corpus)
            self.language_model.save()
    
    def _get_dynamic_threshold(self, query, user_id=None):
        query_len = len(query)
        
        if query_len <= 1:
            base = self.max_threshold
        elif query_len == 2:
            base = self.max_threshold * 0.95
        elif query_len == 3:
            base = self.base_threshold
        elif query_len == 4:
            base = self.base_threshold * 0.95
        elif query_len == 5:
            base = self.base_threshold * 0.9
        else:
            base = max(self.min_threshold, self.base_threshold * 0.85)
        
        if user_id:
            user_adjustment = self.user_preference.get_user_threshold_adjustment(user_id)
            base = max(self.min_threshold, min(self.max_threshold, base + user_adjustment))
        
        return base
    
    def _detect_pinyin_mixed(self, query):
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in query)
        has_english = any(c.isalpha() for c in query)
        return has_chinese and has_english
    
    def _pinyin_to_chinese(self, pinyin_str):
        return self.domain_dict.get_words_by_pinyin(pinyin_str)
    
    def _normalize_score(self, edit_distance, domain_weight, lm_score, feedback_score, 
                         pinyin_similarity=0, personalization_score=0):
        edit_score = 1.0 / (1.0 + edit_distance)
        
        max_weight = max(self.domain_dict.words.values()) if self.domain_dict.words else 1
        normalized_weight = domain_weight / max_weight
        
        lambda_val = self.config.LAMBDA
        combined_score = (
            lambda_val * edit_score +
            (1 - lambda_val) * 0.3 * normalized_weight +
            (1 - lambda_val) * 0.2 * min(lm_score, 1.0) +
            (1 - lambda_val) * 0.2 * feedback_score +
            (1 - lambda_val) * 0.15 * pinyin_similarity +
            (1 - lambda_val) * 0.15 * personalization_score
        )
        
        return combined_score
    
    def correct(self, query, threshold=None, max_candidates=None, user_id=None):
        if not query or not query.strip():
            return {
                'original': query,
                'corrected': query,
                'needs_correction': False,
                'candidates': []
            }
        
        query = query.strip()
        
        dynamic_threshold = self._get_dynamic_threshold(query, user_id)
        if threshold is None:
            threshold = dynamic_threshold
        if max_candidates is None:
            max_candidates = self.max_candidates
        
        if query in self.domain_dict.words:
            self.evaluator.record_correction(
                query, query, False, 1.0, 0
            )
            return {
                'original': query,
                'corrected': query,
                'needs_correction': False,
                'threshold': threshold,
                'dynamic_threshold': dynamic_threshold,
                'query_length': len(query),
                'candidates': []
            }
        
        multilingual_corrected = None
        multilingual_details = None
        if self.enable_multilingual:
            multilingual_corrected, multilingual_details = self.multilingual.correct_multilingual(query)
        
        seed_matches = self.seed_corrections.get_correction(query)
        seed_candidates = []
        if seed_matches:
            for correct_word, weight in seed_matches:
                dist = self.edit_corrector.edit_distance(query, correct_word)
                domain_weight = self.domain_dict.get_weight(correct_word) + weight
                seed_candidates.append((correct_word, dist, domain_weight, 1.0, True))
        
        edit_candidates = self.edit_corrector.correct(query)
        edit_candidates = [(w, d, wt, 0.0, False) for w, d, wt in edit_candidates]
        
        pinyin_mixed = self._detect_pinyin_mixed(query)
        query_pinyin = ''.join(lazy_pinyin(query))
        
        pinyin_vector_matches = self.domain_dict.vector_match_pinyin(query_pinyin, min_similarity=0.6)
        pinyin_candidates = []
        for word, similarity in pinyin_vector_matches:
            dist = self.edit_corrector.edit_distance(query, word)
            if dist <= self.config.MAX_EDIT_DISTANCE + 1:
                weight = self.domain_dict.get_weight(word)
                pinyin_candidates.append((word, dist, weight, similarity, False))
        
        if pinyin_mixed:
            pinyin_words = self._pinyin_to_chinese(query_pinyin)
            for word in pinyin_words:
                dist = self.edit_corrector.edit_distance(query, word)
                if dist <= self.config.MAX_EDIT_DISTANCE:
                    weight = self.domain_dict.get_weight(word)
                    similarity = self.domain_dict.pinyin_vector_similarity(query_pinyin, ''.join(lazy_pinyin(word)))
                    pinyin_candidates.append((word, dist, weight, similarity, False))
        
        if multilingual_corrected and multilingual_corrected != query:
            dist = self.edit_corrector.edit_distance(query, multilingual_corrected)
            weight = self.domain_dict.get_weight(multilingual_corrected) + 200
            pinyin_candidates.append((multilingual_corrected, 1, weight, 0.95, False))
        
        all_candidates = seed_candidates + edit_candidates + pinyin_candidates
        
        seen = {}
        for word, dist, weight, pinyin_sim, is_seed in all_candidates:
            if word not in seen:
                seen[word] = {
                    'dist': dist,
                    'weight': weight,
                    'pinyin_sim': pinyin_sim,
                    'is_seed': is_seed
                }
            else:
                if dist < seen[word]['dist']:
                    seen[word]['dist'] = dist
                seen[word]['weight'] = max(seen[word]['weight'], weight)
                seen[word]['pinyin_sim'] = max(seen[word]['pinyin_sim'], pinyin_sim)
                seen[word]['is_seed'] = seen[word]['is_seed'] or is_seed
        
        candidates_list = [(w, v['dist'], v['weight'], v['pinyin_sim'], v['is_seed']) for w, v in seen.items()]
        
        base_candidates = [(w, d, wt) for w, d, wt, ps, is_seed in candidates_list]
        scored_candidates = self.language_model.score_candidates(query, base_candidates)
        
        word_to_lm = {w: lm for w, d, wt, lm in scored_candidates}
        
        final_candidates = []
        for word, dist, weight, pinyin_sim, is_seed in candidates_list:
            lm_score = word_to_lm.get(word, 0.5)
            feedback_score = self.feedback.get_feedback_score(query, word)
            learned_weight = self.feedback.get_learned_weight(word)
            total_weight = weight + learned_weight
            
            personalization_score = 0.5
            if user_id:
                personalization_score = self.user_preference.get_word_preference_score(user_id, word)
            
            if is_seed:
                seed_bonus = 0.15
            else:
                seed_bonus = 0
            
            final_score = self._normalize_score(
                dist, total_weight, lm_score, feedback_score, 
                pinyin_sim, personalization_score
            ) + seed_bonus
            final_score = min(1.0, final_score)
            
            final_candidates.append({
                'word': word,
                'edit_distance': dist,
                'domain_weight': weight,
                'lm_score': lm_score,
                'feedback_score': feedback_score,
                'pinyin_similarity': pinyin_sim,
                'personalization_score': personalization_score,
                'is_seed_match': is_seed,
                'final_score': final_score
            })
        
        if user_id:
            final_candidates = self.user_preference.get_personalized_candidates(
                user_id, final_candidates, max_candidates
            )
        
        final_candidates.sort(key=lambda x: -x['final_score'])
        final_candidates = final_candidates[:max_candidates]
        
        needs_correction = False
        corrected_query = query
        
        if final_candidates and final_candidates[0]['final_score'] >= threshold:
            needs_correction = True
            corrected_query = final_candidates[0]['word']
        
        if multilingual_corrected and multilingual_corrected != query:
            ml_weight = self.domain_dict.get_weight(multilingual_corrected)
            if ml_weight > 0:
                ml_score = self._normalize_score(
                    1, ml_weight + 200, 0.8, 0.5, 0.95, 0.5
                ) + 0.2
                if not final_candidates or ml_score > final_candidates[0]['final_score']:
                    needs_correction = True
                    corrected_query = multilingual_corrected
                    final_candidates.insert(0, {
                        'word': multilingual_corrected,
                        'edit_distance': 1,
                        'domain_weight': ml_weight + 200,
                        'lm_score': 0.8,
                        'feedback_score': 0.5,
                        'pinyin_similarity': 0.95,
                        'personalization_score': 0.5,
                        'is_seed_match': False,
                        'is_multilingual': True,
                        'final_score': ml_score
                    })
                    final_candidates = final_candidates[:max_candidates]
        
        popular_corrections = self.feedback.get_popular_corrections(query, limit=3)
        
        improvement = None
        if needs_correction:
            improvement = self.evaluator.evaluate_improvement(query, corrected_query)
            self.evaluator.record_correction(
                query, corrected_query, True,
                final_candidates[0]['final_score'],
                final_candidates[0]['edit_distance']
            )
        else:
            self.evaluator.record_correction(query, query, False, 1.0, 0)
        
        result = {
            'original': query,
            'corrected': corrected_query,
            'needs_correction': needs_correction,
            'threshold': threshold,
            'dynamic_threshold': dynamic_threshold,
            'base_threshold': self.base_threshold,
            'query_length': len(query),
            'pinyin_mixed_detected': pinyin_mixed,
            'candidates': final_candidates,
            'popular_from_feedback': popular_corrections,
            'multilingual_details': multilingual_details,
            'improvement': improvement
        }
        
        if user_id:
            result['user_id'] = user_id
            result['user_profile'] = self.user_preference.get_user_profile(user_id)
        
        return result
    
    def record_click(self, original_query, corrected_query, suggestion, user_id=None):
        self.feedback.record_click(original_query, corrected_query, suggestion)
        self.evaluator.update_feedback(original_query, corrected_query, 'accept')
        
        if user_id and original_query != corrected_query:
            self.user_preference.record_correction(
                user_id, original_query, corrected_query, True
            )
    
    def record_skip(self, original_query, suggestion, user_id=None):
        self.feedback.record_skip(original_query, suggestion)
        self.evaluator.update_feedback(original_query, suggestion, 'skip')
        
        if user_id:
            self.user_preference.record_correction(
                user_id, original_query, suggestion, False
            )
    
    def set_threshold(self, threshold):
        self.base_threshold = max(0.0, min(1.0, threshold))
    
    def get_threshold(self):
        return self.base_threshold
    
    def get_dynamic_threshold_for_query(self, query, user_id=None):
        return self._get_dynamic_threshold(query, user_id)
    
    def add_domain_word(self, word, weight=1):
        self.domain_dict.add_word(word, weight)
        self.domain_dict.save_dictionary()
    
    def add_seed_correction(self, wrong, correct, weight=80):
        self.seed_corrections.add_correction(wrong, correct, weight)
    
    def get_domain_words(self):
        return self.domain_dict.get_all_words()
    
    def get_seed_corrections(self):
        return self.seed_corrections.get_all_seeds()
    
    def get_user_profile(self, user_id):
        return self.user_preference.get_user_profile(user_id)
    
    def get_evaluation_metrics(self):
        return {
            'overall': self.evaluator.get_overall_metrics(),
            'daily': self.evaluator.get_daily_metrics(7),
            'top_corrections': self.evaluator.get_top_corrections(10)
        }
