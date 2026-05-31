from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import List, Optional, Dict
import logging

from ..models.schemas import (
    Paper, GraphData, GraphBuildRequest, InfluenceMetrics,
    TrendData, KeywordTrend, ApiResponse, SourceType, RankingMetric,
    SubGraphRequest, SubGraphData, MultiGranularClusters, HierarchicalGraphData,
    PaperRecommendations, CollaborationNetwork, BatchCitationPrediction, CitationPrediction
)
from ..services.data_service import DataService
from ..services.graph_analyzer import GraphAnalyzer
from ..services.neo4j_service import Neo4jService
from ..services.cache_service import CacheService
from ..services.insight_service import PaperRecommender, CollaboratorFinder, CitationPredictor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["citation-network"])

_data_service: Optional[DataService] = None
_graph_analyzer: Optional[GraphAnalyzer] = None
_neo4j_service: Optional[Neo4jService] = None
_cache_service: Optional[CacheService] = None


def get_data_service() -> DataService:
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service


def get_graph_analyzer() -> GraphAnalyzer:
    global _graph_analyzer
    if _graph_analyzer is None:
        _graph_analyzer = GraphAnalyzer()
    return _graph_analyzer


def get_neo4j_service() -> Neo4jService:
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
    return _neo4j_service


def get_cache_service() -> CacheService:
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


