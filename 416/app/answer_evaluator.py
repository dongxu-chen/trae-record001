import json
import re
from typing import List, Optional, Tuple
from dataclasses import dataclass
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.config import get_settings
from app.llm_chain import LLMChain
from app.schemas import SourceReference


@dataclass
class AnswerEvaluation:
    accuracy_score: float
    completeness_score: float
    relevance_score: float
    overall_score: float
    feedback: str
    needs_improvement: bool
    suggestions: List[str]


@dataclass
class RetrievalOptimization:
    should_expand_query: bool
    expanded_query: Optional[str]
    should_adjust_k: bool
    adjusted_k: Optional[int]
    should_lower_threshold: bool
    adjusted_threshold: Optional[float]


EVALUATION_PROMPT = """你是一个专业的答案质量评估专家。请根据以下信息评估答案的质量：

评估维度：
1. 准确性(0-1)：答案是否准确反映了来源文档的内容
2. 完整性(0-1)：答案是否完整回答了用户的问题
3. 相关性(0-1)：答案与用户问题的相关程度

评估规则：
- 检查答案是否忠实于来源文档
- 检查答案是否有编造或猜测的内容
- 检查答案是否遗漏了重要信息
- 检查引用来源是否正确

请严格按照以下JSON格式输出：
{{
    "accuracy": 0.85,
    "completeness": 0.75,
    "relevance": 0.90,
    "feedback": "评估反馈...",
    "needs_improvement": false,
    "suggestions": ["建议1", "建议2"]
}}"""


QUERY_EXPANSION_PROMPT = """你是一个查询优化专家。针对用户的问题，生成一个更精确、更适合检索的查询。

原始查询：{original_query}
上下文信息：{context_summary}

优化要求：
1. 保留原始查询的核心意图
2. 添加相关关键词以提高召回率
3. 对于复杂问题，拆分为子查询
4. 保持简洁（不超过原查询的2倍长度）

请直接返回优化后的查询文本，不要添加其他解释。"""


