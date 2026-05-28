import os
import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Dict
from collections import Counter
from app.config import get_settings
from app.document_parser import DocumentParser, ParsedDocument, TableData, ChartData
from app.text_splitter import SemanticTextSplitter
from app.vector_store import get_vector_store, VectorStore
from app.llm_chain import get_llm_chain, LLMChain
from app.answer_evaluator import get_answer_evaluator, AnswerEvaluator
from app.schemas import (
    DocumentInfo,
    SourceReference,
    ChatMessage,
    ChatResponse,
    TableReference,
    ChartReference,
    AnswerEvaluationResult,
    UncoveredQuery,
    ActiveLearningStats,
)


class RAGChain:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        cls._vector_store: VectorStore = get_vector_store()
        cls._llm_chain: LLMChain = get_llm_chain()
        cls._evaluator: AnswerEvaluator = get_answer_evaluator()
        cls._text_splitter: SemanticTextSplitter = SemanticTextSplitter()
        cls._document_index: Dict[str, DocumentInfo] = {}
        cls._parsed_docs: Dict[str, ParsedDocument] = {}
        cls._uncovered_queries: List[UncoveredQuery] = []
        cls._query_history: List[Dict] = []
        cls._total_queries: int = 0
        cls._covered_queries: int = 0

    def process_document(
        self,
        file_path: str,
        filename: str,
        document_id: Optional[str] = None,
    ) -> DocumentInfo:
        if not DocumentParser.is_supported(filename):
            raise ValueError(f"Unsupported file type: {filename}")

        document_id = document_id or str(uuid.uuid4())
        file_size = os.path.getsize(file_path)

        parsed_doc = DocumentParser.parse(file_path, filename)
        langchain_docs = DocumentParser.to_langchain_documents(parsed_doc)
        chunks = self._text_splitter.split_documents(
            langchain_docs, document_id, parsed_doc
        )

        self._vector_store.add_documents(chunks)
        self._vector_store.persist()

        doc_info = DocumentInfo(
            document_id=document_id,
            filename=filename,
            file_type=parsed_doc.file_type,
            file_size=file_size,
            upload_time=datetime.now(),
            chunk_count=len(chunks),
            status="completed",
        )

        self._document_index[document_id] = doc_info
        self._parsed_docs[document_id] = parsed_doc
        return doc_info

    def get_parsed_document(self, document_id: str) -> Optional[ParsedDocument]:
        return self._parsed_docs.get(document_id)

    def _extract_tables_from_documents(
        self, document_ids: Optional[List[str]]
    ) -> List[TableReference]:
        tables = []
        docs_to_search = document_ids or list(self._parsed_docs.keys())
        
        for doc_id in docs_to_search:
            parsed_doc = self._parsed_docs.get(doc_id)
            if parsed_doc and parsed_doc.tables:
                doc_info = self._document_index.get(doc_id)
                filename = doc_info.filename if doc_info else doc_id
                
                for table in parsed_doc.tables:
                    tables.append(TableReference(
                        table_id=table.table_id,
                        document_id=doc_id,
                        filename=filename,
                        page=table.page,
                        headers=table.headers,
                        rows=table.rows,
                        summary=f"包含{len(table.rows)}行数据，{len(table.headers)}列",
                    ))
        
        return tables

    def _extract_charts_from_documents(
        self, document_ids: Optional[List[str]]
    ) -> List[ChartReference]:
        charts = []
        docs_to_search = document_ids or list(self._parsed_docs.keys())
        
        for doc_id in docs_to_search:
            parsed_doc = self._parsed_docs.get(doc_id)
            if parsed_doc and parsed_doc.charts:
                doc_info = self._document_index.get(doc_id)
                filename = doc_info.filename if doc_info else doc_id
                
                for chart in parsed_doc.charts:
                    data_summary = f"图表类型: {chart.chart_type}, 数据点: {len(chart.data_points)}"
                    charts.append(ChartReference(
                        chart_id=chart.chart_id,
                        document_id=doc_id,
                        filename=filename,
                        page=chart.page,
                        chart_type=chart.chart_type,
                        title=chart.title,
                        data_summary=data_summary,
                    ))
        
        return charts

    def chat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None,
        document_ids: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ) -> ChatResponse:
        self._total_queries += 1
        
        tables = self._extract_tables_from_documents(document_ids)
        charts = self._extract_charts_from_documents(document_ids)
        
        sources = self._vector_store.search_with_references(
            query=query,
            document_ids=document_ids,
        )

        has_tables = any(
            self._llm_chain._extract_table_data(s.content) for s in sources
        )
        
        extracted_tables = self._llm_chain.extract_tables_from_sources(sources)
        all_tables = tables + extracted_tables

        answer, confidence, reasoning, source_chunks = self._llm_chain.generate_answer(
            query=query,
            sources=sources,
            chat_history=chat_history,
            tables=all_tables if has_tables else tables,
            charts=charts,
        )

        final_sources = self._filter_sources(sources, source_chunks)
        final_confidence = self._adjust_confidence(confidence, sources)

        coverage_status = "covered"
        suggestions: List[str] = []

        if not sources and not tables and not charts:
            coverage_status = "uncovered"
            suggestions = self._generate_suggestions(query)
            self._record_uncovered_query(query, 0, suggestions)
            answer = (
                "抱歉，我没有找到与您问题相关的信息。\n\n"
                + "\n".join(f"- {s}" for s in suggestions)
            )
        elif final_confidence < 0.4:
            coverage_status = "low_coverage"
            suggestions = self._generate_suggestions(query)
            self._covered_queries += 1
        else:
            self._covered_queries += 1

        evaluation = self._evaluator.evaluate_answer(
            query, answer, final_sources
        )
        if evaluation.needs_improvement and final_confidence >= 0.3:
            optimization = self._evaluator.optimize_retrieval(
                query, sources, 0.5, 4
            )
            if optimization.should_expand_query and optimization.expanded_query:
                retry_sources = self._vector_store.search_with_references(
                    query=optimization.expanded_query,
                    document_ids=document_ids,
                )
                if retry_sources:
                    retry_answer, retry_confidence, retry_reasoning, retry_chunks = \
                        self._llm_chain.generate_answer(
                            query=query,
                            sources=retry_sources,
                            chat_history=chat_history,
                            tables=all_tables if has_tables else tables,
                            charts=charts,
                        )
                    retry_conf = self._adjust_confidence(retry_confidence, retry_sources)
                    if retry_conf > final_confidence:
                        answer = retry_answer
                        final_confidence = retry_conf
                        final_sources = self._filter_sources(retry_sources, retry_chunks)
                        reasoning = retry_reasoning

        return ChatResponse(
            session_id=session_id or str(uuid.uuid4()),
            answer=answer,
            confidence_score=final_confidence,
            sources=final_sources,
            tables=tables[:5],
            charts=charts[:5],
            reasoning=reasoning,
            suggestions=suggestions,
            coverage_status=coverage_status,
        )

    async def chat_stream(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None,
        document_ids: Optional[List[str]] = None,
    ):
        self._total_queries += 1
        
        tables = self._extract_tables_from_documents(document_ids)
        charts = self._extract_charts_from_documents(document_ids)
        
        sources = self._vector_store.search_with_references(
            query=query,
            document_ids=document_ids,
        )

        if not sources and not tables and not charts:
            suggestions = self._generate_suggestions(query)
            self._record_uncovered_query(query, 0, suggestions)
            yield "抱歉，我没有找到与您问题相关的信息。\n\n"
            for s in suggestions:
                yield f"- {s}\n"
            return

        has_tables = any(
            self._llm_chain._extract_table_data(s.content) for s in sources
        )
        
        extracted_tables = self._llm_chain.extract_tables_from_sources(sources)
        all_tables = tables + extracted_tables

        self._covered_queries += 1

        async for chunk in self._llm_chain.generate_answer_stream(
            query=query,
            sources=sources,
            chat_history=chat_history,
            tables=all_tables if has_tables else tables,
            charts=charts,
        ):
            yield chunk

    def evaluate_answer(
        self,
        query: str,
        answer: str,
        sources: List[SourceReference],
    ) -> AnswerEvaluationResult:
        evaluation = self._evaluator.evaluate_answer(query, answer, sources)
        return AnswerEvaluationResult(
            accuracy_score=evaluation.accuracy_score,
            completeness_score=evaluation.completeness_score,
            relevance_score=evaluation.relevance_score,
            overall_score=evaluation.overall_score,
            feedback=evaluation.feedback,
            needs_improvement=evaluation.needs_improvement,
            suggestions=evaluation.suggestions,
        )

    def _generate_suggestions(self, query: str) -> List[str]:
        suggestions = [
            "上传包含相关内容的文档（PDF、Word、Markdown）",
            "尝试使用更具体的关键词或重新表述问题",
            "检查现有文档是否包含所需信息",
        ]
        
        if self._uncovered_queries:
            similar_topics = self._find_similar_uncovered_queries(query)
            if similar_topics:
                suggestions.append(f"类似问题已被记录: {', '.join(similar_topics[:3])}")
        
        return suggestions

    def _find_similar_uncovered_queries(self, query: str) -> List[str]:
        query_words = set(query.lower().split())
        similar = []
        
        for uq in self._uncovered_queries[-20:]:
            uq_words = set(uq.query.lower().split())
            if query_words & uq_words:
                similar.append(uq.query)
        
        return similar[:5]

    def _record_uncovered_query(
        self,
        query: str,
        attempted_sources: int,
        suggested_documents: List[str],
    ):
        uncovered = UncoveredQuery(
            query=query,
            timestamp=datetime.now(),
            attempted_sources=attempted_sources,
            suggested_documents=suggested_documents,
        )
        self._uncovered_queries.append(uncovered)
        
        if len(self._uncovered_queries) > 100:
            self._uncovered_queries = self._uncovered_queries[-50:]

    def get_uncovered_queries(self) -> List[UncoveredQuery]:
        return self._uncovered_queries

    def get_active_learning_stats(self) -> ActiveLearningStats:
        uncovered_count = len(self._uncovered_queries)
        coverage_rate = (
            self._covered_queries / self._total_queries if self._total_queries > 0 else 1.0
        )
        
        frequent_queries = Counter(uq.query for uq in self._uncovered_queries)
        frequent_list = [
            {"query": q, "count": c}
            for q, c in frequent_queries.most_common(10)
        ]
        
        return ActiveLearningStats(
            total_queries=self._total_queries,
            covered_queries=self._covered_queries,
            uncovered_queries=uncovered_count,
            coverage_rate=coverage_rate,
            frequent_uncovered=frequent_list,
        )

    def _filter_sources(
        self,
        all_sources: List[SourceReference],
        referenced_chunk_ids: List[str],
    ) -> List[SourceReference]:
        if not referenced_chunk_ids:
            return all_sources

        filtered = []
        for source in all_sources:
            if source.chunk_id in referenced_chunk_ids:
                filtered.append(source)

        return filtered if filtered else all_sources

    def _adjust_confidence(
        self,
        llm_confidence: float,
        sources: List[SourceReference],
    ) -> float:
        if not sources:
            return 0.0

        avg_similarity = sum(s.similarity_score for s in sources) / len(sources)
        source_count_factor = min(len(sources) / 4.0, 1.0)
        combined_confidence = (
            0.4 * avg_similarity + 0.4 * llm_confidence + 0.2 * source_count_factor
        )

        return max(0.0, min(1.0, combined_confidence))

    def delete_document(self, document_id: str) -> bool:
        try:
            self._vector_store.delete_by_document_id(document_id)
            self._vector_store.persist()
            if document_id in self._document_index:
                del self._document_index[document_id]
            if document_id in self._parsed_docs:
                del self._parsed_docs[document_id]
            return True
        except Exception as e:
            print(f"Error deleting document {document_id}: {e}")
            return False

    def get_document_info(self, document_id: str) -> Optional[DocumentInfo]:
        return self._document_index.get(document_id)

    def list_documents(self) -> List[DocumentInfo]:
        return list(self._document_index.values())

    def get_total_documents(self) -> int:
        return self._vector_store.get_document_count()


def get_rag_chain() -> RAGChain:
    return RAGChain()