@router.get("/search", response_model=ApiResponse[List[Paper]])
async def search_papers(
    q: str = Query(..., description="搜索关键词"),
    source: SourceType = Query(SourceType.CROSSREF, description="数据源"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    data_service: DataService = Depends(get_data_service),
    cache_service: CacheService = Depends(get_cache_service)
):
    try:
        cache_key = f"{source.value}:{q.lower()}:{limit}"
        cached = cache_service.get_search(q, source.value)
        if cached:
            return ApiResponse(success=True, data=cached, message="从缓存返回")

        papers = await data_service.search_papers(q, source, limit)

        paper_dicts = [p.model_dump() for p in papers]
        cache_service.set_search(q, source.value, paper_dicts)

        return ApiResponse(
            success=True,
            data=papers,
            message=f"找到 {len(papers)} 篇论文"
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paper/{doi:path}", response_model=ApiResponse[Paper])
async def get_paper(
    doi: str,
    data_service: DataService = Depends(get_data_service),
    cache_service: CacheService = Depends(get_cache_service)
):
    try:
        cached = cache_service.get_paper(doi)
        if cached:
            return ApiResponse(success=True, data=cached, message="从缓存返回")

        paper = await data_service.get_paper(doi)
        if not paper:
            raise HTTPException(status_code=404, detail=f"未找到DOI为 {doi} 的论文")

        cache_service.set_paper(doi, paper.model_dump())

        return ApiResponse(success=True, data=paper)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get paper error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paper/{doi:path}/references", response_model=ApiResponse[List[Paper]])
async def get_paper_references(
    doi: str,
    data_service: DataService = Depends(get_data_service)
):
    try:
        ref_dois = await data_service.get_references(doi)
        papers = await data_service.get_papers(ref_dois[:50])
        return ApiResponse(
            success=True,
            data=papers,
            message=f"找到 {len(papers)} 篇参考文献"
        )
    except Exception as e:
        logger.error(f"Get references error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paper/{doi:path}/citations", response_model=ApiResponse[List[Paper]])
async def get_paper_citations(
    doi: str,
    data_service: DataService = Depends(get_data_service)
):
    try:
        cit_dois = await data_service.get_citations(doi)
        papers = await data_service.get_papers(cit_dois[:50])
        return ApiResponse(
            success=True,
            data=papers,
            message=f"找到 {len(papers)} 篇引用文献"
        )
    except Exception as e:
        logger.error(f"Get citations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/build", response_model=ApiResponse[GraphData])
async def build_graph(
    request: GraphBuildRequest,
    data_service: DataService = Depends(get_data_service),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer),
    neo4j_service: Neo4jService = Depends(get_neo4j_service),
    cache_service: CacheService = Depends(get_cache_service)
):
    try:
        network_data = await data_service.build_citation_network(
            seed_dois=request.dois,
            depth=request.depth,
            max_nodes=request.max_nodes
        )

        if not network_data["papers"]:
            raise HTTPException(status_code=400, detail="无法构建网络，请检查输入的DOI")

        graph_analyzer.build_graph(network_data["papers"], network_data["edges"])
        graph_data = graph_analyzer.export_graph_data()

        neo4j_service.save_graph(graph_data)
        cache_service.set_graph(graph_data.graph_id, graph_data.model_dump())

        return ApiResponse(
            success=True,
            data=graph_data,
            message=f"网络构建完成：{graph_data.stats.total_nodes} 个节点，{graph_data.stats.total_edges} 条边"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Build graph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/{graph_id}", response_model=ApiResponse[GraphData])
async def get_graph(
    graph_id: str,
    cache_service: CacheService = Depends(get_cache_service)
):
    try:
        graph_data = cache_service.get_graph(graph_id)
        if not graph_data:
            raise HTTPException(status_code=404, detail=f"未找到ID为 {graph_id} 的图数据")

        return ApiResponse(success=True, data=graph_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get graph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/influence/ranking", response_model=ApiResponse[List[InfluenceMetrics]])
async def get_influence_ranking(
    metric: RankingMetric = Query(RankingMetric.PAGERANK, description="排序指标"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer),
    neo4j_service: Neo4jService = Depends(get_neo4j_service)
):
    try:
        if graph_analyzer.graph.number_of_nodes() > 0:
            rankings = graph_analyzer.compute_influence_rankings()
            if metric == RankingMetric.PAGERANK:
                rankings.sort(key=lambda x: x.pagerank_rank)
            elif metric == RankingMetric.H_INDEX:
                rankings.sort(key=lambda x: x.h_index_rank)
            elif metric == RankingMetric.CITATIONS:
                rankings.sort(key=lambda x: x.citations_rank)
            rankings = rankings[:limit]
        else:
            rankings = neo4j_service.get_influence_rankings(metric.value, limit)

        return ApiResponse(
            success=True,
            data=rankings,
            message=f"按 {metric.value} 排名的前 {len(rankings)} 篇论文"
        )
    except Exception as e:
        logger.error(f"Get influence ranking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/influence/core-papers", response_model=ApiResponse[List[InfluenceMetrics]])
async def get_core_papers(
    method: str = Query("pagerank", description="核心论文发现方法"),
    threshold: float = Query(0.1, ge=0.01, le=0.5, description="核心阈值"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer)
):
    try:
        if graph_analyzer.graph.number_of_nodes() == 0:
            raise HTTPException(status_code=400, detail="请先构建引用网络")

        core_papers = graph_analyzer.get_core_papers(method, limit)

        return ApiResponse(
            success=True,
            data=core_papers,
            message=f"发现 {len(core_papers)} 篇核心论文"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get core papers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/over-time", response_model=ApiResponse[List[TrendData]])
async def get_trends_over_time(
    keywords: Optional[str] = Query(None, description="关键词，用逗号分隔"),
    start_year: int = Query(2010, ge=1990, le=2025, description="起始年份"),
    end_year: int = Query(2025, ge=1990, le=2025, description="结束年份"),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer),
    neo4j_service: Neo4jService = Depends(get_neo4j_service)
):
    try:
        if graph_analyzer.graph.number_of_nodes() > 0:
            trends = graph_analyzer.analyze_trends(start_year, end_year)
        else:
            raw_trends = neo4j_service.get_trend_data(start_year, end_year)
            trends = [
                TrendData(
                    year=t['year'],
                    paper_count=t['paper_count'],
                    citation_count=t['citation_count'],
                    avg_citations=t['citation_count'] / t['paper_count'] if t['paper_count'] > 0 else 0
                )
                for t in raw_trends
            ]

        return ApiResponse(
            success=True,
            data=trends,
            message=f"时间趋势分析：{start_year}-{end_year}"
        )
    except Exception as e:
        logger.error(f"Get trends over time error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/keywords", response_model=ApiResponse[List[KeywordTrend]])
async def get_keyword_trends(
    limit: int = Query(30, ge=10, le=100, description="返回关键词数量"),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer)
):
    try:
        if graph_analyzer.graph.number_of_nodes() == 0:
            raise HTTPException(status_code=400, detail="请先构建引用网络")

        keyword_trends = graph_analyzer.extract_keyword_trends(limit)

        return ApiResponse(
            success=True,
            data=keyword_trends,
            message=f"提取了 {len(keyword_trends)} 个关键词趋势"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get keyword trends error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/subgraph", response_model=ApiResponse[SubGraphData])
async def get_subgraph(
    request: SubGraphRequest,
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer)
):
    try:
        if graph_analyzer.graph.number_of_nodes() == 0:
            raise HTTPException(status_code=400, detail="请先构建引用网络")

        subgraph_data = graph_analyzer.get_subgraph(
            node_id=request.node_id,
            max_depth=request.max_depth,
            max_nodes=request.max_nodes
        )

        return ApiResponse(
            success=True,
            data=subgraph_data,
            message=f"子图查询完成：{len(subgraph_data.nodes)} 个节点，{len(subgraph_data.edges)} 条边"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get subgraph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/hierarchical", response_model=ApiResponse[HierarchicalGraphData])
async def get_hierarchical_graph(
    include_hierarchy: bool = Query(True, description="是否包含层次聚类信息"),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer),
    data_service: DataService = Depends(get_data_service),
    neo4j_service: Neo4jService = Depends(get_neo4j_service),
    cache_service: CacheService = Depends(get_cache_service)
):
    try:
        if graph_analyzer.graph.number_of_nodes() == 0:
            raise HTTPException(status_code=400, detail="请先构建引用网络")

        graph_data = graph_analyzer.export_graph_data(include_hierarchy=include_hierarchy)

        return ApiResponse(
            success=True,
            data=graph_data,
            message=f"分层图数据：{graph_data.stats.total_nodes} 个节点，{graph_data.stats.total_edges} 条边"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get hierarchical graph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/clusters", response_model=ApiResponse[MultiGranularClusters])
async def get_clusters(
    num_levels: int = Query(3, ge=1, le=5, description="聚类粒度层级数"),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer)
):
    try:
        if graph_analyzer.graph.number_of_nodes() == 0:
            raise HTTPException(status_code=400, detail="请先构建引用网络")

        hierarchy = graph_analyzer.detect_hierarchical_communities(num_levels=num_levels)

        return ApiResponse(
            success=True,
            data=hierarchy,
            message=f"多粒度聚类完成：{hierarchy.levels} 个层级"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get clusters error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/cluster/{level}/{cluster_id}/papers", response_model=ApiResponse[List[InfluenceMetrics]])
async def get_cluster_papers(
    level: int,
    cluster_id: int,
    limit: int = Query(20, ge=1, le=100, description="返回论文数量限制"),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer)
):
    try:
        if graph_analyzer.graph.number_of_nodes() == 0:
            raise HTTPException(status_code=400, detail="请先构建引用网络")

        hierarchy = graph_analyzer.detect_hierarchical_communities()
        core_papers_by_comm = graph_analyzer.get_core_papers_by_community(
            hierarchy, level=level, limit_per_community=limit
        )

        cluster_papers = core_papers_by_comm.get(cluster_id, [])

        return ApiResponse(
            success=True,
            data=cluster_papers,
            message=f"聚类 L{level}-{cluster_id} 包含 {len(cluster_papers)} 篇核心论文"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get cluster papers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pagerank/benchmark", response_model=ApiResponse[Dict[str, float]])
async def benchmark_pagerank(
    use_sparse: bool = Query(True, description="是否使用稀疏矩阵算法"),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer)
):
    import time

    try:
        if graph_analyzer.graph.number_of_nodes() == 0:
            raise HTTPException(status_code=400, detail="请先构建引用网络")

        start_time = time.time()
        graph_analyzer.compute_pagerank(use_sparse=use_sparse)
        elapsed = time.time() - start_time

        return ApiResponse(
            success=True,
            data={
                "sparse_algorithm": use_sparse,
                "execution_time_ms": elapsed * 1000,
                "node_count": graph_analyzer.graph.number_of_nodes(),
                "edge_count": graph_analyzer.graph.number_of_edges()
            },
            message=f"PageRank 计算耗时：{elapsed * 1000:.2f}ms"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Benchmark pagerank error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    return ApiResponse(success=True, message="服务运行正常", data={"status": "healthy"})


@router.get("/recommendations/{doi:path}", response_model=ApiResponse[PaperRecommendations])
async def get_paper_recommendations(
    doi: str,
    limit: int = Query(20, ge=1, le=50, description="推荐数量限制"),
    method: str = Query("hybrid", description="推荐方法: citation, content, hybrid"),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer),
    data_service: DataService = Depends(get_data_service)
):
    try:
        if graph_analyzer.graph.number_of_nodes() == 0:
            raise HTTPException(status_code=400, detail="请先构建引用网络")

        papers_by_doi = {p.doi: p for p in graph_analyzer.papers.values()}

        recommender = PaperRecommender(graph_analyzer.graph, papers_by_doi)
        recommendations = recommender.recommend(doi, limit=limit, method=method)

        return ApiResponse(
            success=True,
            data=recommendations,
            message=f"为论文 {doi} 找到 {len(recommendations.recommendations)} 篇推荐论文"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collaborators/{author_name}", response_model=ApiResponse[CollaborationNetwork])
async def get_collaborators(
    author_name: str,
    limit: int = Query(20, ge=1, le=50, description="合作者数量限制"),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer)
):
    try:
        if graph_analyzer.graph.number_of_nodes() == 0:
            raise HTTPException(status_code=400, detail="请先构建引用网络")

        papers_by_doi = {p.doi: p for p in graph_analyzer.papers.values()}

        finder = CollaboratorFinder(graph_analyzer.graph, papers_by_doi)
        collab_network = finder.find_collaborators(author_name, limit=limit)

        return ApiResponse(
            success=True,
            data=collab_network,
            message=f"为作者 {author_name} 找到 {len(collab_network.potential_collaborators)} 位潜在合作者"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get collaborators error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prediction/citations/{doi:path}", response_model=ApiResponse[CitationPrediction])
async def get_citation_prediction(
    doi: str,
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer)
):
    try:
        if graph_analyzer.graph.number_of_nodes() == 0:
            raise HTTPException(status_code=400, detail="请先构建引用网络")

        papers_by_doi = {p.doi: p for p in graph_analyzer.papers.values()}

        predictor = CitationPredictor(graph_analyzer.graph, papers_by_doi)
        prediction = predictor.predict(doi)

        if not prediction:
            raise HTTPException(status_code=404, detail=f"未找到DOI为 {doi} 的论文")

        return ApiResponse(
            success=True,
            data=prediction,
            message=f"论文 {doi} 的引用预测完成"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get citation prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prediction/citations/batch", response_model=ApiResponse[BatchCitationPrediction])
async def get_batch_citation_prediction(
    dois: List[str] = Body(..., embed=True, description="论文DOI列表"),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer)
):
    try:
        if graph_analyzer.graph.number_of_nodes() == 0:
            raise HTTPException(status_code=400, detail="请先构建引用网络")

        papers_by_doi = {p.doi: p for p in graph_analyzer.papers.values()}

        predictor = CitationPredictor(graph_analyzer.graph, papers_by_doi)
        predictions = predictor.predict_batch(dois)

        return ApiResponse(
            success=True,
            data=predictions,
            message=f"批量预测完成：{len(predictions.predictions)} 篇论文"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch citation prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prediction/trending", response_model=ApiResponse[List[CitationPrediction]])
async def get_trending_papers(
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    graph_analyzer: GraphAnalyzer = Depends(get_graph_analyzer)
):
    try:
        if graph_analyzer.graph.number_of_nodes() == 0:
            raise HTTPException(status_code=400, detail="请先构建引用网络")

        papers_by_doi = {p.doi: p for p in graph_analyzer.papers.values()}
        dois = list(papers_by_doi.keys())

        predictor = CitationPredictor(graph_analyzer.graph, papers_by_doi)
        predictions = predictor.predict_batch(dois)

        trending = sorted(
            predictions.predictions,
            key=lambda x: x.growth_rate,
            reverse=True
        )[:limit]

        return ApiResponse(
            success=True,
            data=trending,
            message=f"找到 {len(trending)} 篇高增长趋势论文"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get trending papers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
