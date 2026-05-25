import os
import re
import importlib.util
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field


@dataclass
class CustomRuleResult:
    rule_name: str
    valid: bool
    score: float
    max_score: float
    issues: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CustomRule:
    name: str
    weight: int
    check_function: Callable
    config: Dict[str, Any] = field(default_factory=dict)


class CustomRuleLoader:
    def __init__(self, config: Any):
        self.config = config
        self.enabled = config.get("custom_rules.enabled", False)
        self.rules_dir = config.get("custom_rules.rules_dir", ".commit-rules")
        self.rules: List[CustomRule] = []

        if self.enabled:
            self._load_rules()

    def _load_rules(self):
        if not os.path.exists(self.rules_dir):
            return

        for filename in os.listdir(self.rules_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                self._load_rule_file(os.path.join(self.rules_dir, filename))

        yaml_files = [f for f in os.listdir(self.rules_dir) if f.endswith((".yaml", ".yml"))]
        for filename in yaml_files:
            self._load_yaml_rule(os.path.join(self.rules_dir, filename))

    def _load_rule_file(self, filepath: str):
        try:
            spec = importlib.util.spec_from_file_location(
                f"custom_rule_{os.path.basename(filepath)}", filepath
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, "check") and callable(module.check):
                    rule_name = getattr(module, "name", os.path.splitext(os.path.basename(filepath))[0])
                    weight = getattr(module, "weight", 10)
                    rule_config = getattr(module, "config", {})

                    self.rules.append(CustomRule(
                        name=rule_name,
                        weight=weight,
                        check_function=module.check,
                        config=rule_config
                    ))
        except Exception as e:
            print(f"Warning: Failed to load custom rule from {filepath}: {e}")

    def _load_yaml_rule(self, filepath: str):
        try:
            import yaml
            with open(filepath, "r", encoding="utf-8") as f:
                rule_def = yaml.safe_load(f)

            if not rule_def or "name" not in rule_def:
                return

            rule_name = rule_def["name"]
            weight = rule_def.get("weight", 10)
            check_type = rule_def.get("type", "message")
            pattern = rule_def.get("pattern")
            conditions = rule_def.get("conditions", {})

            def create_check_function(
                check_type: str,
                pattern: Optional[str],
                conditions: Dict[str, Any]
            ) -> Callable:
                compiled_pattern = re.compile(pattern) if pattern else None

                def check(commit_info: Dict[str, Any]) -> CustomRuleResult:
                    issues: List[str] = []
                    score = weight
                    max_score = weight
                    details: Dict[str, Any] = {}

                    if check_type == "message" and compiled_pattern:
                        message = commit_info.get("message", "")
                        if not compiled_pattern.search(message):
                            issues.append(rule_def.get("error_message", f"规则 '{rule_name}' 未通过"))
                            score = 0

                    elif check_type == "file_count":
                        min_count = conditions.get("min", 0)
                        max_count = conditions.get("max", 1000)
                        file_count = len(commit_info.get("changed_files", []))
                        details["file_count"] = file_count
                        if file_count < min_count or file_count > max_count:
                            issues.append(
                                f"文件数量 {file_count} 超出范围 [{min_count}, {max_count}]"
                            )
                            score = 0

                    elif check_type == "line_count":
                        min_lines = conditions.get("min", 0)
                        max_lines = conditions.get("max", 10000)
                        total_lines = commit_info.get("total_lines_changed", 0)
                        details["total_lines"] = total_lines
                        if total_lines < min_lines or total_lines > max_lines:
                            issues.append(
                                f"变更行数 {total_lines} 超出范围 [{min_lines}, {max_lines}]"
                            )
                            score = 0

                    elif check_type == "file_pattern":
                        changed_files = commit_info.get("changed_files", [])
                        forbidden = conditions.get("forbidden_patterns", [])
                        allowed = conditions.get("allowed_patterns", [])

                        if forbidden:
                            for f_pattern in forbidden:
                                f_regex = re.compile(f_pattern)
                                for f in changed_files:
                                    if f_regex.search(f):
                                        issues.append(f"禁止修改文件: {f} (匹配模式: {f_pattern})")
                                        score = 0
                                        break

                    valid = score >= max_score * 0.6
                    return CustomRuleResult(
                        rule_name=rule_name,
                        valid=valid,
                        score=score,
                        max_score=max_score,
                        issues=issues,
                        details=details
                    )

                return check

            check_func = create_check_function(check_type, pattern, conditions)
            self.rules.append(CustomRule(
                name=rule_name,
                weight=weight,
                check_function=check_func,
                config=rule_def
            ))
        except Exception as e:
            print(f"Warning: Failed to load YAML rule from {filepath}: {e}")

    def run_rules(
        self,
        commit_message: str,
        changed_files: List[str],
        file_stats: List[Any],
        commit_info: Dict[str, Any]
    ) -> List[CustomRuleResult]:
        if not self.enabled or not self.rules:
            return []

        results: List[CustomRuleResult] = []

        commit_data = {
            **commit_info,
            "message": commit_message,
            "changed_files": changed_files,
            "file_stats": file_stats,
            "total_lines_changed": sum(
                getattr(s, "insertions", 0) + getattr(s, "deletions", 0) for s in file_stats
            ),
        }

        for rule in self.rules:
            try:
                result = rule.check_function(commit_data)
                if isinstance(result, CustomRuleResult):
                    results.append(result)
                elif isinstance(result, tuple) and len(result) >= 2:
                    valid, score = result[0], result[1]
                    issues = result[2] if len(result) > 2 else []
                    details = result[3] if len(result) > 3 else {}
                    results.append(CustomRuleResult(
                        rule_name=rule.name,
                        valid=valid,
                        score=score,
                        max_score=rule.weight,
                        issues=issues,
                        details=details
                    ))
            except Exception as e:
                results.append(CustomRuleResult(
                    rule_name=rule.name,
                    valid=False,
                    score=0,
                    max_score=rule.weight,
                    issues=[f"规则执行出错: {str(e)}"],
                    details={"error": str(e)}
                ))

        return results
