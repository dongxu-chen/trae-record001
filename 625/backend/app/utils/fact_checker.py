import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from difflib import SequenceMatcher


@dataclass
class NumberFact:
    value: str
    normalized: float
    context: str
    unit: str = ""
    position: int = 0


@dataclass
class EntityFact:
    name: str
    entity_type: str
    context: str
    position: int = 0


@dataclass
class FactCheckResult:
    is_consistent: bool
    original_text: str
    summary_text: str
    number_issues: List[Dict] = field(default_factory=list)
    entity_issues: List[Dict] = field(default_factory=list)
    corrected_summary: str = ""
    corrections: List[Dict] = field(default_factory=list)


class NumberExtractor:
    NUMBER_PATTERNS = [
        (r'(?<!\w)(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\s*(%|percent|percentile)', 'percentage'),
        (r'(?<!\w)(\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?)\s*(billion|million|trillion|thousand|B|M|K)', 'large_number'),
        (r'(?<!\w)(\d+(?:\.\d+)?)\s*(%|percent)', 'percentage'),
        (r'(?<!\w)(\$?\d+(?:\.\d+)?)\s*(billion|million|trillion|thousand|B|M|K)', 'large_number'),
        (r'(?<!\w)(\d{1,3}(?:,\d{3})+(?:\.\d+)?)', 'formatted_number'),
        (r'(?<!\w)(\$?\d+(?:\.\d+)?)', 'plain_number'),
    ]
    
    UNIT_MAP = {
        'billion': 1e9, 'B': 1e9,
        'million': 1e6, 'M': 1e6,
        'trillion': 1e12,
        'thousand': 1e3, 'K': 1e3,
        '%': 0.01, 'percent': 0.01,
    }

    def extract(self, text: str) -> List[NumberFact]:
        facts = []
        seen_positions = set()
        
        for pattern, num_type in self.NUMBER_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = match.start()
                if any(abs(start - sp) < 3 for sp in seen_positions):
                    continue
                
                seen_positions.add(start)
                
                full_match = match.group(0)
                number_part = match.group(1) if match.lastindex else match.group(0)
                
                clean_number = number_part.replace('$', '').replace(',', '')
                
                try:
                    value = float(clean_number)
                except ValueError:
                    continue
                
                unit = ""
                if match.lastindex and match.lastindex >= 2:
                    unit = match.group(2).lower()
                elif num_type == 'percentage':
                    unit = 'percent'
                
                normalized = value
                if unit in self.UNIT_MAP:
                    if unit in ('%', 'percent'):
                        normalized = value
                    else:
                        normalized = value * self.UNIT_MAP[unit]
                
                context_start = max(0, start - 30)
                context_end = min(len(text), match.end() + 30)
                context = text[context_start:context_end].strip()
                
                facts.append(NumberFact(
                    value=full_match.strip(),
                    normalized=normalized,
                    context=context,
                    unit=unit,
                    position=start
                ))
        
        return facts


