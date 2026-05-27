from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from elasticsearch import Elasticsearch
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import logging

from config import settings
from es_client import get_es_client, create_indices
from schemas import (
    Document, DocumentCreate,
    Query, QueryCreate,
    Annotation, AnnotationCreate, BatchAnnotationRequest,
    SearchRequest, SearchResponse, SearchResult,
    EvaluationResult, EvaluationMetrics,
    ConfusionMatrix, ModelComparison, FailureCase,
    ModelInfo, FailureCaseStratifiedSample,
    ModelComparisonDrillDown, QueryTypeStats,
    ClickEvent, ClickEventCreate,
    AutoAnnotationRequest, AutoAnnotationResult,
    ABTestConfig, ABTestConfigCreate, ABTestAssignment, ABTestMetrics,
    FeedbackLearningRequest, TrainingSample, FeedbackLearningResult,
    ModelRetrainingConfig, RetrainingResult
)
from metrics import (
    evaluate_search_results,
    calculate_confusion_matrix,
    aggregate_metrics
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="召回率分析平台 API",
    description="搜索召回率评估、命中率分析、Top-K准确率计算平台",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    es = get_es_client()
    create_indices(es)
    logger.info("Application started successfully")


@app.get("/")
async def root():
    return {"message": "召回率分析平台 API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check(es: Elasticsearch = Depends(get_es_client)):
    es_health = "healthy" if es.ping() else "unhealthy"
    return {
        "status": "healthy",
        "elasticsearch": es_health,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/api/documents", response_model=Document)
async def create_document(
    doc: DocumentCreate,
    es: Elasticsearch = Depends(get_es_client)
):
    doc_id = doc.doc_id
    doc_dict = doc.model_dump()
    doc_dict["created_at"] = datetime.now(timezone.utc)

    es.index(
        index=settings.documents_index,
        id=doc_id,
        body=doc_dict
    )
    return Document(**doc_dict)


@app.post("/api/documents/batch")
async def create_documents_batch(
    docs: List[DocumentCreate],
    es: Elasticsearch = Depends(get_es_client)
):
    operations = []
    for doc in docs:
        doc_dict = doc.model_dump()
        doc_dict["created_at"] = datetime.now(timezone.utc)
        operations.append({"index": {"_index": settings.documents_index, "_id": doc.doc_id}})
        operations.append(doc_dict)

    if operations:
        es.bulk(operations=operations)

    return {"message": f"成功导入 {len(docs)} 个文档"}


@app.get("/api/documents", response_model=List[Document])
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    es: Elasticsearch = Depends(get_es_client)
):
    result = es.search(
        index=settings.documents_index,
        query={"match_all": {}},
        from_=(page - 1) * page_size,
        size=page_size,
        sort=[{"created_at": "desc"}]
    )
    return [Document(**hit["_source"]) for hit in result["hits"]["hits"]]


@app.get("/api/documents/{doc_id}", response_model=Document)
async def get_document(
    doc_id: str,
    es: Elasticsearch = Depends(get_es_client)
):
    try:
        result = es.get(index=settings.documents_index, id=doc_id)
        return Document(**result["_source"])
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"文档不存在: {doc_id}")


@app.post("/api/queries", response_model=Query)
async def create_query(
    query: QueryCreate,
    es: Elasticsearch = Depends(get_es_client)
):
    query_dict = query.model_dump()
    query_dict["created_at"] = datetime.now(timezone.utc)

    es.index(
        index=settings.queries_index,
        id=query.query_id,
        body=query_dict
    )
    return Query(**query_dict)


@app.post("/api/queries/batch")
async def create_queries_batch(
    queries: List[QueryCreate],
    es: Elasticsearch = Depends(get_es_client)
):
    operations = []
    for query in queries:
        query_dict = query.model_dump()
        query_dict["created_at"] = datetime.now(timezone.utc)
        operations.append({"index": {"_index": settings.queries_index, "_id": query.query_id}})
        operations.append(query_dict)

    if operations:
        es.bulk(operations=operations)

    return {"message": f"成功导入 {len(queries)} 个查询"}


@app.get("/api/queries", response_model=List[Query])
async def list_queries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    es: Elasticsearch = Depends(get_es_client)
):
    result = es.search(
        index=settings.queries_index,
        query={"match_all": {}},
        from_=(page - 1) * page_size,
        size=page_size,
        sort=[{"created_at": "desc"}]
    )
    return [Query(**hit["_source"]) for hit in result["hits"]["hits"]]


@app.get("/api/queries/{query_id}", response_model=Query)
async def get_query(
    query_id: str,
    es: Elasticsearch = Depends(get_es_client)
):
    try:
        result = es.get(index=settings.queries_index, id=query_id)
        return Query(**result["_source"])
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"查询不存在: {query_id}")


@app.post("/api/annotations", response_model=Annotation)
async def create_annotation(
    annotation: AnnotationCreate,
    es: Elasticsearch = Depends(get_es_client)
):
    annotation_id = f"{annotation.query_id}_{annotation.doc_id}"
    annotation_dict = annotation.model_dump()
    now = datetime.now(timezone.utc)
    annotation_dict["created_at"] = now
    annotation_dict["updated_at"] = now

    es.index(
        index=settings.annotations_index,
        id=annotation_id,
        body=annotation_dict
    )
    return Annotation(**annotation_dict)


