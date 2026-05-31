import re
from collections import Counter
from typing import List, Set
from sklearn.feature_extraction.text import TfidfVectorizer
import nltk


nltk.download('averaged_perceptron_tagger', quiet=True)


class KeywordExtractor:
    def __init__(self):
        self.stopwords = set()
        self._load_stopwords()

    def _load_stopwords(self):
        try:
            from nltk.corpus import stopwords
            self.stopwords = set(stopwords.words('english'))
        except:
            self.stopwords = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
                'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were',
                'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'
            }

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'[^\w\s-]', ' ', text.lower())
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_keywords_tfidf(self, text: str, top_k: int = 10) -> List[str]:
        sentences = nltk.sent_tokenize(text) if len(text) > 100 else [text]
        
        try:
            tfidf = TfidfVectorizer(
                stop_words='english',
                max_features=100,
                ngram_range=(1, 2)
            )
            tfidf.fit(sentences)
            
            feature_names = tfidf.get_feature_names_out()
            scores = tfidf.transform([text]).toarray()[0]
            
            keyword_scores = [(word, score) for word, score in zip(feature_names, scores)]
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            keywords = [word for word, score in keyword_scores if score > 0.01][:top_k]
            return keywords
        except Exception as e:
            print(f"TF-IDF extraction error: {e}")
            return self.extract_keywords_frequency(text, top_k)

    def extract_keywords_frequency(self, text: str, top_k: int = 10) -> List[str]:
        cleaned_text = self._clean_text(text)
        words = cleaned_text.split()
        
        filtered_words = [
            word for word in words
            if word not in self.stopwords
            and len(word) > 3
            and not word.isdigit()
        ]
        
        word_freq = Counter(filtered_words)
        top_keywords = [word for word, _ in word_freq.most_common(top_k)]
        
        return top_keywords

    def extract_keywords_rake(self, text: str, top_k: int = 10) -> List[str]:
        phrases = self._generate_phrases(text)
        phrase_scores = {}
        
        for phrase in phrases:
            words = phrase.split()
            phrase_scores[phrase] = sum(1 / (1 + len(word)) for word in words)
        
        sorted_phrases = sorted(phrase_scores.items(), key=lambda x: x[1], reverse=True)
        return [phrase for phrase, _ in sorted_phrases[:top_k]]

    def _generate_phrases(self, text: str) -> List[str]:
        sentences = re.split(r'[.!?;,]', text.lower())
        phrases = []
        
        for sentence in sentences:
            words = re.findall(r'\b[a-z]{3,}\b', sentence)
            current_phrase = []
            
            for word in words:
                if word not in self.stopwords:
                    current_phrase.append(word)
                elif current_phrase:
                    phrases.append(' '.join(current_phrase))
                    current_phrase = []
            
            if current_phrase:
                phrases.append(' '.join(current_phrase))
        
        return list(set(phrases))

    def extract_keywords(self, text: str, top_k: int = 10, method: str = 'tfidf') -> List[str]:
        if method == 'tfidf':
            return self.extract_keywords_tfidf(text, top_k)
        elif method == 'frequency':
            return self.extract_keywords_frequency(text, top_k)
        elif method == 'rake':
            return self.extract_keywords_rake(text, top_k)
        else:
            return self.extract_keywords_tfidf(text, top_k)

    def highlight_keywords(self, text: str, keywords: List[str]) -> str:
        highlighted_text = text
        for keyword in keywords:
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            highlighted_text = pattern.sub(f'**{keyword}**', highlighted_text)
        return highlighted_text
