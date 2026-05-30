import logging
from flask import Flask, request, jsonify
from es_ilm_tool.es_client import ESClient
from es_ilm_tool.ilm_policy import ILMPolicyManager
from es_ilm_tool.lifecycle import LifecycleEngine
from es_ilm_tool.performance import PerformanceAnalyzer
from es_ilm_tool.audit import AuditLogger
from es_ilm_tool.metrics import MetricsExporter
from es_ilm_tool.scheduler import ILMScheduler
from es_ilm_tool.cost_analysis import CostAnalyzer
from es_ilm_tool.ccr import CCRManager
from es_ilm_tool import config

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)

    es_client = ESClient()
    ilm_manager = ILMPolicyManager()
    engine = LifecycleEngine()
    perf_analyzer = PerformanceAnalyzer()
    audit = AuditLogger()
    metrics_exporter = MetricsExporter()
    scheduler = ILMScheduler()
    cost_analyzer = CostAnalyzer()
    ccr_manager = CCRManager()

    @app.route("/api/health", methods=["GET"])
    def health_check():
        es_health = es_client.health_check()
        return jsonify({
            "service": "es-ilm-tool",
            "status": "running",
            "elasticsearch": es_health,
        })

    @app.route("/api/indices", methods=["GET"])
    def list_indices():
        pattern = request.args.get("pattern", "*")
        indices = engine.list_all_indices(pattern)
        return jsonify({"indices": indices, "count": len(indices)})

    @app.route("/api/indices/<index_name>", methods=["GET"])
    def get_index_info(index_name):
        info = engine.get_index_info(index_name)
        return jsonify(info.to_dict())

    @app.route("/api/indices/<index_name>/performance", methods=["GET"])
    def get_index_performance(index_name):
        perf = perf_analyzer.get_index_performance(index_name)
        return jsonify(perf)

    @app.route("/api/indices/<index_name>/health", methods=["GET"])
    def analyze_index_health(index_name):
        analysis = perf_analyzer.analyze_index_health(index_name)
        return jsonify(analysis)

    @app.route("/api/indices/<index_name>/shards", methods=["GET"])
    def get_index_shards(index_name):
        perf = perf_analyzer.get_shard_performance(index_name)
        return jsonify(perf)

    @app.route("/api/disk/cluster", methods=["GET"])
    def get_cluster_disk():
        disk_usage = engine.get_cluster_disk_usage()
        return jsonify(disk_usage)

    @app.route("/api/disk/tier/<tier>", methods=["GET"])
    def get_tier_disk(tier):
        if tier not in ("hot", "warm", "cold"):
            return jsonify({"error": "tier must be 'hot', 'warm', or 'cold'"}), 400
        disk_usage = engine.get_tier_disk_usage(tier)
        return jsonify(disk_usage)

    @app.route("/api/disk/check-migration", methods=["POST"])
    def check_migration_disk():
        data = request.get_json(force=True)
        target_tier = data.get("target_tier")
        index_size_bytes = data.get("index_size_bytes", 0)
        if not target_tier:
            return jsonify({"error": "target_tier is required"}), 400
        if target_tier not in ("warm", "cold"):
            return jsonify({"error": "target_tier must be 'warm' or 'cold'"}), 400
        check = engine.check_disk_watermark_for_migration(target_tier, index_size_bytes)
        return jsonify(check)

    @app.route("/api/rollover", methods=["POST"])
    def rollover():
        data = request.get_json(force=True)
        alias = data.get("alias")
        if not alias:
            return jsonify({"error": "alias is required"}), 400
        conditions = data.get("conditions")
        dry_run = data.get("dry_run", False)

        if dry_run:
            result = engine.rollover_dry_run(alias, conditions)
        else:
            result = engine.rollover(alias, conditions)
            if result.get("success"):
                audit.log_rollover(
                    alias=alias,
                    old_index=result.get("old_index", ""),
                    new_index=result.get("new_index", ""),
                    operator=data.get("operator", "api"),
                    dry_run=False,
                )
                metrics_exporter.record_rollover(alias, True)
            else:
                metrics_exporter.record_rollover(alias, False)
                audit.log_error("rollover", alias, result.get("error", "unknown"), operator=data.get("operator", "api"))

        return jsonify(result)

    @app.route("/api/freeze/<index_name>", methods=["POST"])
    def freeze_index(index_name):
        data = request.get_json(force=True) if request.is_json else {}
        result = engine.freeze_index(index_name)
        if result.get("success"):
            audit.log_freeze(index_name, operator=data.get("operator", "api"))
            metrics_exporter.record_freeze(index_name, True)
        else:
            metrics_exporter.record_freeze(index_name, False)
            audit.log_error("freeze", index_name, result.get("error", "unknown"))
        return jsonify(result)

    @app.route("/api/unfreeze/<index_name>", methods=["POST"])
    def unfreeze_index(index_name):
        data = request.get_json(force=True) if request.is_json else {}
        result = engine.unfreeze_index(index_name)
        if result.get("success"):
            audit.log_unfreeze(index_name, operator=data.get("operator", "api"))
        return jsonify(result)

    @app.route("/api/delete/<index_name>", methods=["DELETE"])
    def delete_index(index_name):
        data = request.get_json(force=True) if request.is_json else {}
        result = engine.delete_index(index_name)
        if result.get("success"):
            audit.log_delete(index_name, operator=data.get("operator", "api"))
            metrics_exporter.record_delete(index_name, True)
        else:
            metrics_exporter.record_delete(index_name, False)
            audit.log_error("delete", index_name, result.get("error", "unknown"))
        return jsonify(result)

    @app.route("/api/migrate/<index_name>/<target_tier>", methods=["POST"])
    def migrate_index(index_name, target_tier):
        data = request.get_json(force=True) if request.is_json else {}
        if target_tier not in ("warm", "cold"):
            return jsonify({"error": "target_tier must be 'warm' or 'cold'"}), 400

        if target_tier == "warm":
            result = engine.migrate_to_warm(index_name)
        else:
            result = engine.migrate_to_cold(index_name)

        if result.get("success"):
            audit.log_migrate(index_name, target_tier, operator=data.get("operator", "api"))
            metrics_exporter.record_migrate(index_name, target_tier, True)
        else:
            metrics_exporter.record_migrate(index_name, target_tier, False)
            audit.log_error(f"migrate_to_{target_tier}", index_name, result.get("error", "unknown"))

        return jsonify(result)

    @app.route("/api/forcemerge/<index_name>", methods=["POST"])
    def forcemerge_index(index_name):
        data = request.get_json(force=True) if request.is_json else {}
        max_segments = data.get("max_segments", 1)
        result = engine.forcemerge_index(index_name, max_segments)
        if result.get("success"):
            audit.log_forcemerge(index_name, max_segments, operator=data.get("operator", "api"))
        return jsonify(result)

    @app.route("/api/shrink/<index_name>", methods=["POST"])
    def shrink_index(index_name):
        data = request.get_json(force=True) if request.is_json else {}
        target_shards = data.get("target_shards", 1)
        result = engine.shrink_index(index_name, target_shards)
        if result.get("success"):
            audit.log_shrink(index_name, result.get("target", ""), target_shards, operator=data.get("operator", "api"))
        return jsonify(result)

    @app.route("/api/auto-lifecycle", methods=["POST"])
    def auto_lifecycle():
        data = request.get_json(force=True) if request.is_json else {}
        pattern = data.get("pattern", "*")
        dry_run = data.get("dry_run", True)
        result = engine.auto_lifecycle(pattern=pattern, dry_run=dry_run)
        return jsonify(result)

    @app.route("/api/fragmentation/<index_name>", methods=["GET"])
    def get_fragmentation(index_name):
        result = engine.get_fragmentation_ratio(index_name)
        return jsonify(result)

    @app.route("/api/fragmentation", methods=["GET"])
    def list_fragmented_indices():
        pattern = request.args.get("pattern", "*")
        result = engine.get_highly_fragmented_indices(pattern)
        return jsonify({"fragmented_indices": result, "count": len(result)})

    @app.route("/api/rebuild/<index_name>", methods=["POST"])
    def rebuild_index(index_name):
        data = request.get_json(force=True) if request.is_json else {}
        target_shards = data.get("target_shards")
        slices = data.get("slices")
        wait_for_completion = data.get("wait_for_completion", True)
        result = engine.rebuild_index(index_name, target_shards, slices, wait_for_completion)
        if result.get("success"):
            audit.log(
                action="rebuild",
                target=index_name,
                operator=data.get("operator", "api"),
                source="api",
                details=result,
            )
        return jsonify(result)

    @app.route("/api/auto-rebuild", methods=["POST"])
    def auto_rebuild():
        data = request.get_json(force=True) if request.is_json else {}
        pattern = data.get("pattern", "*")
        dry_run = data.get("dry_run", True)
        max_count = data.get("max_count")
        result = engine.auto_rebuild(pattern=pattern, dry_run=dry_run, max_count=max_count)
        return jsonify(result)

    @app.route("/api/ilm/policies", methods=["GET"])
    def list_ilm_policies():
        policies = ilm_manager.list_policies()
        return jsonify({"policies": policies, "count": len(policies)})

    @app.route("/api/ilm/policies/<policy_name>", methods=["GET"])
    def get_ilm_policy(policy_name):
        policy = ilm_manager.get_policy(policy_name)
        if not policy:
            return jsonify({"error": f"Policy '{policy_name}' not found"}), 404
        return jsonify(policy)

    @app.route("/api/ilm/policies", methods=["POST"])
    def create_ilm_policy():
        data = request.get_json(force=True)
        policy_name = data.get("name")
        policy_def = data.get("policy")
        if not policy_name or not policy_def:
            return jsonify({"error": "name and policy are required"}), 400

        success = ilm_manager.create_policy(policy_name, policy_def)
        if success:
            audit.log_policy_change(policy_name, "create", operator=data.get("operator", "api"))
            return jsonify({"success": True, "policy_name": policy_name}), 201
        return jsonify({"success": False, "error": "Failed to create policy"}), 500

    @app.route("/api/ilm/policies/<policy_name>", methods=["DELETE"])
    def delete_ilm_policy(policy_name):
        success = ilm_manager.delete_policy(policy_name)
        if success:
            audit.log_policy_change(policy_name, "delete", operator="api")
            return jsonify({"success": True, "policy_name": policy_name})
        return jsonify({"success": False, "error": "Failed to delete policy"}), 500

    @app.route("/api/ilm/policies/<policy_name>/apply", methods=["POST"])
    def apply_ilm_policy(policy_name):
        data = request.get_json(force=True)
        index_name = data.get("index")
        if not index_name:
            return jsonify({"error": "index is required"}), 400
        success = ilm_manager.apply_policy_to_index(index_name, policy_name)
        if success:
            audit.log_policy_change(policy_name, "apply_to_index", operator=data.get("operator", "api"))
            return jsonify({"success": True, "index": index_name, "policy": policy_name})
        return jsonify({"success": False}), 500

    @app.route("/api/ilm/policies/<policy_name>/remove", methods=["POST"])
    def remove_ilm_policy(policy_name):
        data = request.get_json(force=True)
        index_name = data.get("index")
        if not index_name:
            return jsonify({"error": "index is required"}), 400
        success = ilm_manager.remove_policy_from_index(index_name)
        if success:
            audit.log_policy_change(policy_name, "remove_from_index", operator=data.get("operator", "api"))
            return jsonify({"success": True, "index": index_name})
        return jsonify({"success": False}), 500

    @app.route("/api/ilm/status/<index_name>", methods=["GET"])
    def get_ilm_status(index_name):
        status = ilm_manager.get_index_ilm_status(index_name)
        return jsonify(status)

    @app.route("/api/ilm/retry/<index_name>", methods=["POST"])
    def retry_ilm(index_name):
        success = ilm_manager.retry_ilm(index_name)
        return jsonify({"success": success, "index": index_name})

    @app.route("/api/ilm/ensure-default", methods=["POST"])
    def ensure_default_policy():
        data = request.get_json(force=True) if request.is_json else {}
        policy_name = data.get("policy_name", "default_ilm_policy")
        success = ilm_manager.ensure_default_policy(policy_name)
        return jsonify({"success": success, "policy_name": policy_name})

    @app.route("/api/performance/cluster", methods=["GET"])
    def cluster_performance():
        result = perf_analyzer.get_cluster_performance()
        return jsonify(result)

    @app.route("/api/performance/slow-indices", methods=["GET"])
    def slow_indices():
        threshold = request.args.get("threshold_ms", type=int)
        result = perf_analyzer.get_slow_indices(threshold)
        return jsonify({"slow_indices": result, "count": len(result)})

    @app.route("/api/performance/largest-indices", methods=["GET"])
    def largest_indices():
        top_n = request.args.get("top_n", type=int)
        result = perf_analyzer.get_largest_indices(top_n)
        return jsonify({"largest_indices": result, "count": len(result)})

    @app.route("/api/performance/slow-shards", methods=["GET"])
    def slow_shards():
        threshold = request.args.get("threshold_ms", type=int)
        top_n = request.args.get("top_n", type=int)
        result = perf_analyzer.get_slow_shards(threshold, top_n)
        return jsonify({"slow_shards": result, "count": len(result)})

    @app.route("/api/cost/cluster", methods=["GET"])
    def cluster_cost():
        result = cost_analyzer.calculate_cluster_cost()
        return jsonify(result)

    @app.route("/api/cost/index/<index_name>", methods=["GET"])
    def index_cost(index_name):
        result = cost_analyzer.calculate_index_cost(index_name)
        return jsonify(result)

    @app.route("/api/cost/optimization", methods=["GET"])
    def cost_optimization():
        result = cost_analyzer.analyze_cost_optimization()
        return jsonify(result)

    @app.route("/api/cost/forecast", methods=["GET"])
    def cost_forecast():
        months = request.args.get("months", 12, type=int)
        result = cost_analyzer.get_cost_forecast(months)
        return jsonify(result)

    @app.route("/api/ccr/enabled", methods=["GET"])
    def ccr_enabled():
        return jsonify({"enabled": config.CCR_ENABLED, "remote_cluster": config.CCR_REMOTE_CLUSTER_NAME})

    @app.route("/api/ccr/register", methods=["POST"])
    def ccr_register():
        result = ccr_manager.register_remote_cluster()
        return jsonify(result)

    @app.route("/api/ccr/remote-info", methods=["GET"])
    def ccr_remote_info():
        result = ccr_manager.get_remote_cluster_info()
        return jsonify(result)

    @app.route("/api/ccr/follow/<leader_index>", methods=["POST"])
    def ccr_follow(leader_index):
        data = request.get_json(force=True) if request.is_json else {}
        follower_index = data.get("follower_index")
        result = ccr_manager.create_follower_index(leader_index, follower_index)
        if result.get("success"):
            audit.log(
                action="ccr_follow",
                target=leader_index,
                operator=data.get("operator", "api"),
                source="api",
                details=result,
            )
        return jsonify(result)

    @app.route("/api/ccr/unfollow/<follower_index>", methods=["POST"])
    def ccr_unfollow(follower_index):
        result = ccr_manager.unfollow_index(follower_index)
        return jsonify(result)

    @app.route("/api/ccr/pause/<follower_index>", methods=["POST"])
    def ccr_pause(follower_index):
        result = ccr_manager.pause_follow(follower_index)
        return jsonify(result)

    @app.route("/api/ccr/resume/<follower_index>", methods=["POST"])
    def ccr_resume(follower_index):
        result = ccr_manager.resume_follow(follower_index)
        return jsonify(result)

    @app.route("/api/ccr/followers", methods=["GET"])
    def ccr_followers():
        result = ccr_manager.list_follower_indices()
        return jsonify({"followers": result, "count": len(result)})

    @app.route("/api/ccr/follower/<follower_index>", methods=["GET"])
    def ccr_follower_info(follower_index):
        result = ccr_manager.get_follower_info(follower_index)
        return jsonify(result)

    @app.route("/api/ccr/stats", methods=["GET"])
    def ccr_stats():
        result = ccr_manager.get_ccr_stats()
        return jsonify(result)

    @app.route("/api/ccr/sync-hot", methods=["POST"])
    def ccr_sync_hot():
        data = request.get_json(force=True) if request.is_json else {}
        dry_run = data.get("dry_run", True)
        result = ccr_manager.sync_hot_indices(dry_run=dry_run)
        return jsonify(result)

    @app.route("/api/ccr/promote/<follower_index>", methods=["POST"])
    def ccr_promote(follower_index):
        data = request.get_json(force=True) if request.is_json else {}
        result = ccr_manager.promote_follower(follower_index)
        if result.get("success"):
            audit.log(
                action="ccr_promote",
                target=follower_index,
                operator=data.get("operator", "api"),
                source="api",
                details=result,
            )
        return jsonify(result)

    @app.route("/api/audit", methods=["GET"])
    def query_audit():
        action = request.args.get("action")
        target = request.args.get("target")
        operator = request.args.get("operator")
        status = request.args.get("status")
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        limit = request.args.get("limit", 100, type=int)
        results = audit.query_audit_log(
            action=action, target=target, operator=operator,
            status=status, start_time=start_time, end_time=end_time,
            limit=limit,
        )
        return jsonify({"audit_entries": results, "count": len(results)})

    @app.route("/api/audit/search", methods=["POST"])
    def search_audit():
        data = request.get_json(force=True)
        result = audit.search_audit_log(data)
        return jsonify(result)

    @app.route("/api/audit/aggregate", methods=["POST"])
    def aggregate_audit():
        data = request.get_json(force=True)
        result = audit.aggregate_audit_log(data)
        return jsonify(result)

    @app.route("/api/audit/stats", methods=["GET"])
    def audit_stats():
        stats = audit.get_audit_stats()
        return jsonify(stats)

    @app.route("/api/scheduler/status", methods=["GET"])
    def scheduler_status():
        status = scheduler.get_status()
        return jsonify(status)

    @app.route("/api/scheduler/jobs", methods=["GET"])
    def list_scheduler_jobs():
        jobs = scheduler.list_jobs()
        return jsonify({"jobs": jobs, "count": len(jobs)})

    @app.route("/api/scheduler/jobs/<job_id>/trigger", methods=["POST"])
    def trigger_job(job_id):
        result = scheduler.trigger_job(job_id)
        if result.get("success"):
            return jsonify(result)
        return jsonify(result), 404

    @app.route("/api/scheduler/jobs/<job_id>/enable", methods=["POST"])
    def enable_job(job_id):
        success = scheduler.enable_job(job_id)
        return jsonify({"success": success, "job_id": job_id})

    @app.route("/api/scheduler/jobs/<job_id>/disable", methods=["POST"])
    def disable_job(job_id):
        success = scheduler.disable_job(job_id)
        return jsonify({"success": success, "job_id": job_id})

    @app.route("/api/scheduler/start", methods=["POST"])
    def start_scheduler():
        scheduler.start()
        return jsonify({"success": True, "message": "Scheduler started"})

    @app.route("/api/scheduler/stop", methods=["POST"])
    def stop_scheduler():
        scheduler.stop()
        return jsonify({"success": True, "message": "Scheduler stopped"})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app