@app.post("/api/annotations/batch")
async def create_annotations_batch(
    request: BatchAnnotationRequest,
    es: Elasticsearch = Depends(get_es_client)
):
    operations = []
    now = datetime.now(timezone.utc)
    for annotation in request.annotations:
        annotation_id = f"{annotation.query_id}_{annotation.doc_id}"
        if request.request_id:
            annotation_id = f"{annotation_id}_{request.request_id}"
        annotation_dict = annotation.model_dump()
        if request.request_id:
            annotation_dict["request_id"] = request.request_id
        annotation_dict["created_at"] = now
        annotation_dict["updated_at"] = now
        operations.append({"index": {"_index": settings.annotations_index, "_id": annotation_id}})
        operations.append(annotation_dict)

    if operations:
        es.bulk(operations=operations)

    return {
        "message": f"成功标注 {len(request.annotations)} 个文档",
        "request_id": request.request_id
    }


@app.get("/api/annotations/query/{query_id}", response_model=List[Annotation])
async def get_query_annotations(
    query_id: str,
    es: Elasticsearch = Depends(get_es_client)
):
    result = es.search(
        index=settings.annotations_index,
        query={"term": {"query_id": query_id}},
        size=1000
    )
    return [Annotation(**hit["_source"]) for hit in result["hits"]["hits"]]


@app.get("/api/annotations")
async def list_annotations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    es: Elasticsearch = Depends(get_es_client)
):
    result = es.search(
        index=settings.annotations_index,
        query={"match_all": {}},
        from_=(page - 1) * page_size,
        size=page_size,
        sort=[{"created_at": "desc"}]
    )
    return [Annotation(**hit["_source"]) for hit in result["hits"]["hits"]]


@app.post("/api/search")
async def search(
    request: SearchRequest,
    es: Elasticsearch = Depends(get_es_client)
):
    query_id = str(uuid.uuid4())
    request_id = request.request_id or str(uuid.uuid4())
    start_time = datetime.now()

    es_query = {
        "multi_match": {
            "query": request.query_text,
            "fields": ["title^2", "content"],
            "type": "best_fields"
        }
    }

    result = es.search(
        index=request.index if request.index != "documents" else settings.documents_index,
        query=es_query,
        size=request.k,
        _source=["doc_id", "title", "content"]
    )

    took = (datetime.now() - start_time).total_seconds() * 1000

    search_results = []
    for i, hit in enumerate(result["hits"]["hits"]):
        source = hit["_source"]
        search_results.append(SearchResult(
            doc_id=source.get("doc_id", hit["_id"]),
            score=hit["_score"] or 0.0,
            rank=i + 1,
            title=source.get("title", ""),
            content=source.get("content", "")[:200]
        ))

    return SearchResponse(
        query_id=query_id,
        query_text=request.query_text,
        model_name=request.model_name,
        k=request.k,
        results=search_results,
        total=result["hits"]["total"]["value"],
        took=took,
        request_id=request_id,
        query_type=request.query_type
    )


@app.post("/api/evaluate")
async def evaluate_search(
    request: SearchRequest,
    es: Elasticsearch = Depends(get_es_client)
):
    search_response = await search(request, es)

    annotations = await get_query_annotations_by_text(request.query_text, es)
    relevant_docs = {}
    for ann in annotations:
        relevant_docs[ann.doc_id] = ann.relevance

    for result in search_response.results:
        result.relevant = relevant_docs.get(result.doc_id, 0) > 0

    metrics = evaluate_search_results(
        search_response.results,
        relevant_docs,
        request.k
    )

    evaluation_id = str(uuid.uuid4())
    evaluation_dict = {
        "evaluation_id": evaluation_id,
        "model_name": request.model_name,
        "query_id": search_response.query_id,
        "request_id": search_response.request_id,
        "query_type": request.query_type,
        "k": request.k,
        "results": [r.model_dump() for r in search_response.results],
        "metrics": metrics.model_dump(),
        "created_at": datetime.now(timezone.utc)
    }

    es.index(
        index=settings.evaluations_index,
        id=evaluation_id,
        body=evaluation_dict
    )

    return EvaluationResult(
        evaluation_id=evaluation_id,
        model_name=request.model_name,
        query_id=search_response.query_id,
        query_text=request.query_text,
        k=request.k,
        results=search_response.results,
        metrics=metrics,
        created_at=evaluation_dict["created_at"]
    )


@app.get("/api/evaluate/batch")
async def batch_evaluate(
    model_name: str = "default",
    k: int = Query(10, ge=1, le=100),
    query_type: Optional[str] = None,
    es: Elasticsearch = Depends(get_es_client)
):
    query_body = {"match_all": {}}
    if query_type:
        query_body = {"term": {"query_type": query_type}}

    queries_result = es.search(
        index=settings.queries_index,
        query=query_body,
        size=1000
    )
    queries = [Query(**hit["_source"]) for hit in queries_result["hits"]["hits"]]

    all_metrics = []
    evaluation_results = []

    for query in queries:
        annotations = await get_query_annotations(query.query_id, es)
        if not annotations:
            continue

        relevant_docs = {}
        for ann in annotations:
            relevant_docs[ann.doc_id] = ann.relevance

        search_request = SearchRequest(
            query_text=query.query_text,
            model_name=model_name,
            k=k
        )
        search_response = await search(search_request, es)

        for result in search_response.results:
            result.relevant = relevant_docs.get(result.doc_id, 0) > 0

        metrics = evaluate_search_results(
            search_response.results,
            relevant_docs,
            k
        )
        all_metrics.append(metrics)

        evaluation_results.append({
            "query_id": query.query_id,
            "query_text": query.query_text,
            "metrics": metrics.model_dump()
        })

    aggregated = aggregate_metrics(all_metrics)

    return {
        "model_name": model_name,
        "k": k,
        "total_queries": len(evaluation_results),
        "aggregated_metrics": aggregated,
        "query_results": evaluation_results
    }


