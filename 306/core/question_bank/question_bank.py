import json
import random
import os
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import hashlib
import uuid

from config import config


class Question:
    def __init__(self, question_data: Dict[str, Any]):
        self.id = question_data.get('id', str(uuid.uuid4()))
        self.type = question_data.get('type', 'single')
        self.subject = question_data.get('subject', '')
        self.difficulty = question_data.get('difficulty', 'medium')
        self.content = question_data.get('content', '')
        self.options = question_data.get('options', [])
        self.correct_answer = question_data.get('correct_answer', '')
        self.explanation = question_data.get('explanation', '')
        self.tags = question_data.get('tags', [])
        self.created_at = question_data.get('created_at', datetime.now().isoformat())
        self.version = question_data.get('version', 1)
        self.hash = question_data.get('hash', self._calculate_hash())
    
    def _calculate_hash(self) -> str:
        content_str = f"{self.content}{str(self.options)}{self.correct_answer}"
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def to_dict(self, include_answer: bool = True) -> Dict[str, Any]:
        data = {
            'id': self.id,
            'type': self.type,
            'subject': self.subject,
            'difficulty': self.difficulty,
            'content': self.content,
            'options': self.options.copy() if self.type in ['single', 'multiple', 'true_false'] else [],
            'explanation': self.explanation,
            'tags': self.tags,
            'version': self.version
        }
        if include_answer:
            data['correct_answer'] = self.correct_answer
        return data
    
    def shuffle_options(self) -> None:
        if self.type in ['single', 'multiple'] and self.options:
            correct_idx = None
            if isinstance(self.correct_answer, str):
                for i, opt in enumerate(self.options):
                    if opt == self.correct_answer:
                        correct_idx = i
                        break
            
            indices = list(range(len(self.options)))
            random.shuffle(indices)
            
            shuffled_options = [self.options[i] for i in indices]
            self.options = shuffled_options
            
            if correct_idx is not None:
                self.correct_answer = self.options[indices.index(correct_idx)]
    
    def check_answer(self, user_answer: Any) -> Tuple[bool, float]:
        if self.type == 'single':
            is_correct = user_answer == self.correct_answer
            return is_correct, 1.0 if is_correct else 0.0
        
        elif self.type == 'multiple':
            if not isinstance(user_answer, list):
                return False, 0.0
            correct_set = set(self.correct_answer) if isinstance(self.correct_answer, list) else {self.correct_answer}
            user_set = set(user_answer)
            if correct_set == user_set:
                return True, 1.0
            intersection = correct_set & user_set
            return False, len(intersection) / len(correct_set) if correct_set else 0.0
        
        elif self.type == 'true_false':
            is_correct = str(user_answer).lower() == str(self.correct_answer).lower()
            return is_correct, 1.0 if is_correct else 0.0
        
        elif self.type == 'text':
            similarity = self._text_similarity(str(user_answer), str(self.correct_answer))
            return similarity >= 0.8, similarity
        
        return False, 0.0
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)


