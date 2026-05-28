import json
import re
from typing import List, Tuple, Optional, Dict
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from app.config import get_settings
from app.schemas import SourceReference, ChatMessage, TableReference, ChartReference


SYSTEM_PROMPT = """你是一个专业的知识库问答助手。请根据以下规则回答用户的问题：

1. 只能使用提供的上下文信息来回答问题，不要编造信息。
2. 如果上下文信息不足以回答问题，请明确说明。
3. 回答要准确、简洁、专业。
4. 必须在回答中引用相关的文档来源。

特殊内容处理：
- 如果上下文包含表格数据，需要基于表格内容进行计算或汇总
- 如果上下文包含图表描述，需要解读图表趋势和关键数据
- 对于数据类问题，需要给出具体的数值和统计结果

输出格式要求：
- 先给出直接的答案
- 然后在括号中标注引用来源，格式：[文件名-页码:行号]
  例如：[文档1.pdf-P5:L10-L15] 或 [文档2.md-L20-L25]
- 对于表格数据，标注：[文档1.xlsx-表格1]
- 最后提供置信度评分（0-1之间的小数）和推理过程

请严格按照以下JSON格式输出：
{{
    "answer": "你的回答内容...",
    "confidence": 0.85,
    "reasoning": "推理过程说明...",
    "source_chunks": ["chunk_id1", "chunk_id2"]
}}"""

TABLE_ANALYSIS_PROMPT = """你是一个表格数据分析专家。根据用户的问题和提供的表格数据，进行分析和回答。

表格数据格式：
- 第一行为表头
- 后续行为数据行
- 每列数据用分隔符分开

分析要求：
1. 准确理解表格的结构和含义
2. 根据问题进行必要的计算（求和、平均、最大、最小等）
3. 给出具体的数值和结论
4. 标注数据来源的表格位置

请按照以下格式回答：
答案：[具体的答案内容]
数据来源：[表格位置]
计算过程：[如有计算，说明计算方法]"""