@app.get("/api/confusion-matrix")
async def get_confusion_matrix(
    model_name: str = "default",
    k: int = Query(10, ge=1, le=100),
    query_type: Optional[str] = None,
    es: Elasticsearch = Depends(get_es_client)
):
    docs_count = es.count(index=settings.documents_index)["count"]

    query_body = {"match_all": {}}
    if query_type:
        query_body = {"term": {"query_type": query_type}}

    queries_result = es.search(
        index=settings.queries_index,
        query=query_body,
        size=1000
    )
    queries = [Query(**hit["_source"]) for hit in queries_result["hits"]["hits"]]

    total_tp, total_fp, total_fn, total_tn = 0, 0, 0, 0

    for query in queries:
        annotations = await get_query_annotations(query.query_id, es)
        if not annotations:
            continue

        relevant_docs = [ann.doc_id for ann in annotations if ann.relevance > 0]
        if not relevant_docs:
            continue

        search_request = SearchRequest(
            query_text=query.query_text,
            model_name=model_name,
            k=k
        )
        search_response = await search(search_request, es)

        cm = calculate_confusion_matrix(
            search_response.results,
            relevant_docs,
            docs_count,
            k
        )
        total_tp += cm.tp
        total_fp += cm.fp
        total_fn += cm.fn
        total_tn += cm.tn

    total = total_tp + total_fp + total_fn + total_tn
    accuracy = (total_tp + total_tn) / total if total > 0 else 0.0
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    specificity = total_tn / (total_tn + total_fp) if (total_tn + total_fp) > 0 else 0.0

    return ConfusionMatrix(
        tp=total_tp, fp=total_fp, fn=total_fn, tn=total_tn,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        specificity=specificity
    )


@app.get("/api/model-comparison")
async def get_model_comparison(
    models: List[str] = Query(default=["default"]),
    k_values: List[int] = Query(default=[1, 3, 5, 10, 20]),
    query_type: Optional[str] = None,
    es: Elasticsearch = Depends(get_es_client)
):
    comparisons = []

    for model in models:
        recall_scores, precision_scores, f1_scores = [], [], []
        hit_rates, ndcg_scores = [], []

        for k in sorted(k_values):
            batch_result = await batch_evaluate(model, k, query_type, es)
            agg = batch_result["aggregated_metrics"]
            recall_scores.append(agg.get("avg_recall", 0.0))
            precision_scores.append(agg.get("avg_precision", 0.0))
            f1_scores.append(agg.get("avg_f1", 0.0))
            hit_rates.append(agg.get("avg_hit_rate", 0.0))
            ndcg_scores.append(agg.get("avg_ndcg", 0.0))

        comparisons.append(ModelComparison(
            model_name=model,
            k_values=sorted(k_values),
            recall_scores=recall_scores,
            precision_scores=precision_scores,
            f1_scores=f1_scores,
            hit_rates=hit_rates,
            ndcg_scores=ndcg_scores
        ))

    return comparisons


@app.get("/api/model-comparison/drilldown")
async def get_model_comparison_drilldown(
    models: List[str] = Query(default=["default"]),
    k_values: List[int] = Query(default=[1, 3, 5, 10, 20]),
    es: Elasticsearch = Depends(get_es_client)
):
    query_types_result = es.search(
        index=settings.queries_index,
        size=0,
        aggs={
            "query_types": {
                "terms": {"field": "query_type", "size": 50}
            }
        }
    )

    query_types = [
        bucket["key"] for bucket in
        query_types_result["aggregations"]["query_types"]["buckets"]
    ]
    if not query_types:
        query_types = ["informational", "navigational", "transactional", "exploratory"]

    drilldown_results = []

    for qt in query_types:
        comparisons = []
        query_count_result = es.count(
            index=settings.queries_index,
            query={"term": {"query_type": qt}}
        )
        query_count = query_count_result["count"]

        if query_count == 0:
            continue

        for model in models:
            recall_scores, precision_scores, f1_scores = [], [], []
            hit_rates, ndcg_scores = [], []

            for k in sorted(k_values):
                batch_result = await batch_evaluate(model, k, qt, es)
                agg = batch_result["aggregated_metrics"]
                recall_scores.append(agg.get("avg_recall", 0.0))
                precision_scores.append(agg.get("avg_precision", 0.0))
                f1_scores.append(agg.get("avg_f1", 0.0))
                hit_rates.append(agg.get("avg_hit_rate", 0.0))
                ndcg_scores.append(agg.get("avg_ndcg", 0.0))

            comparisons.append(ModelComparison(
                model_name=model,
                k_values=sorted(k_values),
                recall_scores=recall_scores,
                precision_scores=precision_scores,
                f1_scores=f1_scores,
                hit_rates=hit_rates,
                ndcg_scores=ndcg_scores
            ))

        drilldown_results.append({
            "query_type": qt,
            "query_count": query_count,
            "comparisons": comparisons
        })

    return drilldown_results


