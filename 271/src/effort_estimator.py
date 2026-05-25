import os
import re
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ComplexityLevel(Enum):
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class FileEffortBreakdown:
    file: str
    lines_changed: int
    lines_added: int
    lines_deleted: int
    complexity_score: float
    estimated_minutes: float
    factors: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "lines_changed": self.lines_changed,
            "lines_added": self.lines_added,
            "lines_deleted": self.lines_deleted,
            "complexity_score": self.complexity_score,
            "estimated_minutes": self.estimated_minutes,
            "factors": self.factors
        }


@dataclass
class ReviewEffortEstimate:
    total_minutes: float
    total_hours: float
    human_readable: str
    complexity_level: str
    file_estimates: List[FileEffortBreakdown]
    summary: Dict[str, Any] = field(default_factory=dict)
    risk_factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_minutes": round(self.total_minutes, 2),
            "total_hours": round(self.total_hours, 2),
            "human_readable": self.human_readable,
            "complexity_level": self.complexity_level,
            "file_estimates": [f.to_dict() for f in self.file_estimates],
            "summary": self.summary,
            "risk_factors": self.risk_factors,
            "recommendations": self.recommendations
        }


class EffortEstimator:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        effort_config = self.config.get('effort_estimation', {})
        
        self.base_rate_per_line = effort_config.get('base_rate_per_line', 0.5)
        self.complexity_multipliers = effort_config.get('complexity_multipliers', {
            'trivial': 0.5,
            'simple': 1.0,
            'moderate': 2.0,
            'complex': 4.0,
            'very_complex': 8.0
        })
        
        self.setup_time = effort_config.get('setup_time', 10)
        self.context_switch_penalty = effort_config.get('context_switch_penalty', 5)
        self.max_review_session = effort_config.get('max_review_session', 120)
        
        self.language_factors = effort_config.get('language_factors', {
            '.py': 1.2,
            '.js': 1.0,
            '.ts': 1.1,
            '.tsx': 1.3,
            '.jsx': 1.2,
            '.java': 1.3,
            '.go': 1.0,
            '.rs': 1.4
        })
        
        self.critical_paths = effort_config.get('critical_paths', [])
        self.critical_path_multiplier = effort_config.get('critical_path_multiplier', 2.0)
        
    def estimate_from_changes(self, changed_files: List[str], analysis_results: Dict[str, Any] = None) -> ReviewEffortEstimate:
        file_estimates: List[FileEffortBreakdown] = []
        
        for file_path in changed_files:
            estimate = self._estimate_file(file_path, analysis_results)
            file_estimates.append(estimate)
        
        return self._aggregate_estimates(file_estimates, analysis_results)
    
    def estimate_from_directory(self, directory: str, changed_files: List[str] = None, 
                                  analysis_results: Dict[str, Any] = None) -> ReviewEffortEstimate:
        file_estimates: List[FileEffortBreakdown] = []
        
        if changed_files:
            return self.estimate_from_changes(changed_files, analysis_results)
        
        supported_extensions = ['.py', '.js', '.jsx', '.ts', '.tsx']
        
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in supported_extensions):
                    file_path = os.path.join(root, file)
                    estimate = self._estimate_file(file_path, analysis_results)
                    file_estimates.append(estimate)
        
        return self._aggregate_estimates(file_estimates, analysis_results)
    
    def _estimate_file(self, file_path: str, analysis_results: Dict[str, Any] = None) -> FileEffortBreakdown:
        lines_added, lines_deleted, total_lines = self._count_lines(file_path)
        lines_changed = lines_added + lines_deleted
        
        if lines_changed == 0:
            lines_changed = total_lines
            lines_added = total_lines
        
        complexity_score = self._calculate_file_complexity(file_path, analysis_results)
        language_factor = self._get_language_factor(file_path)
        critical_path_factor = self._get_critical_path_factor(file_path)
        
        base_minutes = lines_changed * self.base_rate_per_line
        adjusted_minutes = base_minutes * complexity_score * language_factor * critical_path_factor
        
        factors = {
            "complexity_score": complexity_score,
            "language_factor": language_factor,
            "critical_path_factor": critical_path_factor,
            "base_minutes": base_minutes
        }
        
        return FileEffortBreakdown(
            file=file_path,
            lines_changed=lines_changed,
            lines_added=lines_added,
            lines_deleted=lines_deleted,
            complexity_score=complexity_score,
            estimated_minutes=adjusted_minutes,
            factors=factors
        )
    
    def _count_lines(self, file_path: str) -> Tuple[int, int, int]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            return (0, 0, 0)
        
        total_lines = len(lines)
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif stripped.startswith('#') or stripped.startswith('//'):
                comment_lines += 1
            else:
                code_lines += 1
        
        return (code_lines, 0, total_lines)
    
    def _calculate_file_complexity(self, file_path: str, analysis_results: Dict[str, Any] = None) -> float:
        base_complexity = 1.0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return base_complexity
        
        factors = 1.0
        
        decision_count = self._count_decision_points(content, file_path)
        if decision_count > 50:
            factors *= 3.0
        elif decision_count > 20:
            factors *= 2.0
        elif decision_count > 10:
            factors *= 1.5
        
        function_count = self._count_functions(content, file_path)
        if function_count > 20:
            factors *= 2.0
        elif function_count > 10:
            factors *= 1.5
        
        nesting_depth = self._estimate_nesting_depth(content, file_path)
        if nesting_depth > 5:
            factors *= 1.5
        
        regex_complexity = self._assess_regex_complexity(content)
        factors *= regex_complexity
        
        if analysis_results:
            complexity_data = analysis_results.get('complexity', {})
            file_name = os.path.basename(file_path)
            for func in complexity_data.get('functions', []):
                if func.get('file', '').endswith(file_name):
                    if func.get('ccn', 0) > 20:
                        factors *= 1.5
                        break
        
        return factors
    
    def _count_decision_points(self, content: str, file_path: str) -> int:
        count = 0
        
        if file_path.endswith('.py'):
            patterns = [r'\bif\b', r'\bfor\b', r'\bwhile\b', r'\bexcept\b', r'\band\b', r'\bor\b', r'\?']
        else:
            patterns = [r'\bif\b', r'\bfor\b', r'\bwhile\b', r'\bcatch\b', r'\&\&', r'\|\|', r'\?']
        
        for pattern in patterns:
            count += len(re.findall(pattern, content))
        
        return count
    
    def _count_functions(self, content: str, file_path: str) -> int:
        if file_path.endswith('.py'):
            pattern = r'\bdef\s+\w+'
        else:
            pattern = r'\bfunction\s+\w+|const\s+\w+\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>'
        
        return len(re.findall(pattern, content))
    
    def _estimate_nesting_depth(self, content: str, file_path: str) -> int:
        max_depth = 0
        current_depth = 0
        
        lines = content.split('\n')
        for line in lines:
            indent = len(line) - len(line.lstrip())
            depth = indent // 4 if file_path.endswith('.py') else indent // 2
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _assess_regex_complexity(self, content: str) -> float:
        factor = 1.0
        
        regex_patterns = re.findall(r're\.compile|r["\'].*["\']|new\s+RegExp', content)
        if len(regex_patterns) > 5:
            factor *= 1.3
        
        return factor
    
    def _get_language_factor(self, file_path: str) -> float:
        for ext, factor in self.language_factors.items():
            if file_path.endswith(ext):
                return factor
        return 1.0
    
    def _get_critical_path_factor(self, file_path: str) -> float:
        for path_pattern in self.critical_paths:
            if path_pattern in file_path:
                return self.critical_path_multiplier
        return 1.0
    
    def _aggregate_estimates(self, file_estimates: List[FileEffortBreakdown], 
                            analysis_results: Dict[str, Any] = None) -> ReviewEffortEstimate:
        total_minutes = sum(f.estimated_minutes for f in file_estimates)
        total_minutes += self.setup_time
        
        if len(file_estimates) > 5:
            total_minutes += (len(file_estimates) - 5) * self.context_switch_penalty
        
        total_hours = total_minutes / 60
        
        complexity_level = self._determine_complexity_level(total_minutes, len(file_estimates))
        
        summary = {
            "total_files": len(file_estimates),
            "total_lines_changed": sum(f.lines_changed for f in file_estimates),
            "avg_complexity_score": sum(f.complexity_score for f in file_estimates) / len(file_estimates) if file_estimates else 1.0,
            "setup_time_minutes": self.setup_time,
            "context_switch_penalty_minutes": max(0, (len(file_estimates) - 5) * self.context_switch_penalty
        }
        
        risk_factors = self._identify_risk_factors(file_estimates, analysis_results)
        recommendations = self._generate_recommendations(file_estimates, total_minutes, risk_factors)
        
        return ReviewEffortEstimate(
            total_minutes=total_minutes,
            total_hours=total_hours,
            human_readable=self._format_duration(total_minutes),
            complexity_level=complexity_level.value,
            file_estimates=sorted(file_estimates, key=lambda x: x.estimated_minutes, reverse=True),
            summary=summary,
            risk_factors=risk_factors,
            recommendations=recommendations
        )
    
    def _determine_complexity_level(self, total_minutes: float, file_count: int) -> ComplexityLevel:
        if total_minutes < 15 and file_count <= 2:
            return ComplexityLevel.TRIVIAL
        elif total_minutes < 30 and file_count <= 5:
            return ComplexityLevel.SIMPLE
        elif total_minutes < 60 and file_count <= 10:
            return ComplexityLevel.MODERATE
        elif total_minutes < 120:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.VERY_COMPLEX
    
    def _identify_risk_factors(self, file_estimates: List[FileEffortBreakdown], 
                                  analysis_results: Dict[str, Any] = None) -> List[str]:
        risks = []
        
        high_complexity_files = [f for f in file_estimates if f.complexity_score >= 3.0]
        if len(high_complexity_files) > 0:
            risks.append(f"检测到 {len(high_complexity_files)} 个高复杂度文件需要重点审查")
        
        large_files = [f for f in file_estimates if f.lines_changed > 200]
        if large_files:
            risks.append(f"存在 {len(large_files)} 个大变更文件 (>200行)")
        
        if len(file_estimates) > 10:
            risks.append("变更文件数量较多，建议分批次审查")
        
        if analysis_results:
            impact_risk = analysis_results.get('impact_analysis', {}).get('risk_assessment', {})
            if impact_risk.get('level') == 'critical':
                risks.append("影响分析显示变更影响范围广，风险较高")
            
            duplication = analysis_results.get('duplication', {})
            if duplication.get('similar_blocks', 0) > 5:
                risks.append("检测到较多重复代码块")
            
            ai_review = analysis_results.get('ai_review', {}).get('summary', {})
            if ai_review.get('by_severity', {}).get('critical', 0) > 0:
                risks.append("AI审查发现严重问题")
        
        return risks
    
    def _generate_recommendations(self, file_estimates: List[FileEffortBreakdown], 
                                    total_minutes: float, risk_factors: List[str]) -> List[str]:
        recommendations = []
        
        if total_minutes > self.max_review_session:
            sessions = math.ceil(total_minutes / self.max_review_session)
            recommendations.append(f"建议分成 {sessions} 次审查会话，每次约 {self.max_review_session} 分钟")
        
        high_effort_files = sorted(file_estimates, key=lambda x: x.estimated_minutes, reverse=True)[:3]
        if high_effort_files:
            file_names = [os.path.basename(f.file) for f in high_effort_files]
            recommendations.append(f"重点关注文件: {', '.join(file_names)}")
        
        if len(file_estimates) > 5:
            recommendations.append("建议按模块分组审查，减少上下文切换开销")
        
        if not risk_factors:
            recommendations.append("本次变更风险较低，可进行标准审查流程")
        
        return recommendations
    
    def _format_duration(self, minutes: float) -> str:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        
        if hours > 0:
            if mins > 0:
                return f"{hours} 小时 {mins} 分钟"
            return f"{hours} 小时"
        return f"{mins} 分钟"
    
    def get_quick_estimate(self, lines_of_code: int, file_count: int = 1, 
                            complexity: str = 'moderate') -> Dict[str, Any]:
        multipliers = {
            'trivial': 0.5,
            'simple': 1.0,
            'moderate': 2.0,
            'complex': 4.0,
            'very_complex': 8.0
        }
        
        base_minutes = lines_of_code * self.base_rate_per_line
        adjusted_minutes = base_minutes * multipliers.get(complexity, 2.0)
        
        if file_count > 5:
            adjusted_minutes += (file_count - 5) * self.context_switch_penalty
        
        adjusted_minutes += self.setup_time
        
        return {
            "estimated_minutes": round(adjusted_minutes, 2),
            "estimated_hours": round(adjusted_minutes / 60, 2),
            "human_readable": self._format_duration(adjusted_minutes)
        }
