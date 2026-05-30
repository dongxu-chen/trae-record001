import logging
from typing import Dict, List, Any
from celery import group
from celery_config import app
from redis_connection import RedisConnectionManager
from memory_analyzer import MemoryAnalyzer, NodeInfo
from memory_defrag import MemoryDefragmenter, DefragMethod
from statistics_analyzer import StatisticsAnalyzer
from fragmentation_predictor import (
    FragmentationPredictor, 
    CostBenefitAnalyzer,
    FragmentationPrediction,
    CostBenefitAnalysis
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def check_fragmentation(self) -> Dict[str, Any]:
    try:
        logger.info("Starting fragmentation check task")
        connection_manager = RedisConnectionManager()
        analyzer = MemoryAnalyzer(connection_manager)
        stats_analyzer = StatisticsAnalyzer()
        
        all_memory_info = analyzer.get_all_memory_info()
        
        for mem_info in all_memory_info:
            stats_analyzer.store_memory_snapshot(mem_info)
        
        summary = analyzer.get_cluster_fragmentation_summary()
        
        logger.info(
            f"Fragmentation check completed: {summary.get('node_count', 0)} nodes, "
            f"avg fragmentation: {summary.get('avg_fragmentation_ratio', 0):.2f}"
        )
        
        return {
            'status': 'success',
            'summary': summary,
            'nodes_checked': len(all_memory_info)
        }
    except Exception as e:
        logger.error(f"Fragmentation check failed: {e}")
        raise self.retry(exc=e)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def check_redis_versions(self) -> Dict[str, Any]:
    try:
        logger.info("Starting Redis version check task")
        connection_manager = RedisConnectionManager()
        analyzer = MemoryAnalyzer(connection_manager)
        defragmenter = MemoryDefragmenter(connection_manager)
        
        nodes = connection_manager.get_all_nodes()
        node_info_list = []
        
        for node in nodes:
            try:
                node_info = analyzer.get_node_info(node)
                defrag_method = defragmenter.determine_defrag_method(node_info)
                node_info_list.append({
                    'node_id': node_info.node_id,
                    'host': node_info.host,
                    'port': node_info.port,
                    'role': node_info.role,
                    'version': str(node_info.version),
                    'mem_allocator': node_info.mem_allocator,
                    'supports_purge': node_info.supports_memory_purge(),
                    'defrag_method': defrag_method.value
                })
            except Exception as e:
                logger.error(f"Failed to get info for node {node['host']}:{node['port']}: {e}")
        
        logger.info(f"Version check completed for {len(node_info_list)} nodes")
        
        return {
            'status': 'success',
            'nodes': node_info_list
        }
    except Exception as e:
        logger.error(f"Redis version check failed: {e}")
        raise self.retry(exc=e)


@app.task(bind=True, max_retries=2, default_retry_delay=120)
def defrag_node(self, node_id: str) -> Dict[str, Any]:
    try:
        logger.info(f"Starting defrag task for node {node_id}")
        connection_manager = RedisConnectionManager()
        defragmenter = MemoryDefragmenter(connection_manager, parallel=False)
        stats_analyzer = StatisticsAnalyzer()
        
        result = defragmenter.defrag_node(node_id)
        stats_analyzer.store_defrag_result(result)
        
        if result.success:
            logger.info(
                f"Defrag successful for node {node_id}: "
                f"saved {result.memory_saved_mb:.2f}MB, "
                f"improved by {result.fragmentation_improvement:.2f}, "
                f"P99 change: {result.performance_impact.p99_latency_increase_ms:+.2f}ms"
            )
        else:
            logger.error(f"Defrag failed for node {node_id}: {result.error_message}")
        
        return {
            'status': 'success' if result.success else 'failed',
            'node_id': node_id,
            'result': result.to_dict()
        }
    except Exception as e:
        logger.error(f"Defrag task failed for node {node_id}: {e}")
        raise self.retry(exc=e)


@app.task(bind=True)
def defrag_nodes_parallel(self, node_ids: List[str], max_workers: int = 4) -> Dict[str, Any]:
    try:
        logger.info(f"Starting parallel defrag for {len(node_ids)} nodes")
        
        job = group(defrag_node.s(node_id) for node_id in node_ids)
        result = job.apply_async()
        results = result.get(timeout=1800)
        
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = len(results) - successful
        
        total_saved = sum(
            r['result'].get('memory_saved_mb', 0) 
            for r in results if r['status'] == 'success'
        )
        
        avg_p99_increase = sum(
            r['result'].get('performance_impact', {}).get('p99_latency_increase_ms', 0)
            for r in results if r['status'] == 'success'
        ) / successful if successful > 0 else 0
        
        logger.info(
            f"Parallel defrag completed: {successful}/{len(node_ids)} successful, "
            f"saved {total_saved:.2f}MB total"
        )
        
        return {
            'status': 'success',
            'total_nodes': len(node_ids),
            'successful': successful,
            'failed': failed,
            'total_memory_saved_mb': total_saved,
            'avg_p99_latency_increase_ms': avg_p99_increase,
            'results': results
        }
    except Exception as e:
        logger.error(f"Parallel defrag failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@app.task(bind=True)
def defrag_high_fragmentation_nodes(self, threshold: float = None, 
                                     min_memory_mb: float = None,
                                     parallel: bool = True,
                                     max_workers: int = 4) -> Dict[str, Any]:
    try:
        logger.info("Starting defrag for high fragmentation nodes")
        connection_manager = RedisConnectionManager()
        analyzer = MemoryAnalyzer(connection_manager)
        
        high_frag_nodes = analyzer.get_high_fragmentation_nodes()
        
        if not high_frag_nodes:
            logger.info("No nodes with high fragmentation found")
            return {
                'status': 'success',
                'message': 'No high fragmentation nodes found',
                'nodes_processed': 0
            }

        node_ids = [m.node_id for m in high_frag_nodes]
        logger.info(f"Found {len(node_ids)} nodes with high fragmentation")
        
        if parallel and len(node_ids) > 1:
            return defrag_nodes_parallel(node_ids, max_workers)
        else:
            defragmenter = MemoryDefragmenter(connection_manager, parallel=False)
            stats_analyzer = StatisticsAnalyzer()
            
            results = []
            for mem_info in high_frag_nodes:
                try:
                    result = defragmenter.defrag_node(mem_info.node_id)
                    stats_analyzer.store_defrag_result(result)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to defrag node {mem_info.node_id}: {e}")
            
            summary = defragmenter.get_defrag_summary(results)
            
            return {
                'status': 'success',
                'summary': summary
            }
    except Exception as e:
        logger.error(f"Defrag for high fragmentation nodes failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@app.task
def periodic_defrag_check(parallel: bool = True, max_workers: int = 4) -> Dict[str, Any]:
    logger.info("Starting periodic defrag check")
    
    check_result = check_fragmentation.delay()
    check_result.wait(timeout=300)
    
    defrag_result = defrag_high_fragmentation_nodes.apply_async(
        kwargs={'parallel': parallel, 'max_workers': max_workers}
    )
    defrag_result.wait(timeout=1800)
    
    return {
        'status': 'completed',
        'check_task_id': check_result.id,
        'defrag_task_id': defrag_result.id
    }


@app.task
def daily_fragmentation_report() -> Dict[str, Any]:
    try:
        logger.info("Generating daily fragmentation report")
        connection_manager = RedisConnectionManager()
        analyzer = MemoryAnalyzer(connection_manager)
        stats_analyzer = StatisticsAnalyzer()
        
        all_memory_info = analyzer.get_all_memory_info()
        node_ids = [m.node_id for m in all_memory_info]
        
        report = stats_analyzer.generate_daily_report(node_ids)
        
        logger.info(
            f"Daily report generated: {report['cluster_summary'].get('node_count', 0)} nodes, "
            f"{len(report['high_risk_nodes'])} high risk nodes"
        )
        
        for rec in report['recommendations']:
            logger.info(f"Recommendation: {rec}")
        
        return {
            'status': 'success',
            'report': report
        }
    except Exception as e:
        logger.error(f"Daily report generation failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@app.task
def get_cluster_statistics(hours: int = 24) -> Dict[str, Any]:
    try:
        connection_manager = RedisConnectionManager()
        analyzer = MemoryAnalyzer(connection_manager)
        stats_analyzer = StatisticsAnalyzer()
        
        all_memory_info = analyzer.get_all_memory_info()
        node_ids = [m.node_id for m in all_memory_info]
        
        stats = stats_analyzer.get_cluster_statistics(node_ids, hours)
        
        return {'status': 'success', 'statistics': stats}
    except Exception as e:
        logger.error(f"Get cluster statistics failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@app.task
def manual_defrag_all() -> Dict[str, Any]:
    try:
        logger.info("Starting manual defrag for all nodes")
        connection_manager = RedisConnectionManager()
        defragmenter = MemoryDefragmenter(connection_manager)
        stats_analyzer = StatisticsAnalyzer()
        
        results = defragmenter.defrag_all_nodes()
        
        for result in results:
            stats_analyzer.store_defrag_result(result)
        
        summary = defragmenter.get_defrag_summary(results)
        
        return {'status': 'success', 'summary': summary}
    except Exception as e:
        logger.error(f"Manual defrag all failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@app.task
def get_defrag_history(node_id: str = None, limit: int = 50) -> Dict[str, Any]:
    try:
        stats_analyzer = StatisticsAnalyzer()
        history = stats_analyzer.get_defrag_history(node_id, limit)
        
        return {'status': 'success', 'history': history}
    except Exception as e:
        logger.error(f"Get defrag history failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@app.task
def get_defrag_effectiveness(node_id: str = None, limit: int = 20) -> Dict[str, Any]:
    try:
        stats_analyzer = StatisticsAnalyzer()
        effectiveness = stats_analyzer.get_defrag_effectiveness(node_id, limit)
        
        return {'status': 'success', 'effectiveness': effectiveness}
    except Exception as e:
        logger.error(f"Get defrag effectiveness failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@app.task(bind=True)
def analyze_fragmentation_causes_task(self) -> Dict[str, Any]:
    try:
        logger.info("Starting fragmentation cause analysis task")
        connection_manager = RedisConnectionManager()
        analyzer = MemoryAnalyzer(connection_manager)
        
        analyses = analyzer.analyze_all_fragmentation_causes()
        
        results = []
        for analysis in analyses:
            results.append(analysis.to_dict())
        
        logger.info(f"Fragmentation cause analysis completed: {len(results)} nodes analyzed")
        
        return {
            'status': 'success',
            'nodes_analyzed': len(results),
            'analyses': results
        }
    except Exception as e:
        logger.error(f"Fragmentation cause analysis failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@app.task(bind=True)
def predict_fragmentation_task(self, hours: int = 24, threshold: float = 1.5) -> Dict[str, Any]:
    try:
        logger.info(f"Starting fragmentation prediction task: {hours} hours ahead")
        predictor = FragmentationPredictor()
        
        predictions = predictor.predict_all_nodes(hours=hours, threshold=threshold)
        nodes_needing_defrag = predictor.get_nodes_needing_defrag(hours=hours, threshold=threshold)
        
        results = []
        for p in predictions:
            results.append(p.to_dict())
        
        logger.info(
            f"Fragmentation prediction completed: {len(predictions)} nodes predicted, "
            f"{len(nodes_needing_defrag)} nodes need defrag"
        )
        
        return {
            'status': 'success',
            'prediction_hours': hours,
            'threshold': threshold,
            'total_nodes': len(predictions),
            'nodes_needing_defrag': len(nodes_needing_defrag),
            'predictions': results
        }
    except Exception as e:
        logger.error(f"Fragmentation prediction failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@app.task(bind=True)
def analyze_cost_benefit_task(self) -> Dict[str, Any]:
    try:
        logger.info("Starting cost/benefit analysis task")
        analyzer = CostBenefitAnalyzer()
        
        analyses = analyzer.analyze_all_nodes()
        priority_list = analyzer.get_priority_defrag_list()
        
        results = []
        for a in analyses:
            results.append(a.to_dict())
        
        priority_results = []
        for a in priority_list:
            priority_results.append(a.to_dict())
        
        logger.info(
            f"Cost/benefit analysis completed: {len(analyses)} nodes analyzed, "
            f"{len(priority_list)} nodes recommended for defrag"
        )
        
        return {
            'status': 'success',
            'total_nodes': len(analyses),
            'recommended_count': len(priority_list),
            'analyses': results,
            'priority_list': priority_results
        }
    except Exception as e:
        logger.error(f"Cost/benefit analysis failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@app.task(bind=True)
def predictive_defrag_task(self, hours: int = 24, threshold: float = 1.5,
                           parallel: bool = True, max_workers: int = 4) -> Dict[str, Any]:
    try:
        logger.info(f"Starting predictive defrag task: {hours} hours ahead")
        predictor = FragmentationPredictor()
        
        predictions = predictor.get_nodes_needing_defrag(hours=hours, threshold=threshold)
        
        if not predictions:
            logger.info("No nodes need predictive defragmentation")
            return {
                'status': 'success',
                'message': 'No nodes need predictive defragmentation',
                'nodes_processed': 0
            }
        
        node_ids = [p.node_id for p in predictions]
        logger.info(f"Found {len(node_ids)} nodes needing predictive defragmentation")
        
        if parallel and len(node_ids) > 1:
            return defrag_nodes_parallel(node_ids, max_workers)
        else:
            connection_manager = RedisConnectionManager()
            defragmenter = MemoryDefragmenter(connection_manager, parallel=False)
            stats_analyzer = StatisticsAnalyzer()
            
            results = []
            for node_id in node_ids:
                try:
                    result = defragmenter.defrag_node(node_id)
                    stats_analyzer.store_defrag_result(result)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to defrag node {node_id}: {e}")
            
            summary = defragmenter.get_defrag_summary(results)
            
            return {
                'status': 'success',
                'predictive': True,
                'prediction_hours': hours,
                'threshold': threshold,
                'summary': summary
            }
    except Exception as e:
        logger.error(f"Predictive defrag failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@app.task
def periodic_analysis_and_prediction() -> Dict[str, Any]:
    logger.info("Starting periodic analysis and prediction")
    
    analysis_result = analyze_fragmentation_causes_task.delay()
    prediction_result = predict_fragmentation_task.delay(hours=24, threshold=1.5)
    cost_benefit_result = analyze_cost_benefit_task.delay()
    
    analysis_result.wait(timeout=300)
    prediction_result.wait(timeout=300)
    cost_benefit_result.wait(timeout=300)
    
    return {
        'status': 'completed',
        'analysis_task_id': analysis_result.id,
        'prediction_task_id': prediction_result.id,
        'cost_benefit_task_id': cost_benefit_result.id
    }


@app.task
def intelligent_predictive_defrag(hours: int = 24, threshold: float = 1.5,
                                   parallel: bool = True, max_workers: int = 4) -> Dict[str, Any]:
    logger.info("Starting intelligent predictive defrag")
    
    prediction_data = predict_fragmentation_task(hours=hours, threshold=threshold)
    
    cost_data = analyze_cost_benefit_task()
    
    if prediction_data.get('status') == 'success' and cost_data.get('status') == 'success':
        priority_node_ids = [
            p['node_id'] for p in cost_data.get('priority_list', [])
            if any(
                pred['node_id'] == p['node_id'] and pred['will_exceed_threshold']
                for pred in prediction_data.get('predictions', [])
            )
        ]
        
        if priority_node_ids:
            logger.info(f"Starting intelligent defrag for {len(priority_node_ids)} priority nodes")
            return defrag_nodes_parallel(priority_node_ids, max_workers) if parallel else None
        else:
            return {
                'status': 'success',
                'message': 'No priority nodes need predictive defragmentation'
            }
    
    return {
        'status': 'failed',
        'message': 'Analysis tasks failed'
    }