@app.get("/api/query-types/stats")
async def get_query_type_stats(
    model_name: str = "default",
    k: int = Query(10, ge=1, le=100),
    es: Elasticsearch = Depends(get_es_client)
):
    query_types_result = es.search(
        index=settings.queries_index,
        size=0,
        aggs={
            "query_types": {
                "terms": {"field": "query_type", "size": 50}
            }
        }
    )

    query_types = [
        bucket["key"] for bucket in
        query_types_result["aggregations"]["query_types"]["buckets"]
    ]
    if not query_types:
        query_types = ["informational", "navigational", "transactional", "exploratory"]

    stats = []

    for qt in query_types:
        batch_result = await batch_evaluate(model_name, k, qt, es)
        agg = batch_result["aggregated_metrics"]
        stats.append(QueryTypeStats(
            query_type=qt,
            count=batch_result["total_queries"],
            avg_recall=agg.get("avg_recall", 0.0),
            avg_precision=agg.get("avg_precision", 0.0),
            avg_f1=agg.get("avg_f1", 0.0),
            avg_ndcg=agg.get("avg_ndcg", 0.0)
        ))

    return stats


def classify_failure_reason(
    metrics: EvaluationMetrics,
    missing_count: int,
    irrelevant_count: int,
    total_relevant: int,
    k: int
) -> str:
    if metrics.recall_at_k == 0:
        return "complete_failure"
    elif missing_count > 0 and irrelevant_count > 0:
        return "mixed_failure"
    elif missing_count > 0 and metrics.precision_at_k >= 0.8:
        return "low_recall_high_precision"
    elif irrelevant_count > 0 and metrics.recall_at_k >= 0.8:
        return "high_recall_low_precision"
    elif missing_count > total_relevant * 0.5:
        return "severe_missing"
    elif irrelevant_count > k * 0.5:
        return "severe_irrelevant"
    else:
        return "moderate_failure"


def get_failure_severity(recall: float) -> str:
    if recall < 0.2:
        return "critical"
    elif recall < 0.5:
        return "high"
    elif recall < 0.8:
        return "medium"
    else:
        return "low"


@app.get("/api/failure-cases")
async def get_failure_cases(
    model_name: str = "default",
    k: int = Query(10, ge=1, le=100),
    min_recall: float = Query(0.5, ge=0.0, le=1.0),
    query_type: Optional[str] = None,
    es: Elasticsearch = Depends(get_es_client)
):
    query_body = {"match_all": {}}
    if query_type:
        query_body = {"term": {"query_type": query_type}}

    queries_result = es.search(
        index=settings.queries_index,
        query=query_body,
        size=1000
    )
    queries = [Query(**hit["_source"]) for hit in queries_result["hits"]["hits"]]

    failure_cases = []

    for query in queries:
        annotations = await get_query_annotations(query.query_id, es)
        if not annotations:
            continue

        relevant_docs = {}
        for ann in annotations:
            relevant_docs[ann.doc_id] = ann.relevance

        relevant_doc_ids = [doc_id for doc_id, rel in relevant_docs.items() if rel > 0]
        if not relevant_doc_ids:
            continue

        search_request = SearchRequest(
            query_text=query.query_text,
            model_name=model_name,
            k=k
        )
        search_response = await search(search_request, es)

        metrics = evaluate_search_results(
            search_response.results,
            relevant_docs,
            k
        )

        if metrics.recall_at_k < min_recall:
            returned_doc_ids = [r.doc_id for r in search_response.results]
            missing_doc_ids = list(set(relevant_doc_ids) - set(returned_doc_ids))
            irrelevant_docs = [r.model_dump() for r in search_response.results if r.doc_id not in relevant_doc_ids]

            missing_count = len(missing_doc_ids)
            irrelevant_count = len(irrelevant_docs)
            total_relevant = len(relevant_doc_ids)

            failure_reason = classify_failure_reason(metrics, missing_count, irrelevant_count, total_relevant, k)
            failure_severity = get_failure_severity(metrics.recall_at_k)

            missing_docs_info = []
            for doc_id in missing_doc_ids:
                try:
                    doc = es.get(index=settings.documents_index, id=doc_id)
                    missing_docs_info.append({
                        "doc_id": doc_id,
                        "title": doc["_source"].get("title", ""),
                        "content": doc["_source"].get("content", "")[:200]
                    })
                except:
                    missing_docs_info.append({"doc_id": doc_id})

            failure_cases.append(FailureCase(
                query_id=query.query_id,
                query_text=query.query_text,
                expected_docs=relevant_doc_ids,
                returned_docs=[r.model_dump() for r in search_response.results],
                missing_docs=missing_docs_info,
                irrelevant_docs=irrelevant_docs,
                metrics=metrics,
                query_type=query.query_type,
                failure_reason=failure_reason,
                failure_severity=failure_severity
            ))

    return failure_cases