class QuestionBank:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(config.DATA_DIR, 'question_bank.json')
        self.questions: Dict[str, Question] = {}
        self._load_questions()
    
    def _load_questions(self) -> None:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for q_data in data:
                        q = Question(q_data)
                        self.questions[q.id] = q
            except Exception as e:
                print(f"Error loading question bank: {e}")
    
    def save_questions(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        data = [q.to_dict(include_answer=True) for q in self.questions.values()]
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_question(self, question_data: Dict[str, Any]) -> Question:
        q = Question(question_data)
        self.questions[q.id] = q
        self.save_questions()
        return q
    
    def add_questions_batch(self, questions_data: List[Dict[str, Any]]) -> List[Question]:
        added = []
        for q_data in questions_data:
            q = Question(q_data)
            self.questions[q.id] = q
            added.append(q)
        self.save_questions()
        return added
    
    def get_question(self, question_id: str) -> Optional[Question]:
        return self.questions.get(question_id)
    
    def update_question(self, question_id: str, updates: Dict[str, Any]) -> Optional[Question]:
        if question_id not in self.questions:
            return None
        
        q = self.questions[question_id]
        for key, value in updates.items():
            if hasattr(q, key):
                setattr(q, key, value)
        q.version += 1
        q.hash = q._calculate_hash()
        self.save_questions()
        return q
    
    def delete_question(self, question_id: str) -> bool:
        if question_id in self.questions:
            del self.questions[question_id]
            self.save_questions()
            return True
        return False
    
    def list_questions(self, filters: Optional[Dict[str, Any]] = None) -> List[Question]:
        questions = list(self.questions.values())
        
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    questions = [q for q in questions if getattr(q, key) in value]
                else:
                    questions = [q for q in questions if getattr(q, key) == value]
        
        return questions
    
    def get_all_subjects(self) -> List[str]:
        subjects = set()
        for q in self.questions.values():
            if q.subject:
                subjects.add(q.subject)
        return sorted(list(subjects))
    
    def get_all_tags(self) -> List[str]:
        tags = set()
        for q in self.questions.values():
            tags.update(q.tags)
        return sorted(list(tags))
    
    def _filter_questions(self, 
                         subject: Optional[str] = None,
                         difficulty: Optional[str] = None,
                         tags: Optional[List[str]] = None,
                         exclude_ids: Optional[List[str]] = None) -> List[Question]:
        questions = list(self.questions.values())
        
        if subject:
            questions = [q for q in questions if q.subject == subject]
        
        if difficulty:
            questions = [q for q in questions if q.difficulty == difficulty]
        
        if tags:
            questions = [q for q in questions if any(tag in q.tags for tag in tags)]
        
        if exclude_ids:
            questions = [q for q in questions if q.id not in exclude_ids]
        
        return questions
    
    def select_random_questions(self,
                                 count: int,
                                 subject: Optional[str] = None,
                                 difficulty: Optional[str] = None,
                                 tags: Optional[List[str]] = None,
                                 exclude_ids: Optional[List[str]] = None,
                                 shuffle_options: bool = True,
                                 shuffle_questions: bool = True) -> List[Question]:
        filtered = self._filter_questions(subject, difficulty, tags, exclude_ids)
        
        if count > len(filtered):
            print(f"Warning: Requested {count} questions but only {len(filtered)} available")
            count = len(filtered)
        
        if shuffle_questions:
            selected = random.sample(filtered, count) if count > 0 else []
        else:
            selected = filtered[:count]
        
        if shuffle_options:
            for q in selected:
                q.shuffle_options()
        
        return selected
    
    def generate_exam(self,
                     exam_id: str,
                     count: Optional[int] = None,
                     subject: Optional[str] = None,
                     difficulty: Optional[str] = None,
                     tags: Optional[List[str]] = None,
                     difficulty_distribution: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        count = count or config.QUESTION_COUNT_PER_EXAM
        
        questions = []
        
        if difficulty_distribution:
            total_ratio = sum(difficulty_distribution.values())
            for diff, ratio in difficulty_distribution.items():
                diff_count = max(1, int(count * ratio / total_ratio))
                diff_questions = self.select_random_questions(
                    diff_count,
                    subject=subject,
                    difficulty=diff,
                    tags=tags,
                    exclude_ids=[q.id for q in questions]
                )
                questions.extend(diff_questions)
            
            if len(questions) < count:
                remaining = self.select_random_questions(
                    count - len(questions),
                    subject=subject,
                    tags=tags,
                    exclude_ids=[q.id for q in questions]
                )
                questions.extend(remaining)
        else:
            questions = self.select_random_questions(
                count,
                subject=subject,
                difficulty=difficulty,
                tags=tags
            )
        
        random.shuffle(questions)
        
        exam_data = {
            'exam_id': exam_id,
            'generated_at': datetime.now().isoformat(),
            'count': len(questions),
            'subject': subject,
            'difficulty': difficulty,
            'tags': tags,
            'questions': [q.to_dict(include_answer=False) for q in questions],
            'answer_key': {q.id: q.correct_answer for q in questions},
            'question_ids': [q.id for q in questions]
        }
        
        return exam_data
    
    def get_stats(self) -> Dict[str, Any]:
        total = len(self.questions)
        by_subject = {}
        by_difficulty = {}
        by_type = {}
        
        for q in self.questions.values():
            by_subject[q.subject] = by_subject.get(q.subject, 0) + 1
            by_difficulty[q.difficulty] = by_difficulty.get(q.difficulty, 0) + 1
            by_type[q.type] = by_type.get(q.type, 0) + 1
        
        return {
            'total_questions': total,
            'by_subject': by_subject,
            'by_difficulty': by_difficulty,
            'by_type': by_type,
            'subjects': self.get_all_subjects(),
            'tags': self.get_all_tags()
        }
