import re
import string
from typing import List

import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from Levenshtein import ratio as levenshtein_ratio


def clean_text(text: str) -> str:
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def tokenize_chinese(text: str) -> List[str]:
    return list(jieba.cut(text))


def extract_keywords(text: str, top_k: int = 20) -> List[str]:
    tokens = tokenize_chinese(text)
    tokens = [t.strip() for t in tokens if len(t.strip()) > 1 and t.strip() not in string.punctuation]
    if not tokens:
        return []
    vectorizer = TfidfVectorizer(tokenizer=lambda x: x, token_pattern=None, max_features=top_k)
    try:
        tfidf_matrix = vectorizer.fit_transform([" ".join(tokens)])
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]
        keyword_scores = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in keyword_scores[:top_k]]
    except ValueError:
        return tokens[:top_k]


def compute_levenshtein_similarity(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    return levenshtein_ratio(s1, s2)


def compute_jaccard_similarity(set1: set, set2: set) -> float:
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union)


def contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))