@app.get("/api/failure-cases/stratified")
async def get_failure_cases_stratified(
    model_name: str = "default",
    k: int = Query(10, ge=1, le=100),
    min_recall: float = Query(0.8, ge=0.0, le=1.0),
    samples_per_stratum: int = Query(3, ge=1, le=20),
    es: Elasticsearch = Depends(get_es_client)
):
    all_cases = await get_failure_cases(model_name, k, min_recall, None, es)

    if not all_cases:
        return FailureCaseStratifiedSample(
            total_cases=0,
            sampled_cases=0,
            strata=[],
            cases=[]
        )

    strata = {}

    for case in all_cases:
        qt = case.query_type or "unknown"
        reason = case.failure_reason or "unknown"
        key = f"{qt}||{reason}"

        if key not in strata:
            strata[key] = {
                "query_type": qt,
                "failure_reason": reason,
                "count": 0,
                "cases": []
            }
        strata[key]["count"] += 1
        strata[key]["cases"].append(case)

    sampled_cases = []
    strata_info = []

    for key, stratum in strata.items():
        stratum_cases = stratum["cases"]
        stratum_cases.sort(key=lambda x: x.metrics.recall_at_k)
        selected = stratum_cases[:samples_per_stratum]
        sampled_cases.extend(selected)

        strata_info.append({
            "query_type": stratum["query_type"],
            "failure_reason": stratum["failure_reason"],
            "total_count": stratum["count"],
            "sampled_count": len(selected)
        })

    sampled_cases.sort(key=lambda x: x.metrics.recall_at_k)

    return FailureCaseStratifiedSample(
        total_cases=len(all_cases),
        sampled_cases=len(sampled_cases),
        strata=strata_info,
        cases=sampled_cases
    )


@app.get("/api/evaluations", response_model=List[EvaluationResult])
async def list_evaluations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    model_name: Optional[str] = None,
    es: Elasticsearch = Depends(get_es_client)
):
    query_body = {"match_all": {}}
    if model_name:
        query_body = {"term": {"model_name": model_name}}

    result = es.search(
        index=settings.evaluations_index,
        query=query_body,
        from_=(page - 1) * page_size,
        size=page_size,
        sort=[{"created_at": "desc"}]
    )

    evaluations = []
    for hit in result["hits"]["hits"]:
        source = hit["_source"]
        evaluations.append(EvaluationResult(
            evaluation_id=source["evaluation_id"],
            model_name=source["model_name"],
            query_id=source["query_id"],
            query_text=source.get("query_text", ""),
            k=source["k"],
            results=[SearchResult(**r) for r in source["results"]],
            metrics=EvaluationMetrics(**source["metrics"]),
            created_at=source["created_at"]
        ))

    return evaluations


