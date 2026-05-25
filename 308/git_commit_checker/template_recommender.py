import os
import re
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class CommitRecommendation:
    template: str
    type: str
    scopes: List[str]
    subject_suggestion: str
    body_suggestion: str
    confidence: float
    reason: str


@dataclass
class TemplateRecommendationResult:
    valid: bool
    score: float
    max_score: float
    issues: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[CommitRecommendation] = field(default_factory=list)


@dataclass
class FileContentHint:
    path: str
    keywords: List[str]
    change_type: str
    module: str


class TemplateRecommender:
    SRC_DIRS = {"src", "lib", "main", "app", "source", "sources"}

    TYPE_KEYWORDS: Dict[str, List[str]] = {
        "feat": [
            "add", "new", "create", "implement", "feature", "introduce",
            "support", "enable", "新增", "添加", "实现", "功能", "支持", "引入"
        ],
        "fix": [
            "fix", "bug", "error", "issue", "correct", "repair", "resolve",
            "修复", "问题", "错误", "解决", "纠正", "修补"
        ],
        "refactor": [
            "refactor", "restructure", "reorganize", "clean", "simplify",
            "rename", "move", "重构", "整理", "优化", "重命名", "移动", "简化"
        ],
        "docs": [
            "doc", "document", "readme", "comment", "注释", "文档", "说明"
        ],
        "style": [
            "style", "format", "lint", "indent", "whitespace",
            "格式", "样式", "缩进", "空格", "格式化"
        ],
        "perf": [
            "perf", "performance", "optimize", "speed", "improve",
            "性能", "优化", "加速", "提升", "改进"
        ],
        "test": [
            "test", "spec", "coverage", "assert", "测试", "用例", "覆盖率"
        ],
        "build": [
            "build", "compile", "package", "depend", "构建", "编译", "打包", "依赖"
        ],
        "ci": [
            "ci", "pipeline", "workflow", "action", "jenkins", "github action",
            "持续集成", "流水线", "工作流"
        ],
        "chore": [
            "chore", "upgrade", "update", "bump", "version",
            "升级", "更新", "版本", "杂项", "例行"
        ],
        "revert": [
            "revert", "rollback", "undo", "回滚", "撤销"
        ]
    }

    SCOPE_PATTERNS = [
        re.compile(r"^src/([^/]+)/"),
        re.compile(r"^packages/([^/]+)/"),
        re.compile(r"^([^/]+)/"),
        re.compile(r"^lib/([^/]+)/"),
        re.compile(r"^app/([^/]+)/"),
    ]

    BREAKING_KEYWORDS = [
        "breaking", "incompatible", "deprecate", "remove", "delete",
        "不兼容", "废弃", "删除", "移除"
    ]

    def __init__(self, config: Any):
        self.config = config
        self.enabled = config.get("template_recommendation.enabled", True)
        self.weight = config.get("template_recommendation.weight", 10)
        self.custom_templates = config.get("template_recommendation.custom_templates", {})
        self.analyze_content = config.get("template_recommendation.analyze_content", True)
        self.max_recommendations = config.get("template_recommendation.max_recommendations", 3)

    def recommend(
        self,
        changed_files: List[str],
        file_stats: Optional[List[Any]] = None,
        existing_message: Optional[str] = None,
        file_contents: Optional[Dict[str, str]] = None
    ) -> TemplateRecommendationResult:
        if not self.enabled:
            return TemplateRecommendationResult(
                valid=True,
                score=self.weight,
                max_score=self.weight,
                issues=[],
                details={"skipped": True}
            )

        issues: List[str] = []
        score = self.weight
        max_score = self.weight
        details: Dict[str, Any] = {}

        file_hints = self._analyze_files(changed_files, file_contents)
        details["file_hints"] = [h.__dict__ for h in file_hints]

        dominant_module = self._find_dominant_module(file_hints)
        details["dominant_module"] = dominant_module

        type_scores = self._calculate_type_scores(file_hints, file_stats)
        details["type_scores"] = type_scores

        has_breaking = self._detect_breaking_changes(
            file_hints, file_stats, file_contents
        )
        details["has_breaking_changes"] = has_breaking

        recommendations = self._generate_recommendations(
            file_hints, type_scores, dominant_module, has_breaking
        )
        details["recommendation_count"] = len(recommendations)

        if existing_message is not None:
            message_quality = self._evaluate_existing_message(
                existing_message, recommendations
            )
            details["message_quality"] = message_quality

            if message_quality["needs_improvement"]:
                issues.extend(message_quality["suggestions"])
                score *= 0.9

        if not recommendations:
            issues.append("未能生成推荐模板，请手动填写提交信息。")
            score *= 0.7

        score = round(score, 2)
        valid = score >= (max_score * 0.6)

        return TemplateRecommendationResult(
            valid=valid,
            score=score,
            max_score=max_score,
            issues=issues,
            details=details,
            recommendations=recommendations
        )

    def _analyze_files(
        self,
        changed_files: List[str],
        file_contents: Optional[Dict[str, str]]
    ) -> List[FileContentHint]:
        hints: List[FileContentHint] = []

        chore_files = {
            "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
            "requirements.txt", "pyproject.toml", "Pipfile", "poetry.lock",
            "Cargo.toml", "Cargo.lock", "go.mod", "go.sum",
            "Gemfile", "Gemfile.lock", "composer.json", "composer.lock",
            "build.gradle", "pom.xml", "Makefile", "CMakeLists.txt",
        }

        for file_path in changed_files:
            normalized = file_path.replace("\\", "/")
            keywords: List[str] = []
            change_type = "unknown"
            module = self._extract_module(normalized)

            filename = os.path.basename(normalized).lower()
            path_parts = normalized.split("/")

            if normalized in chore_files or filename in chore_files:
                change_type = "chore"
                keywords.append("依赖")
            elif any(part.lower() in {"tests", "test", "__tests__", "spec", "specs"} for part in path_parts):
                change_type = "test"
                keywords.append("测试")
            elif filename.endswith((".test.", "_test.", ".spec.", "_spec.")) or \
                 filename.startswith(("test_", "spec_")):
                change_type = "test"
                keywords.append("测试")
            elif filename.endswith((".md", ".rst", ".txt")):
                change_type = "docs"
                keywords.append("文档")
            elif "readme" in filename or "changelog" in filename:
                change_type = "docs"
                keywords.append("文档")
            elif filename.startswith("dockerfile") or "docker-compose" in filename:
                change_type = "build"
                keywords.append("构建")
            elif ".github/workflows" in normalized or ".gitlab-ci" in normalized:
                change_type = "ci"
                keywords.append("CI")
            elif normalized.endswith((".yml", ".yaml")) and ("workflow" in normalized or "pipeline" in normalized or "ci" in normalized):
                change_type = "ci"
                keywords.append("CI")

            if self.analyze_content and file_contents and file_path in file_contents:
                content_keywords = self._extract_keywords_from_content(
                    file_contents[file_path]
                )
                keywords.extend(content_keywords)

                if content_keywords:
                    content_type = self._detect_type_from_keywords(content_keywords)
                    if content_type and change_type == "unknown":
                        change_type = content_type

            hints.append(FileContentHint(
                path=normalized,
                keywords=list(set(keywords)),
                change_type=change_type,
                module=module or ""
            ))

        return hints

    def _extract_module(self, file_path: str) -> Optional[str]:
        normalized = file_path.replace("\\", "/")
        path_parts = normalized.split("/")

        for i, part in enumerate(path_parts):
            if part.lower() in self.SRC_DIRS and i < len(path_parts) - 1:
                next_part = path_parts[i + 1]
                if "." not in next_part:
                    return next_part
                else:
                    name, _ = os.path.splitext(next_part)
                    return name

        for pattern in self.SCOPE_PATTERNS:
            match = pattern.match(normalized)
            if match:
                module = match.group(1)
                if module and module.lower() not in {"src", "lib", "app", "packages"}:
                    return module

        if len(path_parts) >= 1 and "." in path_parts[0]:
            return None

        if len(path_parts) >= 1 and path_parts[0].lower() not in self.SRC_DIRS:
            return path_parts[0]

        return None

    def _extract_keywords_from_content(self, content: str) -> List[str]:
        if not content:
            return []

        keywords: List[str] = []
        content_lower = content.lower()

        for type_name, type_keywords in self.TYPE_KEYWORDS.items():
            for kw in type_keywords:
                if kw.lower() in content_lower:
                    keywords.append(kw)

        return list(set(keywords))

    def _detect_type_from_keywords(self, keywords: List[str]) -> Optional[str]:
        if not keywords:
            return None

        type_matches: Dict[str, int] = defaultdict(int)
        for type_name, type_keywords in self.TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in [t.lower() for t in type_keywords]:
                    type_matches[type_name] += 1

        if type_matches:
            return max(type_matches.items(), key=lambda x: x[1])[0]
        return None

    def _find_dominant_module(self, hints: List[FileContentHint]) -> Optional[str]:
        module_counts: Dict[str, int] = defaultdict(int)

        for hint in hints:
            if hint.module:
                module_counts[hint.module] += 1

        if not module_counts:
            return None

        total_files = len(hints)
        dominant_module, count = max(module_counts.items(), key=lambda x: x[1])

        if count / total_files >= 0.5:
            return dominant_module
        return None

    def _calculate_type_scores(
        self,
        hints: List[FileContentHint],
        file_stats: Optional[List[Any]]
    ) -> Dict[str, float]:
        scores: Dict[str, float] = defaultdict(float)

        all_types = ["feat", "fix", "refactor", "docs", "style", "perf", "test", "build", "ci", "chore", "revert"]
        for t in all_types:
            scores[t] = 0.1

        for hint in hints:
            if hint.change_type != "unknown":
                scores[hint.change_type] += 2.0

            for kw in hint.keywords:
                for type_name, type_keywords in self.TYPE_KEYWORDS.items():
                    if kw.lower() in [t.lower() for t in type_keywords]:
                        scores[type_name] += 1.0

        if file_stats:
            total_changes = sum(s.total for s in file_stats)
            if total_changes >= 500:
                scores["refactor"] += 1.5
            elif total_changes >= 200:
                scores["refactor"] += 0.8

        total = sum(scores.values())
        normalized = {k: round(v / total, 2) for k, v in sorted(
            scores.items(), key=lambda x: x[1], reverse=True
        )}

        return normalized

    def _detect_breaking_changes(
        self,
        hints: List[FileContentHint],
        file_stats: Optional[List[Any]],
        file_contents: Optional[Dict[str, str]]
    ) -> bool:
        if file_contents:
            for content in file_contents.values():
                if content:
                    content_lower = content.lower()
                    for kw in self.BREAKING_KEYWORDS:
                        if kw.lower() in content_lower:
                            return True

        if file_stats:
            deletion_ratio = sum(
                s.deletions for s in file_stats
            ) / max(sum(s.total for s in file_stats), 1)
            if deletion_ratio > 0.5 and sum(s.total for s in file_stats) > 100:
                return True

        return False

    def _generate_recommendations(
        self,
        hints: List[FileContentHint],
        type_scores: Dict[str, float],
        dominant_module: Optional[str],
        has_breaking: bool
    ) -> List[CommitRecommendation]:
        recommendations: List[CommitRecommendation] = []

        top_types = list(type_scores.keys())[:self.max_recommendations]
        if not top_types:
            top_types = ["feat"]

        for i, commit_type in enumerate(top_types):
            scopes = []
            if dominant_module:
                scopes = [dominant_module]

            subject_suggestion = self._generate_subject(
                commit_type, hints, dominant_module
            )
            body_suggestion = self._generate_body(commit_type, hints, has_breaking)

            template = self._build_template(
                commit_type, scopes, subject_suggestion, body_suggestion, has_breaking
            )

            confidence = type_scores.get(commit_type, 0.0) * (0.9 - i * 0.2)
            reason = self._generate_reason(commit_type, hints, confidence)

            recommendations.append(CommitRecommendation(
                template=template,
                type=commit_type,
                scopes=scopes,
                subject_suggestion=subject_suggestion,
                body_suggestion=body_suggestion,
                confidence=round(confidence, 2),
                reason=reason
            ))

        return recommendations

    def _generate_subject(
        self,
        commit_type: str,
        hints: List[FileContentHint],
        dominant_module: Optional[str]
    ) -> str:
        type_descriptions = {
            "feat": "添加新功能",
            "fix": "修复问题",
            "refactor": "重构代码",
            "docs": "更新文档",
            "style": "调整代码风格",
            "perf": "优化性能",
            "test": "完善测试",
            "build": "更新构建配置",
            "ci": "更新CI配置",
            "chore": "升级依赖或其他维护",
            "revert": "回滚变更"
        }

        desc = type_descriptions.get(commit_type, "更新代码")

        if dominant_module:
            files_in_module = [h for h in hints if h.module == dominant_module]
            if len(files_in_module) > 1:
                return f"{desc} - {dominant_module} 模块相关变更"
            elif files_in_module:
                filename = os.path.basename(files_in_module[0].path)
                return f"{desc} - {filename}"

        if len(hints) == 1:
            filename = os.path.basename(hints[0].path)
            return f"{desc} - {filename}"

        return f"{desc} - 涉及 {len(hints)} 个文件"

    def _generate_body(
        self,
        commit_type: str,
        hints: List[FileContentHint],
        has_breaking: bool
    ) -> str:
        parts: List[str] = []

        changed_files = [h.path for h in hints]
        if len(changed_files) <= 5:
            parts.append("变更文件:")
            for f in changed_files:
                parts.append(f"- {f}")
        else:
            parts.append(f"共变更 {len(changed_files)} 个文件")

        if has_breaking:
            parts.append("")
            parts.append("BREAKING CHANGE: 本次提交包含不兼容变更")
            parts.append("请参考具体文件了解变更详情")

        return "\n".join(parts)

    def _build_template(
        self,
        commit_type: str,
        scopes: List[str],
        subject: str,
        body: str,
        has_breaking: bool
    ) -> str:
        scope_str = ""
        if scopes:
            scope_str = f"({','.join(scopes)})"

        breaking_str = "!" if has_breaking else ""

        header = f"{commit_type}{scope_str}{breaking_str}: {subject}"

        if body:
            return f"{header}\n\n{body}"
        return header

    def _generate_reason(
        self,
        commit_type: str,
        hints: List[FileContentHint],
        confidence: float
    ) -> str:
        type_names = {
            "feat": "新功能",
            "fix": "Bug修复",
            "refactor": "重构",
            "docs": "文档更新",
            "style": "代码风格",
            "perf": "性能优化",
            "test": "测试",
            "build": "构建系统",
            "ci": "CI配置",
            "chore": "维护任务",
            "revert": "回滚"
        }

        name = type_names.get(commit_type, commit_type)

        if confidence >= 0.6:
            return f"高置信度推荐：根据文件类型和内容分析，本次变更属于{name}"
        elif confidence >= 0.3:
            return f"中等置信度：检测到{name}相关特征"
        else:
            return f"低置信度：可能是{name}类型，请根据实际情况调整"

    def _evaluate_existing_message(
        self,
        message: str,
        recommendations: List[CommitRecommendation]
    ) -> Dict[str, Any]:
        result = {
            "needs_improvement": False,
            "suggestions": [],
            "match_score": 0.0
        }

        if not message.strip():
            result["needs_improvement"] = True
            result["suggestions"].append("提交信息为空，建议使用推荐模板")
            return result

        if recommendations:
            top_rec = recommendations[0]
            if top_rec.type.lower() not in message.lower():
                result["needs_improvement"] = True
                result["suggestions"].append(
                    f"建议使用推荐类型 '{top_rec.type}': {top_rec.reason}"
                )
                result["suggestions"].append(
                    f"推荐模板: {top_rec.template}"
                )

            if top_rec.confidence >= 0.7:
                result["match_score"] = top_rec.confidence
            else:
                result["match_score"] = 0.5

        return result

    def format_recommendations(
        self,
        recommendations: List[CommitRecommendation],
        format_type: str = "text"
    ) -> str:
        if format_type == "json":
            import json
            return json.dumps(
                [r.__dict__ for r in recommendations],
                ensure_ascii=False,
                indent=2
            )

        lines = []
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"推荐 {i} (置信度: {rec.confidence:.0%}):")
            lines.append(f"  类型: {rec.type}")
            if rec.scopes:
                lines.append(f"  范围: {', '.join(rec.scopes)}")
            lines.append(f"  理由: {rec.reason}")
            lines.append(f"  模板:")
            lines.append(f"    {rec.template}")
            lines.append("")

        return "\n".join(lines)
