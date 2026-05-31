import re
from typing import Dict, List

class FactorInterpreter:
    def __init__(self):
        self.operator_map = {
            'add': '加法',
            'sub': '减法',
            'mul': '乘法',
            '_protected_div': '除法(安全)',
            '_protected_sqrt': '绝对值开方',
            '_protected_log': '绝对值对数',
            'absolute': '绝对值',
            'sign': '符号函数',
            '_ts_mean': '移动平均(5日)',
            '_ts_std': '移动标准差(5日)',
            '_ts_max': '滚动最大值(5日)',
            '_ts_min': '滚动最小值(5日)',
            '_ts_delay': '滞后1期',
            '_ts_delta': '一阶差分',
            '_ts_rank': '滚动百分位排名(10日)',
        }
        
        self.argument_map = {
            'close': '收盘价',
            'open': '开盘价',
            'high': '最高价',
            'low': '最低价',
            'volume': '成交量',
        }
        
        self.pattern_map = {
            r'_ts_mean\(close\)': '收盘价5日均线',
            r'_ts_mean\(open\)': '开盘价5日均线',
            r'_ts_mean\(volume\)': '成交量5日均线',
            r'_ts_std\(close\)': '收盘价5日波动率',
            r'_ts_std\(volume\)': '成交量5日波动率',
            r'_ts_delay\(close\)': '前一日收盘价',
            r'_ts_delay\(open\)': '前一日开盘价',
            r'_ts_delta\(close\)': '收盘价日变化',
            r'_ts_delta\(volume\)': '成交量日变化',
            r'_ts_rank\(close\)': '收盘价10日百分位',
            r'_ts_rank\(volume\)': '成交量10日百分位',
            r'_protected_div\(close, _ts_mean\(close\)\)': '收盘价/5日均线(偏离度)',
            r'_protected_div\(volume, _ts_mean\(volume\)\)': '成交量/5日均量(量比)',
            r'_protected_div\(close, open\)': '收盘价/开盘价(日内涨幅)',
            r'sub\(close, _ts_delay\(close\)\)': '收盘价日涨跌',
            r'sub\(close, _ts_mean\(close\)\)': '收盘价偏离均线',
            r'mul\(_ts_delta\(close\), volume\)': '价格变化×成交量(量价配合)',
            r'_protected_sqrt\(mul\(close, volume\)\)': '√(价×量)(等权组合)',
            r'sub\(high, low\)': '日内振幅(最高-最低)',
        }
        
        self.complex_pattern_map = {
            r'_protected_div\(([^,]+), _ts_mean\(([^)]+)\)\)': r'\1 / \2均线(偏离度)',
            r'_protected_div\(([^,]+), _ts_std\(([^)]+)\)\)': r'\1 / \2波动率(标准化)',
            r'sub\(([^,]+), _ts_delay\(([^)]+)\)\)': r'\1 - 前1期\2(动量)',
            r'sub\(([^,]+), _ts_mean\(([^)]+)\)\)': r'\1 - \2均线(均值偏离)',
            r'mul\(_ts_delta\(([^)]+)\), ([^,]+)\)': r'\1变化 × \2(量价因子)',
            r'_protected_log\(mul\(([^,]+), ([^)]+)\)\)': r'ln(\1 × \2)(对数组合)',
        }
        
        self.factor_type_keywords = {
            '动量因子': ['_ts_delta', 'sub', '_ts_delay'],
            '均值回归因子': ['_ts_mean', '_protected_div', 'sub'],
            '波动率因子': ['_ts_std', '_protected_sqrt'],
            '量价因子': ['volume', 'mul'],
            '排名因子': ['_ts_rank', 'sign'],
            '趋势因子': ['_ts_mean', '_ts_max', '_ts_min'],
        }
    
    def _translate_token(self, token: str) -> str:
        token = token.strip()
        if token in self.argument_map:
            return self.argument_map[token]
        if token in self.operator_map:
            return self.operator_map[token]
        for key, value in self.operator_map.items():
            if key in token:
                return value
        for key, value in self.argument_map.items():
            if key in token:
                return value
        try:
            float(token)
            return f'常数({token})'
        except ValueError:
            pass
        return token
    
    def _match_patterns(self, expression: str) -> List[str]:
        meanings = []
        
        for pattern, meaning in self.pattern_map.items():
            if re.search(pattern, expression):
                meanings.append(meaning)
        
        for pattern, replacement in self.complex_pattern_map.items():
            match = re.search(pattern, expression)
            if match:
                groups = match.groups()
                translated = [self._translate_token(g) for g in groups]
                result = replacement
                for i, t in enumerate(translated):
                    result = result.replace(f'\\{i+1}', t)
                meanings.append(result)
        
        return meanings
    
    def _classify_factor_type(self, expression: str) -> List[str]:
        types = []
        type_scores = {}
        for ftype, keywords in self.factor_type_keywords.items():
            score = sum(1 for kw in keywords if kw in expression)
            if score > 0:
                type_scores[ftype] = score
        
        if type_scores:
            max_score = max(type_scores.values())
            types = [ft for ft, sc in type_scores.items() if sc == max_score]
        
        return types
    
    def _analyze_expression_depth(self, expression: str) -> Dict:
        max_depth = 0
        current_depth = 0
        for char in expression:
            if char == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ')':
                current_depth -= 1
        
        tokens = expression.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()
        n_operators = sum(1 for t in tokens if t in self.operator_map or 
                         any(k in t for k in self.operator_map))
        n_features = sum(1 for t in tokens if t in self.argument_map or 
                        any(k in t for k in self.argument_map))
        
        return {
            'nesting_depth': max_depth,
            'n_operators': n_operators,
            'n_features': n_features,
            'complexity': n_operators + n_features
        }
    
    def _build_readable_description(self, expression: str) -> str:
        desc = expression
        
        sorted_ops = sorted(self.operator_map.items(), key=lambda x: len(x[0]), reverse=True)
        for op, cn in sorted_ops:
            desc = desc.replace(op, cn)
        
        sorted_args = sorted(self.argument_map.items(), key=lambda x: len(x[0]), reverse=True)
        for arg, cn in sorted_args:
            desc = desc.replace(arg, cn)
        
        desc = re.sub(r'(\d+\.\d+)', lambda m: f'常数({m.group(1)})', desc)
        desc = re.sub(r'(\d+)', lambda m: f'常数({m.group(1)})', desc)
        
        return desc
    
    def interpret(self, expression: str) -> Dict:
        pattern_meanings = self._match_patterns(expression)
        factor_types = self._classify_factor_type(expression)
        structure = self._analyze_expression_depth(expression)
        readable = self._build_readable_description(expression)
        
        tokens = expression.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()
        feature_list = [t for t in tokens if t in self.argument_map]
        
        warnings = []
        if structure['complexity'] > 15:
            warnings.append('因子表达式过于复杂，可能存在过拟合风险')
        if structure['nesting_depth'] > 4:
            warnings.append('嵌套层次过深，因子可解释性降低')
        if len(set(feature_list)) == 1:
            warnings.append(f'仅使用单一特征({feature_list[0]})，因子多样性不足')
        
        return {
            'original_expression': expression,
            'readable_description': readable,
            'pattern_meanings': pattern_meanings,
            'factor_types': factor_types,
            'structure': structure,
            'features_used': list(set(feature_list)),
            'warnings': warnings
        }
    
    def format_interpretation(self, interpretation: Dict) -> str:
        lines = []
        lines.append(f"原始表达式: {interpretation['original_expression']}")
        lines.append(f"中文描述: {interpretation['readable_description']}")
        
        if interpretation['pattern_meanings']:
            lines.append(f"识别模式: {', '.join(interpretation['pattern_meanings'])}")
        
        if interpretation['factor_types']:
            lines.append(f"因子类型: {', '.join(interpretation['factor_types'])}")
        
        s = interpretation['structure']
        lines.append(f"复杂度: 嵌套{s['nesting_depth']}层, {s['n_operators']}个算子, {s['n_features']}个特征")
        lines.append(f"使用特征: {', '.join(interpretation['features_used'])}")
        
        if interpretation['warnings']:
            lines.append(f"⚠️ 风险提示: {'; '.join(interpretation['warnings'])}")
        
        return '\n'.join(lines)
