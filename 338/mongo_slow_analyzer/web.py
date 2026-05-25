from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .analyzer import build_report
from .config import load_config
from .log_parser import from_profile_entry, parse_file
from .mongo_client import (
    connect,
    fetch_profile_entries,
    get_collection_indexes,
    get_shard_info,
)

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parent.parent / "templates"),
    )

    app.config["APP_CFG"] = load_config()

    @app.route("/", methods=["GET", "POST"])
    def index():
        report = None
        error = None
        if request.method == "POST":
            try:
                report = _run_analysis(request)
            except Exception as e:
                logger.exception("analysis failed")
                error = str(e)
        return render_template("index.html", report=report, error=error)

    @app.route("/api/analyze", methods=["POST"])
    def api_analyze():
        try:
            report = _run_analysis(request)
            return jsonify(report)
        except Exception as e:
            logger.exception("api analysis failed")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app


def _run_analysis(req) -> dict:
    source = req.form.get("source", "profile")
    cfg = req.app.config["APP_CFG"]["mongodb"]
    client = connect(cfg)
    try:
        client.admin.command("ping")
    except Exception as e:
        raise RuntimeError("无法连接MongoDB: {}".format(e))

    if source == "file":
        log_path = req.form.get("log_path") or ""
        if not log_path or not os.path.isfile(log_path):
            raise RuntimeError("请提供有效的日志文件路径")
        parsed = list(parse_file(log_path))
        existing_indexes = []
        shard_info = get_shard_info(client)
    else:
        db = (req.form.get("db") or "").strip()
        if not db:
            raise RuntimeError("请指定数据库名称")
        slow_ms = int(req.form.get("slow_ms") or 100)
        limit = int(req.form.get("limit") or 1000)
        entries = fetch_profile_entries(client, db, min_ms=slow_ms, limit=limit)
        parsed = [from_profile_entry(d) for d in entries]
        existing_indexes = []
        for coll in set(e.get("collection", "") for e in parsed if e.get("collection")):
            try:
                existing_indexes.extend(get_collection_indexes(client, db, coll))
            except Exception:
                pass
        shard_info = get_shard_info(client)

    return build_report(parsed, existing_indexes=existing_indexes, shard_info=shard_info)