class AnswerEvaluator:
    _instance = None
    _llm = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        settings = get_settings()
        from langchain_openai import ChatOpenAI
        cls._llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0.0,
            max_tokens=1024,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
        )

    def evaluate_answer(
        self,
        query: str,
        answer: str,
        sources: List[SourceReference],
    ) -> AnswerEvaluation:
        if not sources:
            return AnswerEvaluation(
                accuracy_score=0.0,
                completeness_score=0.0,
                relevance_score=0.0,
                overall_score=0.0,
                feedback="没有检索到相关文档，无法评估答案质量",
                needs_improvement=True,
                suggestions=["请上传相关文档", "尝试使用其他关键词"],
            )

        context_summary = self._build_context_summary(sources)

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=EVALUATION_PROMPT),
            (
                "human",
                f"用户问题: {query}\n\n"
                f"来源文档摘要:\n{context_summary}\n\n"
                f"待评估答案:\n{answer}"
            ),
        ])

        chain = prompt | self._llm | StrOutputParser()

        try:
            output = chain.invoke({})
            result = self._parse_evaluation_output(output)
        except Exception as e:
            return AnswerEvaluation(
                accuracy_score=0.5,
                completeness_score=0.5,
                relevance_score=0.5,
                overall_score=0.5,
                feedback=f"评估过程出错: {str(e)}",
                needs_improvement=True,
                suggestions=["系统错误，请稍后重试"],
            )

        return result

    def optimize_retrieval(
        self,
        query: str,
        sources: List[SourceReference],
        current_threshold: float,
        current_k: int,
    ) -> RetrievalOptimization:
        optimization = RetrievalOptimization(
            should_expand_query=False,
            expanded_query=None,
            should_adjust_k=False,
            adjusted_k=None,
            should_lower_threshold=False,
            adjusted_threshold=None,
        )

        if not sources:
            optimization.should_expand_query = True
            optimization.expanded_query = self._expand_query(query, "")
            optimization.should_lower_threshold = True
            optimization.adjusted_threshold = max(0.2, current_threshold - 0.15)
            optimization.should_adjust_k = True
            optimization.adjusted_k = current_k + 2
            return optimization

        avg_score = sum(s.similarity_score for s in sources) / len(sources)
        max_score = max(s.similarity_score for s in sources) if sources else 0
        sources_count = len(sources)

        if max_score < current_threshold + 0.1:
            optimization.should_lower_threshold = True
            optimization.adjusted_threshold = max(0.2, current_threshold - 0.1)

        if sources_count < current_k and avg_score < 0.7:
            optimization.should_adjust_k = True
            optimization.adjusted_k = min(current_k + 2, 10)

        if avg_score < 0.6 and sources_count < 3:
            optimization.should_expand_query = True
            context_summary = self._build_context_summary(sources)
            optimization.expanded_query = self._expand_query(query, context_summary)

        return optimization

    def _expand_query(self, original_query: str, context_summary: str) -> str:
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=QUERY_EXPANSION_PROMPT),
            (
                "human",
                f"原始查询: {original_query}\n"
                f"上下文信息: {context_summary if context_summary else '无'}"
            ),
        ])

        chain = prompt | self._llm | StrOutputParser()

        try:
            output = chain.invoke({})
            expanded = output.strip()
            if expanded and len(expanded) < len(original_query) * 2 + 50:
                return expanded
        except Exception:
            pass

        return original_query

    def _build_context_summary(self, sources: List[SourceReference]) -> str:
        summary_parts = []
        for idx, source in enumerate(sources[:5], 1):
            location = self._format_location(source)
            summary_parts.append(
                f"[{idx}] {source.filename} {location}: "
                f"{source.content[:200]}..."
            )
        return "\n".join(summary_parts)

    def _format_location(self, source: SourceReference) -> str:
        parts = []
        if source.page is not None:
            parts.append(f"P{source.page}")
        if source.start_line is not None:
            if source.end_line is not None and source.end_line != source.start_line:
                parts.append(f"L{source.start_line}-L{source.end_line}")
            else:
                parts.append(f"L{source.start_line}")
        return f"({':'.join(parts)})" if parts else ""

    def _parse_evaluation_output(self, output: str) -> AnswerEvaluation:
        try:
            json_match = re.search(r'\{[\s\S]*\}', output)
            if json_match:
                data = json.loads(json_match.group(0))
                accuracy = float(data.get("accuracy", 0.5))
                completeness = float(data.get("completeness", 0.5))
                relevance = float(data.get("relevance", 0.5))
                overall = (accuracy * 0.5 + completeness * 0.3 + relevance * 0.2)

                return AnswerEvaluation(
                    accuracy_score=accuracy,
                    completeness_score=completeness,
                    relevance_score=relevance,
                    overall_score=overall,
                    feedback=data.get("feedback", ""),
                    needs_improvement=data.get("needs_improvement", overall < 0.7),
                    suggestions=data.get("suggestions", []),
                )
        except (json.JSONDecodeError, AttributeError, ValueError):
            pass

        return AnswerEvaluation(
            accuracy_score=0.5,
            completeness_score=0.5,
            relevance_score=0.5,
            overall_score=0.5,
            feedback="无法解析评估结果",
            needs_improvement=True,
            suggestions=["评估系统解析错误"],
        )

    def is_answer_acceptable(self, evaluation: AnswerEvaluation) -> bool:
        return evaluation.overall_score >= 0.6 and not evaluation.needs_improvement

    def get_improvement_suggestions(
        self,
        evaluation: AnswerEvaluation,
        query: str,
    ) -> List[str]:
        suggestions = evaluation.suggestions.copy()

        if evaluation.accuracy_score < 0.6:
            suggestions.append("答案可能不准确，建议上传更详细的文档")
        if evaluation.completeness_score < 0.6:
            suggestions.append("答案可能不完整，尝试使用更具体的问题")
        if evaluation.relevance_score < 0.6:
            suggestions.append("答案与问题相关性低，尝试重新表述问题")

        return suggestions[:5]


def get_answer_evaluator() -> AnswerEvaluator:
    return AnswerEvaluator()