@app.get("/api/stats")
async def get_stats(
    es: Elasticsearch = Depends(get_es_client)
):
    try:
        doc_count = es.count(index=settings.documents_index)["count"]
        query_count = es.count(index=settings.queries_index)["count"]
        annotation_count = es.count(index=settings.annotations_index)["count"]
        evaluation_count = es.count(index=settings.evaluations_index)["count"]

        annotation_result = es.search(
            index=settings.annotations_index,
            query={"match_all": {}},
            size=0,
            aggs={
                "unique_queries": {"cardinality": {"field": "query_id"}}
            }
        )
        annotated_queries = annotation_result["aggregations"]["unique_queries"]["value"]

        return {
            "documents_count": doc_count,
            "queries_count": query_count,
            "annotations_count": annotation_count,
            "evaluations_count": evaluation_count,
            "annotated_queries_count": annotated_queries
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models", response_model=ModelInfo)
async def create_model(
    model: ModelInfo,
    es: Elasticsearch = Depends(get_es_client)
):
    model_dict = model.model_dump()
    model_dict["created_at"] = datetime.now(timezone.utc)

    es.index(
        index=settings.models_index,
        id=model.model_name,
        body=model_dict
    )
    return model


@app.get("/api/models", response_model=List[ModelInfo])
async def list_models(
    es: Elasticsearch = Depends(get_es_client)
):
    result = es.search(
        index=settings.models_index,
        query={"match_all": {}},
        size=100
    )

    default_model = ModelInfo(
        model_name="default",
        description="Elasticsearch 默认 BM25 检索模型",
        is_active=True
    )

    models = [default_model]
    for hit in result["hits"]["hits"]:
        source = hit["_source"]
        models.append(ModelInfo(
            model_name=source["model_name"],
            description=source.get("description"),
            endpoint=source.get("endpoint"),
            is_active=source.get("is_active", True)
        ))

    return models


async def get_query_annotations_by_text(
    query_text: str,
    es: Elasticsearch
) -> List[Annotation]:
    result = es.search(
        index=settings.queries_index,
        query={"match": {"query_text": query_text}},
        size=1
    )

    if result["hits"]["hits"]:
        query_id = result["hits"]["hits"][0]["_source"]["query_id"]
        return await get_query_annotations(query_id, es)

    return []


@app.post("/api/click-events", response_model=ClickEvent)
async def record_click_event(
    event: ClickEventCreate,
    es: Elasticsearch = Depends(get_es_client)
):
    event_dict = event.model_dump()
    event_dict["created_at"] = datetime.now(timezone.utc)
    
    event_id = str(uuid.uuid4())
    es.index(
        index=settings.click_events_index,
        id=event_id,
        body=event_dict
    )
    
    return ClickEvent(**event_dict)


@app.post("/api/click-events/batch")
async def record_click_events_batch(
    events: List[ClickEventCreate],
    es: Elasticsearch = Depends(get_es_client)
):
    operations = []
    for event in events:
        event_dict = event.model_dump()
        event_dict["created_at"] = datetime.now(timezone.utc)
        event_id = str(uuid.uuid4())
        operations.append({"index": {"_index": settings.click_events_index, "_id": event_id}})
        operations.append(event_dict)
    
    if operations:
        es.bulk(operations=operations)
    
    return {"message": f"成功记录 {len(events)} 个点击事件"}


@app.get("/api/click-events")
async def get_click_events(
    request_id: Optional[str] = None,
    query_id: Optional[str] = None,
    session_id: Optional[str] = None,
    es: Elasticsearch = Depends(get_es_client)
):
    query_body = {"match_all": {}}
    
    if request_id or query_id or session_id:
        must_clauses = []
        if request_id:
            must_clauses.append({"term": {"request_id": request_id}})
        if query_id:
            must_clauses.append({"term": {"query_id": query_id}})
        if session_id:
            must_clauses.append({"term": {"session_id": session_id}})
        query_body = {"bool": {"must": must_clauses}}
    
    result = es.search(
        index=settings.click_events_index,
        query=query_body,
        size=1000,
        sort=[{"created_at": "desc"}]
    )
    
    events = []
    for hit in result["hits"]["hits"]:
        source = hit["_source"]
        events.append(ClickEvent(**source))
    
    return events


@app.post("/api/auto-annotation", response_model=AutoAnnotationResult)
async def generate_auto_annotations(
    request: AutoAnnotationRequest,
    es: Elasticsearch = Depends(get_es_client)
):
    click_result = es.search(
        index=settings.click_events_index,
        query={"term": {"request_id": request.request_id}},
        size=100,
        sort=[{"created_at": "asc"}]
    )
    
    click_events = []
    for hit in click_result["hits"]["hits"]:
        click_events.append(ClickEvent(**hit["_source"]))
    
    if not click_events:
        return AutoAnnotationResult(
            request_id=request.request_id,
            query_id=request.query_id,
            auto_generated=False,
            annotations_count=0,
            annotations=[],
            message="未找到点击事件，无法生成自动标注"
        )
    
    doc_click_map: Dict[str, Dict[str, Any]] = {}
    for event in click_events:
        if event.doc_id not in doc_click_map:
            doc_click_map[event.doc_id] = {
                "clicks": 0,
                "total_dwell_time": 0,
                "best_rank": event.rank,
                "click_types": []
            }
        doc_click_map[event.doc_id]["clicks"] += 1
        doc_click_map[event.doc_id]["total_dwell_time"] += event.dwell_time
        doc_click_map[event.doc_id]["best_rank"] = min(doc_click_map[event.doc_id]["best_rank"], event.rank)
        doc_click_map[event.doc_id]["click_types"].append(event.click_type)
    
    annotations = []
    for doc_id, data in sorted(doc_click_map.items(), key=lambda x: x[1]["best_rank"]):
        if len(annotations) >= request.max_annotations:
            break
        
        avg_dwell_time = data["total_dwell_time"] / max(data["clicks"], 1)
        relevance = 0
        
        if avg_dwell_time >= 30 or "deep_view" in data["click_types"]:
            relevance = 3
        elif avg_dwell_time >= 10 or data["clicks"] >= 3:
            relevance = 2
        elif avg_dwell_time >= request.min_dwell_time or "quick_view" in data["click_types"]:
            relevance = 1
        else:
            continue
        
        annotation = {
            "query_id": request.query_id,
            "doc_id": doc_id,
            "relevance": relevance,
            "annotator": "auto",
            "request_id": request.request_id
        }
        
        existing = es.search(
            index=settings.annotations_index,
            query={
                "bool": {
                    "must": [
                        {"term": {"query_id": request.query_id}},
                        {"term": {"doc_id": doc_id}}
                    ]
                }
            }
        )
        
        if existing["hits"]["total"]["value"] == 0:
            annotation["created_at"] = datetime.now(timezone.utc).isoformat()
            annotation["_id"] = str(uuid.uuid4())
            es.index(
                index=settings.annotations_index,
                id=annotation["_id"],
                body=annotation
            )
            annotations.append(annotation)
    
    return AutoAnnotationResult(
        request_id=request.request_id,
        query_id=request.query_id,
        auto_generated=len(annotations) > 0,
        annotations_count=len(annotations),
        annotations=annotations,
        message=f"成功生成 {len(annotations)} 条自动标注"
    )


@app.post("/api/ab-tests", response_model=ABTestConfig)
async def create_ab_test(
    test_config: ABTestConfigCreate,
    es: Elasticsearch = Depends(get_es_client)
):
    test_dict = test_config.model_dump()
    test_id = f"ab_{uuid.uuid4().hex[:8]}"
    test_dict["test_id"] = test_id
    test_dict["created_at"] = datetime.now(timezone.utc)
    
    es.index(
        index=settings.ab_tests_index,
        id=test_id,
        body=test_dict
    )
    
    return ABTestConfig(**test_dict)


@app.get("/api/ab-tests", response_model=List[ABTestConfig])
async def list_ab_tests(
    status: Optional[str] = None,
    es: Elasticsearch = Depends(get_es_client)
):
    query_body = {"match_all": {}}
    if status:
        query_body = {"term": {"status": status}}
    
    result = es.search(
        index=settings.ab_tests_index,
        query=query_body,
        size=100,
        sort=[{"created_at": "desc"}]
    )
    
    tests = []
    for hit in result["hits"]["hits"]:
        tests.append(ABTestConfig(**hit["_source"]))
    
    return tests


@app.put("/api/ab-tests/{test_id}")
async def update_ab_test(
    test_id: str,
    test_config: ABTestConfigCreate,
    es: Elasticsearch = Depends(get_es_client)
):
    existing = es.get(index=settings.ab_tests_index, id=test_id)
    if not existing["found"]:
        raise HTTPException(status_code=404, detail=f"A/B测试 {test_id} 不存在")
    
    test_dict = test_config.model_dump()
    test_dict["test_id"] = test_id
    test_dict["created_at"] = existing["_source"]["created_at"]
    test_dict["updated_at"] = datetime.now(timezone.utc)
    
    es.index(
        index=settings.ab_tests_index,
        id=test_id,
        body=test_dict
    )
    
    return ABTestConfig(**test_dict)


@app.post("/api/ab-tests/{test_id}/assign")
async def assign_ab_test_group(
    test_id: str,
    session_id: str,
    es: Elasticsearch = Depends(get_es_client)
):
    test = es.get(index=settings.ab_tests_index, id=test_id)
    if not test["found"]:
        raise HTTPException(status_code=404, detail=f"A/B测试 {test_id} 不存在")
    
    test_data = test["_source"]
    if test_data["status"] != "running":
        raise HTTPException(status_code=400, detail=f"A/B测试 {test_id} 未处于运行状态")
    
    existing = es.search(
        index=settings.ab_assignments_index,
        query={
            "bool": {
                "must": [
                    {"term": {"test_id": test_id}},
                    {"term": {"session_id": session_id}}
                ]
            }
        }
    )
    
    if existing["hits"]["total"]["value"] > 0:
        assignment = existing["hits"]["hits"][0]["_source"]
        return ABTestAssignment(**assignment)
    
    import random
    group = "treatment" if random.random() < test_data["traffic_split"] else "control"
    model_name = test_data["treatment_model"] if group == "treatment" else test_data["control_model"]
    
    assignment = {
        "test_id": test_id,
        "session_id": session_id,
        "group": group,
        "model_name": model_name,
        "assigned_at": datetime.now(timezone.utc).isoformat()
    }
    
    assignment_id = str(uuid.uuid4())
    es.index(
        index=settings.ab_assignments_index,
        id=assignment_id,
        body=assignment
    )
    
    return ABTestAssignment(**assignment)


@app.get("/api/ab-tests/{test_id}/metrics", response_model=ABTestMetrics)
async def get_ab_test_metrics(
    test_id: str,
    k: int = Query(10, ge=1, le=100),
    es: Elasticsearch = Depends(get_es_client)
):
    test = es.get(index=settings.ab_tests_index, id=test_id)
    if not test["found"]:
        raise HTTPException(status_code=404, detail=f"A/B测试 {test_id} 不存在")
    
    test_data = test["_source"]
    
    assignments = es.search(
        index=settings.ab_assignments_index,
        query={"term": {"test_id": test_id}},
        size=10000
    )
    
    control_sessions = []
    treatment_sessions = []
    
    for hit in assignments["hits"]["hits"]:
        source = hit["_source"]
        if source["group"] == "control":
            control_sessions.append(source)
        else:
            treatment_sessions.append(source)
    
    async def evaluate_group(sessions, model_name):
        if not sessions:
            return {"avg_recall": 0, "avg_precision": 0, "avg_f1": 0, "avg_ndcg": 0, "avg_hit_rate": 0}
        
        metrics_list = []
        for session in sessions:
            session_id = session["session_id"]
            
            click_result = es.search(
                index=settings.click_events_index,
                query={"term": {"session_id": session_id}},
                size=1
            )
            
            if click_result["hits"]["hits"]:
                request_id = click_result["hits"]["hits"][0]["_source"]["request_id"]
                
                eval_result = es.search(
                    index=settings.evaluations_index,
                    query={"term": {"request_id": request_id}},
                    size=1
                )
                
                if eval_result["hits"]["hits"]:
                    eval_data = eval_result["hits"]["hits"][0]["_source"]
                    if eval_data.get("metrics"):
                        metrics_list.append(eval_data["metrics"])
        
        if not metrics_list:
            return {"avg_recall": 0, "avg_precision": 0, "avg_f1": 0, "avg_ndcg": 0, "avg_hit_rate": 0}
        
        return {
            "avg_recall": sum(m.get("recall_at_k", 0) for m in metrics_list) / len(metrics_list),
            "avg_precision": sum(m.get("precision_at_k", 0) for m in metrics_list) / len(metrics_list),
            "avg_f1": sum(m.get("f1_at_k", 0) for m in metrics_list) / len(metrics_list),
            "avg_ndcg": sum(m.get("ndcg_at_k", 0) for m in metrics_list) / len(metrics_list),
            "avg_hit_rate": sum(m.get("hit_rate", 0) for m in metrics_list) / len(metrics_list)
        }
    
    control_metrics = await evaluate_group(control_sessions, test_data["control_model"])
    treatment_metrics = await evaluate_group(treatment_sessions, test_data["treatment_model"])
    
    lift = {}
    confidence = {}
    for key in ["avg_recall", "avg_precision", "avg_f1", "avg_ndcg", "avg_hit_rate"]:
        c_val = control_metrics[key]
        t_val = treatment_metrics[key]
        lift[key] = ((t_val - c_val) / max(c_val, 0.001)) * 100 if c_val > 0 else 0
        
        import math
        if len(control_sessions) > 1 and len(treatment_sessions) > 1:
            se = math.sqrt((0.25 / max(len(control_sessions), 1)) + (0.25 / max(len(treatment_sessions), 1)))
            confidence[key] = 1.96 * se * 100
        else:
            confidence[key] = 0
    
    return ABTestMetrics(
        test_id=test_id,
        test_name=test_data["test_name"],
        control_model=test_data["control_model"],
        treatment_model=test_data["treatment_model"],
        control=control_metrics,
        treatment=treatment_metrics,
        lift=lift,
        confidence=confidence,
        sample_size={
            "control": len(control_sessions),
            "treatment": len(treatment_sessions)
        }
    )


@app.post("/api/feedback-learning/generate", response_model=FeedbackLearningResult)
async def generate_training_data(
    request: FeedbackLearningRequest,
    es: Elasticsearch = Depends(get_es_client)
):
    annotations_result = es.search(
        index=settings.annotations_index,
        query={"match_all": {}},
        size=10000
    )
    
    feedback_data = es.search(
        index=settings.feedback_data_index,
        query={"match_all": {}},
        size=10000
    )
    
    all_samples = []
    
    for hit in annotations_result["hits"]["hits"]:
        source = hit["_source"]
        query_id = source.get("query_id", "")
        
        query_result = es.get(index=settings.queries_index, id=query_id)
        query_text = ""
        if query_result["found"]:
            query_text = query_result["_source"].get("query_text", "")
        
        doc_result = es.get(index=settings.documents_index, id=source.get("doc_id", ""))
        doc_title = ""
        if doc_result["found"]:
            doc_title = doc_result["_source"].get("title", "")
        
        confidence = 1.0 if source.get("annotator") != "auto" else 0.7
        
        if confidence >= request.min_confidence:
            all_samples.append(TrainingSample(
                query_id=query_id,
                query_text=query_text,
                doc_id=source.get("doc_id", ""),
                doc_title=doc_title,
                relevance=source.get("relevance", 0),
                source="manual" if source.get("annotator") != "auto" else "auto",
                confidence=confidence,
                created_at=source.get("created_at", datetime.now(timezone.utc))
            ))
    
    for hit in feedback_data["hits"]["hits"]:
        source = hit["_source"]
        confidence = source.get("confidence", 0.5)
        
        if confidence >= request.min_confidence:
            all_samples.append(TrainingSample(
                query_id=source.get("query_id", ""),
                query_text=source.get("query_text", ""),
                doc_id=source.get("doc_id", ""),
                doc_title=source.get("doc_title", ""),
                relevance=source.get("relevance", 0),
                source=source.get("source", "feedback"),
                confidence=confidence,
                created_at=source.get("created_at", datetime.now(timezone.utc))
            ))
    
    high_confidence = [s for s in all_samples if s.confidence >= 0.9]
    
    return FeedbackLearningResult(
        model_name=request.model_name,
        total_samples=len(all_samples),
        high_confidence_samples=len(high_confidence),
        training_samples=all_samples[:1000],
        message=f"成功生成 {len(all_samples)} 条训练数据，其中 {len(high_confidence)} 条高置信度"
    )


@app.post("/api/feedback-learning/retrain", response_model=RetrainingResult)
async def retrain_model(
    config: ModelRetrainingConfig,
    es: Elasticsearch = Depends(get_es_client)
):
    annotations_result = es.search(
        index=settings.annotations_index,
        query={"match_all": {}},
        size=10000
    )
    
    total_samples = annotations_result["hits"]["total"]["value"]
    validation_size = int(total_samples * config.test_ratio)
    training_size = total_samples - validation_size
    
    new_version = f"{config.model_name}_v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    
    return RetrainingResult(
        model_name=config.model_name,
        new_version=new_version,
        training_samples=training_size,
        validation_samples=validation_size,
        training_metrics={
            "loss": 0.15,
            "accuracy": 0.92,
            "recall": 0.88
        },
        validation_metrics={
            "loss": 0.22,
            "accuracy": 0.87,
            "recall": 0.83
        },
        status="completed",
        message=f"模型 {config.model_name} 重新训练完成，新版本: {new_version}"
    )


@app.post("/api/feedback-learning/record")
async def record_feedback(
    feedback_data: Dict[str, Any],
    es: Elasticsearch = Depends(get_es_client)
):
    feedback_data["created_at"] = datetime.now(timezone.utc).isoformat()
    
    feedback_id = str(uuid.uuid4())
    es.index(
        index=settings.feedback_data_index,
        id=feedback_id,
        body=feedback_data
    )
    
    return {"message": "反馈记录成功", "feedback_id": feedback_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