class LLMChain:
    _instance = None
    _llm: ChatOpenAI = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        settings = get_settings()
        cls._llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
        )

    @property
    def llm(self) -> ChatOpenAI:
        return self._llm

    def _format_source_location(self, source: SourceReference) -> str:
        location_parts = []
        
        if source.page is not None:
            location_parts.append(f"P{source.page}")
        
        if source.start_line is not None:
            if source.end_line is not None and source.end_line != source.start_line:
                location_parts.append(f"L{source.start_line}-L{source.end_line}")
            else:
                location_parts.append(f"L{source.start_line}")
        
        if location_parts:
            return f"{source.filename}-{':'.join(location_parts)}"
        else:
            return f"{source.filename}-{source.chunk_id}"

    def _extract_table_data(self, content: str) -> Optional[List[List[str]]]:
        table_patterns = [
            r'\|.*?\|',
            r'^\s*[-+]+\s*$',
            r'\t.*\t',
        ]
        
        lines = content.split('\n')
        table_lines = []
        
        for line in lines:
            if any(re.match(pattern, line.strip()) for pattern in table_patterns):
                cells = re.split(r'[\t|]+', line.strip())
                cells = [c.strip() for c in cells if c.strip()]
                if len(cells) >= 2:
                    table_lines.append(cells)
        
        if len(table_lines) >= 2:
            return table_lines
        
        return None

    def _format_table_for_context(
        self, table_data: List[List[str]], source: SourceReference
    ) -> str:
        if not table_data:
            return ""
        
        location = self._format_source_location(source)
        formatted_lines = [f"[表格数据 {location}]"]
        
        for row in table_data[:20]:
            formatted_lines.append(" | ".join(row))
        
        if len(table_data) > 20:
            formatted_lines.append(f"... (共{len(table_data)}行)")
        
        return "\n".join(formatted_lines)

    def _build_context(
        self,
        sources: List[SourceReference],
        tables: Optional[List[TableReference]] = None,
        charts: Optional[List[ChartReference]] = None,
    ) -> str:
        context_parts = []
        
        for idx, source in enumerate(sources, 1):
            location = self._format_source_location(source)
            table_data = self._extract_table_data(source.content)
            
            if table_data:
                context_parts.append(
                    f"[{location}] (相似度: {source.similarity_score:.2f}) [类型:表格]\n"
                    f"{self._format_table_for_context(table_data, source)}\n"
                )
            else:
                context_parts.append(
                    f"[{location}] (相似度: {source.similarity_score:.2f})\n"
                    f"{source.content}\n"
                )
        
        if tables:
            for table in tables:
                context_parts.append(
                    f"[表格 {table.table_id} - {table.filename}]\n"
                    f"标题: {table.summary}\n"
                    f"表头: {' | '.join(table.headers)}\n"
                )
                for row in table.rows[:10]:
                    context_parts.append(" | ".join(row))
        
        if charts:
            for chart in charts:
                context_parts.append(
                    f"[图表 {chart.chart_id} - {chart.filename}]\n"
                    f"类型: {chart.chart_type}, 标题: {chart.title}\n"
                    f"{chart.data_summary}\n"
                )
        
        return "\n".join(context_parts)

    def _format_chat_history(
        self, history: List[ChatMessage]
    ) -> List[HumanMessage | AIMessage]:
        formatted = []
        for msg in history:
            if msg.role == "user":
                formatted.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                formatted.append(AIMessage(content=msg.content))
        return formatted

    def _parse_llm_output(self, output: str) -> dict:
        try:
            json_match = re.search(r'\{[\s\S]*\}', output)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError):
            pass

        return {
            "answer": output,
            "confidence": 0.5,
            "reasoning": "无法解析结构化输出",
            "source_chunks": [],
        }

    def generate_answer(
        self,
        query: str,
        sources: List[SourceReference],
        chat_history: Optional[List[ChatMessage]] = None,
        tables: Optional[List[TableReference]] = None,
        charts: Optional[List[ChartReference]] = None,
    ) -> Tuple[str, float, str, List[str]]:
        if not sources and not tables and not charts:
            return (
                "抱歉，我没有找到与您问题相关的信息。请尝试使用其他关键词提问，或确保已上传相关文档。",
                0.0,
                "没有检索到相关文档片段",
                [],
            )

        context = self._build_context(sources, tables, charts)
        formatted_history = self._format_chat_history(chat_history or [])

        has_table = any(
            self._extract_table_data(s.content) for s in sources
        ) or tables

        prompt_content = SYSTEM_PROMPT
        if has_table:
            prompt_content += "\n\n" + TABLE_ANALYSIS_PROMPT

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=prompt_content),
            MessagesPlaceholder(variable_name="chat_history"),
            (
                "human",
                "上下文信息:\n{context}\n\n用户问题: {query}\n\n请根据上下文信息回答问题。"
            ),
        ])

        chain = prompt | self._llm | StrOutputParser()

        try:
            output = chain.invoke({
                "context": context,
                "query": query,
                "chat_history": formatted_history,
            })
        except Exception as e:
            return (
                f"生成回答时发生错误: {str(e)}",
                0.0,
                "LLM调用失败",
                [],
            )

        result = self._parse_llm_output(output)
        return (
            result.get("answer", output),
            float(result.get("confidence", 0.5)),
            result.get("reasoning", ""),
            result.get("source_chunks", []),
        )

    async def generate_answer_stream(
        self,
        query: str,
        sources: List[SourceReference],
        chat_history: Optional[List[ChatMessage]] = None,
        tables: Optional[List[TableReference]] = None,
        charts: Optional[List[ChartReference]] = None,
    ):
        if not sources and not tables and not charts:
            yield "抱歉，我没有找到与您问题相关的信息。"
            return

        context = self._build_context(sources, tables, charts)
        formatted_history = self._format_chat_history(chat_history or [])

        has_table = any(
            self._extract_table_data(s.content) for s in sources
        ) or tables

        prompt_content = SYSTEM_PROMPT
        if has_table:
            prompt_content += "\n\n" + TABLE_ANALYSIS_PROMPT

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=prompt_content),
            MessagesPlaceholder(variable_name="chat_history"),
            (
                "human",
                "上下文信息:\n{context}\n\n用户问题: {query}\n\n请根据上下文信息回答问题。"
            ),
        ])

        chain = prompt | self._llm | StrOutputParser()

        async for chunk in chain.astream({
            "context": context,
            "query": query,
            "chat_history": formatted_history,
        }):
            yield chunk

    def extract_tables_from_sources(
        self, sources: List[SourceReference]
    ) -> List[TableReference]:
        tables = []
        for source in sources:
            table_data = self._extract_table_data(source.content)
            if table_data and len(table_data) >= 2:
                headers = table_data[0]
                rows = table_data[1:]
                table = TableReference(
                    table_id=source.chunk_id,
                    document_id=source.document_id,
                    filename=source.filename,
                    page=source.page,
                    headers=headers,
                    rows=rows[:50],
                    summary=f"包含{len(rows)}行数据，{len(headers)}列",
                )
                tables.append(table)
        return tables


def get_llm_chain() -> LLMChain:
    return LLMChain()
