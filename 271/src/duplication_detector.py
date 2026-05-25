import os
import re
import hashlib
import ast
from typing import Dict, List, Any, Tuple, Optional


class DuplicationDetector:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        dup_config = self.config.get('duplication', {})
        
        self.detection_levels = dup_config.get('detection_levels', ['function', 'statement'])
        self.min_similarity = dup_config.get('min_similarity', 85)
        
        function_config = dup_config.get('function_level', {})
        self.function_min_lines = function_config.get('min_lines', 5)
        self.function_min_tokens = function_config.get('min_tokens', 30)
        
        statement_config = dup_config.get('statement_level', {})
        self.statement_min_lines = statement_config.get('min_lines', 3)
        self.statement_min_tokens = statement_config.get('min_tokens', 20)
        
        self.ignore_comments = dup_config.get('ignore_comments', True)
        self.ignore_whitespace = dup_config.get('ignore_whitespace', True)
        self.ignore_string_values = dup_config.get('ignore_string_values', True)
        self.ignore_numeric_values = dup_config.get('ignore_numeric_values', True)
        self.ignore_variable_names = dup_config.get('ignore_variable_names', False)
        
        self.cross_file_detection = dup_config.get('cross_file_detection', True)
        
    def _normalize_code(self, code: str) -> str:
        normalized = code
        
        if self.ignore_comments:
            normalized = re.sub(r'//.*$', '', normalized, flags=re.MULTILINE)
            normalized = re.sub(r'/\*.*?\*/', '', normalized, flags=re.DOTALL)
            normalized = re.sub(r'#.*$', '', normalized, flags=re.MULTILINE)
        
        if self.ignore_string_values:
            normalized = re.sub(r'"[^"]*"', 'STRING', normalized)
            normalized = re.sub(r"'[^']*'", 'STRING', normalized)
        
        if self.ignore_numeric_values:
            normalized = re.sub(r'\b\d+\.?\d*\b', 'NUMBER', normalized)
        
        if self.ignore_whitespace:
            normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()
    
    def _tokenize(self, code: str) -> List[str]:
        tokens = re.findall(r'[a-zA-Z_]\w*|\d+\.?\d*|[+\-*/%=<>!&|^~]+|[(){}\[\];,.]', code)
        return tokens
    
    def _extract_functions_python(self, content: str) -> List[Dict]:
        functions = []
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_source = ast.get_source_segment(content, node)
                    if func_source:
                        functions.append({
                            'name': node.name,
                            'start_line': node.lineno,
                            'end_line': node.end_line or node.lineno,
                            'source': func_source,
                            'type': 'function'
                        })
        except Exception:
            pass
        return functions
    
    def _extract_functions_javascript(self, content: str) -> List[Dict]:
        functions = []
        lines = content.split('\n')
        
        func_patterns = [
            (r'function\s+(\w+)\s*\([^)]*\)\s*\{', 'function'),
            (r'const\s+(\w+)\s*=\s*(?:async\s+)?function\s*\([^)]*\)\s*\{', 'function'),
            (r'const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>\s*\{', 'arrow_function'),
            (r'(\w+)\s*:\s*(?:async\s+)?function\s*\([^)]*\)\s*\{', 'method')
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, func_type in func_patterns:
                match = re.search(pattern, line)
                if match:
                    func_name = match.group(1)
                    end_line = self._find_closing_brace(lines, i - 1)
                    func_source = '\n'.join(lines[i-1:end_line])
                    functions.append({
                        'name': func_name,
                        'start_line': i,
                        'end_line': end_line + 1,
                        'source': func_source,
                        'type': func_type
                    })
                    break
        
        return functions
    
    def _find_closing_brace(self, lines: List[str], start_idx: int) -> int:
        brace_count = 0
        in_string = False
        string_char = ''
        
        for i in range(start_idx, len(lines)):
            line = lines[i]
            for char in line:
                if char in '"\'':
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                elif not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return i
        return len(lines) - 1
    
    def _extract_statement_blocks(self, content: str, file_ext: str) -> List[Dict]:
        blocks = []
        lines = content.split('\n')
        
        current_block = []
        current_start = 0
        brace_depth = 0
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if not stripped or stripped.startswith(('//', '#', '/*', '*')):
                if current_block:
                    if len(current_block) >= self.statement_min_lines:
                        block_source = '\n'.join(current_block)
                        blocks.append({
                            'start_line': current_start,
                            'end_line': i - 1,
                            'source': block_source,
                            'type': 'statement',
                            'line_count': len(current_block)
                        })
                    current_block = []
                continue
            
            open_braces = line.count('{')
            close_braces = line.count('}')
            prev_depth = brace_depth
            brace_depth += open_braces - close_braces
            
            if brace_depth == 0 and prev_depth > 0:
                current_block.append(line)
                if len(current_block) >= self.statement_min_lines:
                    block_source = '\n'.join(current_block)
                    blocks.append({
                        'start_line': current_start,
                        'end_line': i,
                        'source': block_source,
                        'type': 'statement',
                        'line_count': len(current_block)
                    })
                current_block = []
            else:
                if not current_block:
                    current_start = i
                current_block.append(line)
        
        if current_block and len(current_block) >= self.statement_min_lines:
            block_source = '\n'.join(current_block)
            blocks.append({
                'start_line': current_start,
                'end_line': len(lines),
                'source': block_source,
                'type': 'statement',
                'line_count': len(current_block)
            })
        
        return blocks
    
    def _calculate_similarity(self, code1: str, code2: str) -> float:
        norm1 = self._normalize_code(code1)
        norm2 = self._normalize_code(code2)
        
        if norm1 == norm2:
            return 100.0
        
        tokens1 = self._tokenize(norm1)
        tokens2 = self._tokenize(norm2)
        
        if len(tokens1) == 0 or len(tokens2) == 0:
            return 0.0
        
        hash1 = hashlib.md5(' '.join(tokens1).encode()).hexdigest()
        hash2 = hashlib.md5(' '.join(tokens2).encode()).hexdigest()
        
        if hash1 == hash2:
            return 95.0
        
        set1 = set(tokens1)
        set2 = set(tokens2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        jaccard = intersection / union
        
        min_len = min(len(tokens1), len(tokens2))
        matches = 0
        for i in range(min_len):
            if tokens1[i] == tokens2[i]:
                matches += 1
        
        sequence_sim = matches / min_len
        
        return (jaccard * 0.6 + sequence_sim * 0.4) * 100
    
    def detect_file_duplication(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"duplicates": [], "summary": {"count": 0, "by_level": {}}}
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return {"duplicates": [], "summary": {"count": 0, "by_level": {}}}
        
        file_ext = os.path.splitext(file_path)[1]
        
        all_duplicates = []
        
        if 'function' in self.detection_levels:
            func_duplicates = self._detect_function_level_duplication(content, file_path, file_ext)
            all_duplicates.extend(func_duplicates)
        
        if 'statement' in self.detection_levels:
            stmt_duplicates = self._detect_statement_level_duplication(content, file_path, file_ext)
            all_duplicates.extend(stmt_duplicates)
        
        summary = self._summarize_duplicates(all_duplicates)
        
        return {
            'duplicates': all_duplicates,
            'summary': summary
        }
    
    def _detect_function_level_duplication(self, content: str, file_path: str, file_ext: str) -> List[Dict]:
        duplicates = []
        
        if file_ext == '.py':
            functions = self._extract_functions_python(content)
        elif file_ext in ['.js', '.jsx', '.ts', '.tsx']:
            functions = self._extract_functions_javascript(content)
        else:
            return duplicates
        
        for i, func1 in enumerate(functions):
            tokens1 = self._tokenize(self._normalize_code(func1['source']))
            if len(tokens1) < self.function_min_tokens:
                continue
                
            for j, func2 in enumerate(functions):
                if i >= j:
                    continue
                
                tokens2 = self._tokenize(self._normalize_code(func2['source']))
                if len(tokens2) < self.function_min_tokens:
                    continue
                
                similarity = self._calculate_similarity(func1['source'], func2['source'])
                
                if similarity >= self.min_similarity:
                    duplicates.append({
                        'type': 'internal',
                        'level': 'function',
                        'file': file_path,
                        'original': {
                            'name': func1['name'],
                            'start_line': func1['start_line'],
                            'end_line': func1['end_line'],
                            'line_count': func1['end_line'] - func1['start_line'] + 1
                        },
                        'duplicate': {
                            'name': func2['name'],
                            'start_line': func2['start_line'],
                            'end_line': func2['end_line'],
                            'line_count': func2['end_line'] - func2['start_line'] + 1
                        },
                        'similarity': round(similarity, 2),
                        'token_count': len(tokens1)
                    })
        
        return duplicates
    
    def _detect_statement_level_duplication(self, content: str, file_path: str, file_ext: str) -> List[Dict]:
        duplicates = []
        
        blocks = self._extract_statement_blocks(content, file_ext)
        block_hashes = {}
        
        for block in blocks:
            tokens = self._tokenize(self._normalize_code(block['source']))
            if len(tokens) < self.statement_min_tokens:
                continue
            
            block_hash = hashlib.md5(self._normalize_code(block['source']).encode()).hexdigest()
            
            if block_hash in block_hashes:
                original = block_hashes[block_hash]
                similarity = self._calculate_similarity(original['source'], block['source'])
                
                if similarity >= self.min_similarity:
                    duplicates.append({
                        'type': 'internal',
                        'level': 'statement',
                        'file': file_path,
                        'original': {
                            'start_line': original['start_line'],
                            'end_line': original['end_line'],
                            'line_count': original['line_count']
                        },
                        'duplicate': {
                            'start_line': block['start_line'],
                            'end_line': block['end_line'],
                            'line_count': block['line_count']
                        },
                        'similarity': round(similarity, 2),
                        'token_count': len(tokens)
                    })
            else:
                block_hashes[block_hash] = block
        
        return duplicates
    
    def detect_directory_duplication(self, directory: str) -> Dict[str, Any]:
        all_duplicates = []
        file_fingerprints = {'function': {}, 'statement': {}}
        
        supported_extensions = ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.cs']
        
        for root, _, files in os.walk(directory):
            for file in files:
                if not any(file.endswith(ext) for ext in supported_extensions):
                    continue
                    
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1]
                
                file_result = self.detect_file_duplication(file_path)
                all_duplicates.extend(file_result['duplicates'])
                
                if self.cross_file_detection:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        if 'function' in self.detection_levels:
                            if file_ext == '.py':
                                functions = self._extract_functions_python(content)
                            elif file_ext in ['.js', '.jsx', '.ts', '.tsx']:
                                functions = self._extract_functions_javascript(content)
                            else:
                                functions = []
                            
                            for func in functions:
                                tokens = self._tokenize(self._normalize_code(func['source']))
                                if len(tokens) >= self.function_min_tokens:
                                    func_hash = hashlib.md5(self._normalize_code(func['source']).encode()).hexdigest()
                                    fingerprint = (func_hash, len(tokens))
                                    
                                    if fingerprint in file_fingerprints['function']:
                                        orig_file, orig_func = file_fingerprints['function'][fingerprint]
                                        if orig_file != file_path:
                                            similarity = self._calculate_similarity(orig_func['source'], func['source'])
                                            if similarity >= self.min_similarity:
                                                all_duplicates.append({
                                                    'type': 'cross_file',
                                                    'level': 'function',
                                                    'original_file': orig_file,
                                                    'duplicate_file': file_path,
                                                    'original': {
                                                        'name': orig_func['name'],
                                                        'start_line': orig_func['start_line'],
                                                        'end_line': orig_func['end_line']
                                                    },
                                                    'duplicate': {
                                                        'name': func['name'],
                                                        'start_line': func['start_line'],
                                                        'end_line': func['end_line']
                                                    },
                                                    'similarity': round(similarity, 2)
                                                })
                                    else:
                                        file_fingerprints['function'][fingerprint] = (file_path, func)
                        
                        if 'statement' in self.detection_levels:
                            blocks = self._extract_statement_blocks(content, file_ext)
                            for block in blocks:
                                tokens = self._tokenize(self._normalize_code(block['source']))
                                if len(tokens) >= self.statement_min_tokens:
                                    block_hash = hashlib.md5(self._normalize_code(block['source']).encode()).hexdigest()
                                    fingerprint = (block_hash, len(tokens))
                                    
                                    if fingerprint in file_fingerprints['statement']:
                                        orig_file, orig_block = file_fingerprints['statement'][fingerprint]
                                        if orig_file != file_path:
                                            similarity = self._calculate_similarity(orig_block['source'], block['source'])
                                            if similarity >= self.min_similarity:
                                                all_duplicates.append({
                                                    'type': 'cross_file',
                                                    'level': 'statement',
                                                    'original_file': orig_file,
                                                    'duplicate_file': file_path,
                                                    'original': {
                                                        'start_line': orig_block['start_line'],
                                                        'end_line': orig_block['end_line']
                                                    },
                                                    'duplicate': {
                                                        'start_line': block['start_line'],
                                                        'end_line': block['end_line']
                                                    },
                                                    'similarity': round(similarity, 2)
                                                })
                                    else:
                                        file_fingerprints['statement'][fingerprint] = (file_path, block)
                    except Exception:
                        pass
        
        summary = self._summarize_duplicates(all_duplicates)
        
        return {
            'duplicates': all_duplicates,
            'summary': summary
        }
    
    def _summarize_duplicates(self, duplicates: List[Dict]) -> Dict[str, Any]:
        by_level = {'function': 0, 'statement': 0}
        by_type = {'internal': 0, 'cross_file': 0}
        similarity_ranges = {
            'exact': 0,
            '90-99': 0,
            '80-89': 0,
            '70-79': 0,
            'below_70': 0
        }
        
        for dup in duplicates:
            level = dup.get('level', 'statement')
            if level in by_level:
                by_level[level] += 1
            
            dup_type = dup.get('type', 'internal')
            if dup_type in by_type:
                by_type[dup_type] += 1
            
            similarity = dup.get('similarity', 0)
            if similarity >= 100:
                similarity_ranges['exact'] += 1
            elif similarity >= 90:
                similarity_ranges['90-99'] += 1
            elif similarity >= 80:
                similarity_ranges['80-89'] += 1
            elif similarity >= 70:
                similarity_ranges['70-79'] += 1
            else:
                similarity_ranges['below_70'] += 1
        
        return {
            'total_duplicates': len(duplicates),
            'by_level': by_level,
            'by_type': by_type,
            'similarity_distribution': similarity_ranges,
            'risk_level': self._calculate_risk_level(len(duplicates), by_level)
        }
    
    def _calculate_risk_level(self, total_count: int, by_level: Dict[str, int]) -> str:
        function_count = by_level.get('function', 0)
        statement_count = by_level.get('statement', 0)
        
        weighted_score = function_count * 3 + statement_count * 1
        
        if weighted_score > 30:
            return "critical"
        elif weighted_score > 15:
            return "high"
        elif weighted_score > 5:
            return "medium"
        elif weighted_score > 0:
            return "low"
        else:
            return "none"