class EntityExtractor:
    DATE_PATTERNS = [
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}\b',
        r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
        r'\b\d{4}-\d{2}-\d{2}\b',
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s*\d{4}\b',
    ]
    
    CAPITALIZED_PATTERN = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
    
    KNOWN_ENTITIES = {
        'united states': 'GPE', 'united kingdom': 'GPE', 'new york': 'GPE',
        'los angeles': 'GPE', 'san francisco': 'GPE', 'hong kong': 'GPE',
        'new zealand': 'GPE', 'south korea': 'GPE', 'north korea': 'GPE',
        'world health organization': 'ORG', 'united nations': 'ORG',
        'european union': 'ORG', 'world bank': 'ORG',
        'international monetary fund': 'ORG',
    }

    def extract(self, text: str) -> List[EntityFact]:
        facts = []
        seen = set()
        
        for pattern in self.DATE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entity = match.group(0)
                if entity.lower() not in seen:
                    seen.add(entity.lower())
                    context_start = max(0, match.start() - 30)
                    context_end = min(len(text), match.end() + 30)
                    facts.append(EntityFact(
                        name=entity,
                        entity_type='DATE',
                        context=text[context_start:context_end].strip(),
                        position=match.start()
                    ))
        
        for entity, etype in self.KNOWN_ENTITIES.items():
            for match in re.finditer(re.escape(entity), text, re.IGNORECASE):
                if entity.lower() not in seen:
                    seen.add(entity.lower())
                    context_start = max(0, match.start() - 30)
                    context_end = min(len(text), match.end() + 30)
                    facts.append(EntityFact(
                        name=match.group(0),
                        entity_type=etype,
                        context=text[context_start:context_end].strip(),
                        position=match.start()
                    ))
        
        for match in re.finditer(self.CAPITALIZED_PATTERN, text):
            entity = match.group(1)
            if entity.lower() not in seen and len(entity) > 3:
                skip_words = {'The', 'This', 'That', 'These', 'Those', 'However', 'Therefore',
                             'Although', 'Because', 'Since', 'While', 'When', 'Where', 'Which',
                             'There', 'Here', 'Every', 'Each', 'Some', 'Most', 'Many', 'Such',
                             'Other', 'Another', 'First', 'Second', 'Third', 'Last', 'Next',
                             'According', 'Based', 'Using', 'Using', 'In', 'On', 'At', 'For',
                             'With', 'From', 'After', 'Before', 'During', 'Between'}
                words = entity.split()
                if any(w in skip_words for w in words):
                    continue
                
                seen.add(entity.lower())
                context_start = max(0, match.start() - 30)
                context_end = min(len(text), match.end() + 30)
                facts.append(EntityFact(
                    name=entity,
                    entity_type='PROPER',
                    context=text[context_start:context_end].strip(),
                    position=match.start()
                ))
        
        return facts


