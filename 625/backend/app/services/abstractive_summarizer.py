import torch
import re
import math
from transformers import (
    BartForConditionalGeneration,
    BartTokenizer,
    T5ForConditionalGeneration,
    T5Tokenizer,
    StoppingCriteria,
    StoppingCriteriaList
)
from typing import List, Tuple
import os
from dotenv import load_dotenv

load_dotenv()


class MaxCharLengthCriteria(StoppingCriteria):
    def __init__(self, tokenizer, max_char_length: int):
        self.tokenizer = tokenizer
        self.max_char_length = max_char_length

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        decoded = self.tokenizer.decode(input_ids[0], skip_special_tokens=True)
        if len(decoded) >= self.max_char_length:
            return True
        return False


class SlidingWindowChunker:
    def __init__(self, tokenizer, max_tokens: int = 1024, overlap_ratio: float = 0.15):
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.overlap_ratio = overlap_ratio

    def _split_into_paragraphs(self, text: str) -> List[str]:
        paragraphs = re.split(r'\n\s*\n|\r\n\s*\r\n', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_into_sentences(self, text: str) -> List[str]:
        try:
            import nltk
            sentences = nltk.sent_tokenize(text)
        except:
            sentences = re.split(r'(?<=[.!?。！？])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_text(self, text: str) -> List[str]:
        paragraphs = self._split_into_paragraphs(text)
        
        if len(paragraphs) <= 1:
            sentences = self._split_into_sentences(text)
            return self._chunk_by_tokens(sentences)
        
        return self._chunk_paragraphs_by_tokens(paragraphs)

    def _chunk_by_tokens(self, sentences: List[str]) -> List[str]:
        chunks = []
        current_chunk_sentences = []
        current_token_count = 0
        overlap_token_count = int(self.max_tokens * self.overlap_ratio)
        
        for sentence in sentences:
            sentence_tokens = len(self.tokenizer.encode(sentence, add_special_tokens=False))
            
            if current_token_count + sentence_tokens > self.max_tokens and current_chunk_sentences:
                chunk_text = ' '.join(current_chunk_sentences)
                chunks.append(chunk_text)
                
                overlap_sentences = []
                overlap_count = 0
                for s in reversed(current_chunk_sentences):
                    s_tokens = len(self.tokenizer.encode(s, add_special_tokens=False))
                    if overlap_count + s_tokens <= overlap_token_count:
                        overlap_sentences.insert(0, s)
                        overlap_count += s_tokens
                    else:
                        break
                
                current_chunk_sentences = overlap_sentences
                current_token_count = overlap_count
            
            current_chunk_sentences.append(sentence)
            current_token_count += sentence_tokens
        
        if current_chunk_sentences:
            chunks.append(' '.join(current_chunk_sentences))
        
        return chunks

    def _chunk_paragraphs_by_tokens(self, paragraphs: List[str]) -> List[str]:
        chunks = []
        current_chunk_paragraphs = []
        current_token_count = 0
        overlap_token_count = int(self.max_tokens * self.overlap_ratio)
        
        for paragraph in paragraphs:
            para_tokens = len(self.tokenizer.encode(paragraph, add_special_tokens=False))
            
            if current_token_count + para_tokens > self.max_tokens and current_chunk_paragraphs:
                chunk_text = '\n\n'.join(current_chunk_paragraphs)
                chunks.append(chunk_text)
                
                overlap_paragraphs = []
                overlap_count = 0
                for p in reversed(current_chunk_paragraphs):
                    p_tokens = len(self.tokenizer.encode(p, add_special_tokens=False))
                    if overlap_count + p_tokens <= overlap_token_count:
                        overlap_paragraphs.insert(0, p)
                        overlap_count += p_tokens
                    else:
                        break
                
                current_chunk_paragraphs = overlap_paragraphs
                current_token_count = overlap_count
            
            current_chunk_paragraphs.append(paragraph)
            current_token_count += para_tokens
        
        if current_chunk_paragraphs:
            chunks.append('\n\n'.join(current_chunk_paragraphs))
        
        return chunks


class IncrementalMerger:
    def __init__(self, tokenizer, max_tokens: int = 1024):
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens

    def merge_summaries(
        self,
        summaries: List[str],
        model,
        tokenizer,
        device: str,
        target_max_length: int = 150,
        target_min_length: int = 50,
        preserve_keywords: bool = True
    ) -> str:
        if len(summaries) == 0:
            return ""
        if len(summaries) == 1:
            return summaries[0]
        
        current_summary = summaries[0]
        
        for i in range(1, len(summaries)):
            combined_text = f"Previous summary: {current_summary}\n\nNew content: {summaries[i]}\n\nPlease create a unified summary:"
            
            combined_tokens = len(tokenizer.encode(combined_text))
            if combined_tokens > self.max_tokens:
                ratio = self.max_tokens / combined_tokens
                prev_keep = max(1, int(len(current_summary) * ratio * 0.6))
                new_keep = max(1, int(len(summaries[i]) * ratio * 0.4))
                combined_text = (
                    f"Previous summary: {current_summary[:prev_keep]}...\n\n"
                    f"New content: {summaries[i][:new_keep]}...\n\n"
                    f"Please create a unified summary:"
                )
            
            inputs = tokenizer(
                combined_text,
                max_length=self.max_tokens,
                truncation=True,
                return_tensors="pt"
            ).to(device)
            
            stopping_criteria = StoppingCriteriaList([
                MaxCharLengthCriteria(tokenizer, target_max_length)
            ])
            
            with torch.no_grad():
                summary_ids = model.generate(
                    inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    max_length=target_max_length,
                    min_length=target_min_length,
                    length_penalty=2.0,
                    num_beams=4,
                    early_stopping=True,
                    no_repeat_ngram_size=3 if preserve_keywords else 0,
                    stopping_criteria=stopping_criteria
                )
            
            current_summary = tokenizer.decode(
                summary_ids[0],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )
        
        return current_summary


class AbstractiveSummarizer:
    def __init__(self):
        self.device = os.getenv("DEVICE", "cpu")
        self.bart_model_name = os.getenv("MODEL_NAME_BART", "facebook/bart-large-cnn")
        self.t5_model_name = os.getenv("MODEL_NAME_T5", "t5-large")
        self.max_length = int(os.getenv("MAX_LENGTH", 1024))
        
        self.bart_model = None
        self.bart_tokenizer = None
        self.t5_model = None
        self.t5_tokenizer = None
        self.loaded_models = []
        
        self.bart_chunker = None
        self.t5_chunker = None
        self.bart_merger = None
        self.t5_merger = None

    def load_bart(self):
        if self.bart_model is None:
            print(f"Loading BART model: {self.bart_model_name}...")
            self.bart_tokenizer = BartTokenizer.from_pretrained(self.bart_model_name)
            self.bart_model = BartForConditionalGeneration.from_pretrained(
                self.bart_model_name
            ).to(self.device)
            self.bart_chunker = SlidingWindowChunker(self.bart_tokenizer, self.max_length)
            self.bart_merger = IncrementalMerger(self.bart_tokenizer, self.max_length)
            self.loaded_models.append("bart")
            print("BART model loaded successfully.")

    def load_t5(self):
        if self.t5_model is None:
            print(f"Loading T5 model: {self.t5_model_name}...")
            self.t5_tokenizer = T5Tokenizer.from_pretrained(self.t5_model_name)
            self.t5_model = T5ForConditionalGeneration.from_pretrained(
                self.t5_model_name
            ).to(self.device)
            self.t5_chunker = SlidingWindowChunker(self.t5_tokenizer, self.max_length)
            self.t5_merger = IncrementalMerger(self.t5_tokenizer, self.max_length)
            self.loaded_models.append("t5")
            print("T5 model loaded successfully.")

    def _generate_with_forced_stop(
        self,
        model,
        tokenizer,
        input_ids,
        attention_mask,
        max_length: int,
        min_length: int,
        preserve_keywords: bool = True
    ) -> str:
        stopping_criteria = StoppingCriteriaList([
            MaxCharLengthCriteria(tokenizer, max_length)
        ])
        
        with torch.no_grad():
            summary_ids = model.generate(
                input_ids,
                attention_mask=attention_mask,
                max_length=max_length * 3,
                min_length=min_length,
                length_penalty=2.0,
                num_beams=4,
                early_stopping=True,
                no_repeat_ngram_size=3 if preserve_keywords else 0,
                stopping_criteria=stopping_criteria
            )
        
        summary = tokenizer.decode(
            summary_ids[0],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True
        )
        
        if len(summary) > max_length:
            sentences = re.split(r'(?<=[.!?。！？])\s*', summary)
            truncated = ""
            for sentence in sentences:
                if len(truncated) + len(sentence) <= max_length:
                    truncated += sentence + " "
                else:
                    break
            summary = truncated.strip()
            if not summary:
                summary = summary[:max_length]
        
        return summary

    def summarize_with_bart(
        self,
        text: str,
        max_length: int = 150,
        min_length: int = 50,
        preserve_keywords: bool = True,
        enable_sliding_window: bool = True
    ) -> Tuple[str, int]:
        self.load_bart()
        
        text_tokens = len(self.bart_tokenizer.encode(text))
        chunks_processed = 1
        
        if enable_sliding_window and text_tokens > self.max_length:
            chunks = self.bart_chunker.chunk_text(text)
            chunks_processed = len(chunks)
            print(f"Sliding window: splitting text into {len(chunks)} chunks")
            
            chunk_summaries = []
            per_chunk_max = max(min_length + 20, max_length // max(1, len(chunks)))
            per_chunk_min = max(20, min_length // max(1, len(chunks)))
            
            for i, chunk in enumerate(chunks):
                print(f"  Processing chunk {i + 1}/{len(chunks)}...")
                inputs = self.bart_tokenizer(
                    [chunk],
                    max_length=self.max_length,
                    truncation=True,
                    return_tensors="pt"
                ).to(self.device)
                
                chunk_summary = self._generate_with_forced_stop(
                    self.bart_model,
                    self.bart_tokenizer,
                    inputs["input_ids"],
                    inputs["attention_mask"],
                    per_chunk_max,
                    per_chunk_min,
                    preserve_keywords
                )
                chunk_summaries.append(chunk_summary)
            
            if len(chunk_summaries) > 1:
                summary = self.bart_merger.merge_summaries(
                    chunk_summaries,
                    self.bart_model,
                    self.bart_tokenizer,
                    self.device,
                    target_max_length=max_length,
                    target_min_length=min_length,
                    preserve_keywords=preserve_keywords
                )
            else:
                summary = chunk_summaries[0]
        else:
            inputs = self.bart_tokenizer(
                [text],
                max_length=self.max_length,
                truncation=True,
                return_tensors="pt"
            ).to(self.device)
            
            summary = self._generate_with_forced_stop(
                self.bart_model,
                self.bart_tokenizer,
                inputs["input_ids"],
                inputs["attention_mask"],
                max_length,
                min_length,
                preserve_keywords
            )
        
        return summary, chunks_processed

    def summarize_with_t5(
        self,
        text: str,
        max_length: int = 150,
        min_length: int = 50,
        preserve_keywords: bool = True,
        language: str = "en",
        enable_sliding_window: bool = True
    ) -> Tuple[str, int]:
        self.load_t5()
        
        prefix = "summarize: "
        if language != "en":
            prefix = f"summarize: "
        
        text_tokens = len(self.t5_tokenizer.encode(prefix + text))
        chunks_processed = 1
        
        if enable_sliding_window and text_tokens > self.max_length:
            chunks = self.t5_chunker.chunk_text(text)
            chunks_processed = len(chunks)
            print(f"Sliding window: splitting text into {len(chunks)} chunks")
            
            chunk_summaries = []
            per_chunk_max = max(min_length + 20, max_length // max(1, len(chunks)))
            per_chunk_min = max(20, min_length // max(1, len(chunks)))
            
            for i, chunk in enumerate(chunks):
                print(f"  Processing chunk {i + 1}/{len(chunks)}...")
                preprocessed = prefix + chunk
                
                inputs = self.t5_tokenizer(
                    preprocessed,
                    max_length=self.max_length,
                    truncation=True,
                    return_tensors="pt"
                ).to(self.device)
                
                chunk_summary = self._generate_with_forced_stop(
                    self.t5_model,
                    self.t5_tokenizer,
                    inputs["input_ids"],
                    inputs["attention_mask"],
                    per_chunk_max,
                    per_chunk_min,
                    preserve_keywords
                )
                chunk_summaries.append(chunk_summary)
            
            if len(chunk_summaries) > 1:
                summary = self.t5_merger.merge_summaries(
                    chunk_summaries,
                    self.t5_model,
                    self.t5_tokenizer,
                    self.device,
                    target_max_length=max_length,
                    target_min_length=min_length,
                    preserve_keywords=preserve_keywords
                )
            else:
                summary = chunk_summaries[0]
        else:
            preprocessed = prefix + text
            
            inputs = self.t5_tokenizer(
                preprocessed,
                max_length=self.max_length,
                truncation=True,
                return_tensors="pt"
            ).to(self.device)
            
            summary = self._generate_with_forced_stop(
                self.t5_model,
                self.t5_tokenizer,
                inputs["input_ids"],
                inputs["attention_mask"],
                max_length,
                min_length,
                preserve_keywords
            )
        
        return summary, chunks_processed

    def summarize(
        self,
        text: str,
        model_type: str = "bart",
        max_length: int = 150,
        min_length: int = 50,
        preserve_keywords: bool = True,
        language: str = "en",
        enable_sliding_window: bool = True
    ) -> Tuple[str, int]:
        if model_type.lower() == "bart":
            return self.summarize_with_bart(
                text, max_length, min_length, preserve_keywords, enable_sliding_window
            )
        elif model_type.lower() == "t5":
            return self.summarize_with_t5(
                text, max_length, min_length, preserve_keywords, language, enable_sliding_window
            )
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
