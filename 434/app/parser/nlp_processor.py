import re
from typing import List, Optional, Tuple

import spacy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.utils.text_utils import clean_text, contains_chinese


class NLPProcessor:
    def __init__(self, spacy_model: str = "zh_core_web_sm", bert_model: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self._spacy_model_name = spacy_model
        self._bert_model_name = bert_model
        self._nlp = None
        self._bert = None
        self._load_models()

    def _load_models(self):
        try:
            self._nlp = spacy.load(self._spacy_model_name)
        except OSError:
            print(f"Warning: SpaCy model '{self._spacy_model_name}' not found. Please run: python -m spacy download {self._spacy_model_name}")
            self._nlp = None

        try:
            self._bert = SentenceTransformer(self._bert_model_name)
        except Exception:
            print(f"Warning: BERT model '{self._bert_model_name}' not found. Using fallback.")
            self._bert = None

    @property
    def spacy_nlp(self):
        return self._nlp

    @property
    def bert_model(self):
        return self._bert

    def extract_entities(self, text: str) -> List[dict]:
        if not self._nlp:
            return []
        doc = self._nlp(text)
        entities = []
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PERSON", "GPE", "DATE", "MONEY", "PRODUCT", "WORK_OF_ART", "LANGUAGE"):
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                })
        return entities

    def extract_nouns(self, text: str) -> List[str]:
        if not self._nlp:
            return re.findall(r"\b\w+\b", text)
        doc = self._nlp(text)
        nouns = [token.lemma_ for token in doc if token.pos_ in ("NOUN", "PROPN") and not token.is_stop]
        return list(set(nouns))

    def extract_verbs(self, text: str) -> List[str]:
        if not self._nlp:
            return []
        doc = self._nlp(text)
        verbs = [token.lemma_ for token in doc if token.pos_ == "VERB" and not token.is_stop]
        return list(set(verbs))

    def compute_similarity_bert(self, text1: str, text2: str) -> float:
        if not self._bert:
            return self._fallback_similarity(text1, text2)
        try:
            embeddings = self._bert.encode([text1, text2], convert_to_numpy=True)
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception:
            return self._fallback_similarity(text1, text2)

    def compute_similarity_batch(self, query: str, documents: List[str]) -> List[float]:
        if not self._bert:
            return [self._fallback_similarity(query, doc) for doc in documents]
        try:
            query_embedding = self._bert.encode([query], convert_to_numpy=True)
            doc_embeddings = self._bert.encode(documents, convert_to_numpy=True)
            similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
            return [float(s) for s in similarities]
        except Exception:
            return [self._fallback_similarity(query, doc) for doc in documents]

    def _fallback_similarity(self, text1: str, text2: str) -> float:
        words1 = set(re.findall(r"\w+", text1.lower()))
        words2 = set(re.findall(r"\w+", text2.lower()))
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    def compute_skill_match(self, resume_skills: List[str], required_skills: List[str]) -> Tuple[float, List[str], List[str]]:
        if not required_skills:
            return 1.0, [], []

        resume_lower = [s.lower() for s in resume_skills]
        required_lower = [s.lower() for s in required_skills]

        matched = []
        missing = []

        for req in required_lower:
            found = False
            for res in resume_lower:
                if req == res or req in res or res in req:
                    matched.append(req)
                    found = True
                    break
            if not found:
                missing.append(req)

        score = len(matched) / len(required_lower) if required_lower else 0.0
        return score, matched, missing

    def extract_key_phrases(self, text: str, max_phrases: int = 20) -> List[str]:
        if not self._nlp:
            return re.findall(r"\b\w+\b", text)[:max_phrases]
        doc = self._nlp(text)
        phrases = []
        for chunk in doc.noun_chunks:
            if len(chunk.text) > 1 and not chunk.text.isdigit():
                phrases.append(chunk.text.strip())
        return list(dict.fromkeys(phrases))[:max_phrases]

    def summarize_text(self, text: str, max_sentences: int = 3) -> str:
        if not self._nlp:
            return text[:500]
        doc = self._nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        if not sentences:
            return text[:500]
        if len(sentences) <= max_sentences:
            return " ".join(sentences)
        scores = []
        for i, sent in enumerate(sentences):
            score = 0.0
            if i == 0:
                score += 0.3
            score += min(len(sent.split()), 30) * 0.02
            scores.append((score, sent))
        scores.sort(key=lambda x: x[0], reverse=True)
        selected = [s for _, s in scores[:max_sentences]]
        return " ".join(selected)