class FactChecker:
    def __init__(self, number_tolerance: float = 0.05):
        self.number_extractor = NumberExtractor()
        self.entity_extractor = EntityExtractor()
        self.number_tolerance = number_tolerance

    def _normalize_number_text(self, text: str) -> float:
        text = text.replace('$', '').replace(',', '').strip()
        multipliers = {
            'billion': 1e9, 'b': 1e9,
            'million': 1e6, 'm': 1e6,
            'trillion': 1e12,
            'thousand': 1e3, 'k': 1e3,
        }
        
        for suffix, mult in multipliers.items():
            if text.lower().endswith(suffix):
                num_part = text[:-(len(suffix))].strip()
                try:
                    return float(num_part) * mult
                except ValueError:
                    continue
        
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _find_closest_number(self, target: NumberFact, candidates: List[NumberFact]) -> Optional[NumberFact]:
        best_match = None
        best_diff = float('inf')
        
        for candidate in candidates:
            if candidate.normalized == 0 and target.normalized == 0:
                continue
            
            if target.unit and candidate.unit and target.unit != candidate.unit:
                continue
            
            if target.normalized != 0:
                relative_diff = abs(target.normalized - candidate.normalized) / abs(target.normalized)
            else:
                relative_diff = abs(candidate.normalized)
            
            context_similarity = SequenceMatcher(
                None,
                target.context.lower(),
                candidate.context.lower()
            ).ratio()
            
            weighted_diff = relative_diff - (context_similarity * 0.1)
            
            if weighted_diff < best_diff:
                best_diff = weighted_diff
                best_match = candidate
        
        return best_match

    def _check_number_consistency(
        self,
        source_numbers: List[NumberFact],
        summary_numbers: List[NumberFact]
    ) -> List[Dict]:
        issues = []
        
        for s_num in summary_numbers:
            closest = self._find_closest_number(s_num, source_numbers)
            
            if closest is None:
                if source_numbers:
                    issues.append({
                        'type': 'number_not_found',
                        'summary_value': s_num.value,
                        'summary_context': s_num.context,
                        'message': f'Number "{s_num.value}" in summary not found in source text',
                        'severity': 'warning'
                    })
                continue
            
            if closest.normalized != 0:
                relative_diff = abs(s_num.normalized - closest.normalized) / abs(closest.normalized)
            else:
                relative_diff = abs(s_num.normalized) if s_num.normalized != 0 else 0
            
            if relative_diff > self.number_tolerance:
                issues.append({
                    'type': 'number_mismatch',
                    'summary_value': s_num.value,
                    'source_value': closest.value,
                    'summary_context': s_num.context,
                    'source_context': closest.context,
                    'relative_diff': round(relative_diff, 4),
                    'message': f'Number mismatch: summary says "{s_num.value}" but source says "{closest.value}"',
                    'severity': 'error'
                })
        
        return issues

    def _check_entity_consistency(
        self,
        source_entities: List[EntityFact],
        summary_entities: List[EntityFact]
    ) -> List[Dict]:
        issues = []
        source_names = {e.name.lower() for e in source_entities}
        
        for s_ent in summary_entities:
            if s_ent.name.lower() not in source_names:
                similar = self._find_similar_entity(s_ent.name, source_entities)
                if similar:
                    issues.append({
                        'type': 'entity_mismatch',
                        'summary_entity': s_ent.name,
                        'suggested_entity': similar.name,
                        'entity_type': s_ent.entity_type,
                        'summary_context': s_ent.context,
                        'source_context': similar.context,
                        'message': f'Entity "{s_ent.name}" in summary may be incorrect, source has "{similar.name}"',
                        'severity': 'warning'
                    })
                else:
                    if s_ent.entity_type == 'DATE':
                        issues.append({
                            'type': 'entity_not_found',
                            'summary_entity': s_ent.name,
                            'entity_type': s_ent.entity_type,
                            'summary_context': s_ent.context,
                            'message': f'Date "{s_ent.name}" in summary not found in source text',
                            'severity': 'error'
                        })
        
        return issues

    def _find_similar_entity(self, name: str, candidates: List[EntityFact]) -> Optional[EntityFact]:
        best_match = None
        best_ratio = 0.0
        threshold = 0.6
        
        for candidate in candidates:
            ratio = SequenceMatcher(None, name.lower(), candidate.name.lower()).ratio()
            if ratio > threshold and ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate
        
        return best_match

    def _apply_corrections(self, summary: str, issues: List[Dict]) -> Tuple[str, List[Dict]]:
        corrected = summary
        corrections = []
        
        for issue in issues:
            if issue['type'] == 'number_mismatch':
                old_val = issue['summary_value']
                new_val = issue['source_value']
                
                pattern = re.compile(re.escape(old_val), re.IGNORECASE)
                if pattern.search(corrected):
                    corrected = pattern.sub(new_val, corrected, count=1)
                    corrections.append({
                        'type': 'number_correction',
                        'original': old_val,
                        'corrected': new_val,
                        'reason': issue['message']
                    })
            
            elif issue['type'] == 'entity_mismatch':
                old_ent = issue['summary_entity']
                new_ent = issue['suggested_entity']
                
                pattern = re.compile(re.escape(old_ent), re.IGNORECASE)
                if pattern.search(corrected):
                    corrected = pattern.sub(new_ent, corrected, count=1)
                    corrections.append({
                        'type': 'entity_correction',
                        'original': old_ent,
                        'corrected': new_ent,
                        'reason': issue['message']
                    })
        
        return corrected, corrections

    def check(self, source_text: str, summary_text: str, auto_correct: bool = True) -> FactCheckResult:
        source_numbers = self.number_extractor.extract(source_text)
        summary_numbers = self.number_extractor.extract(summary_text)
        
        source_entities = self.entity_extractor.extract(source_text)
        summary_entities = self.entity_extractor.extract(summary_text)
        
        number_issues = self._check_number_consistency(source_numbers, summary_numbers)
        entity_issues = self._check_entity_consistency(source_entities, summary_entities)
        
        all_issues = number_issues + entity_issues
        has_errors = any(issue['severity'] == 'error' for issue in all_issues)
        
        corrected_summary = summary_text
        corrections = []
        
        if auto_correct and all_issues:
            corrected_summary, corrections = self._apply_corrections(summary_text, all_issues)
        
        return FactCheckResult(
            is_consistent=not has_errors,
            original_text=source_text,
            summary_text=summary_text,
            number_issues=number_issues,
            entity_issues=entity_issues,
            corrected_summary=corrected_summary,
            corrections=corrections
        )
