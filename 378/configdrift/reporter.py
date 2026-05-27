"""Jinja2 报告生成器."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from configdrift.detector import DriftReport

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


_env: Environment | None = None


def _get_env() -> Environment:
    global _env
    if _env is None:
        _env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _env


def render(reports: List[DriftReport], output_dir: str) -> Dict[str, str]:
    """渲染 HTML + TXT + JSON 三份报告,返回文件路径 dict."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    env = _get_env()

    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reports": reports,
        "summary_total": sum(r.summary.get("total", 0) for r in reports),
        "summary_changed": sum(r.summary.get("changed", 0) for r in reports),
        "summary_added": sum(r.summary.get("added", 0) for r in reports),
        "summary_removed": sum(r.summary.get("removed", 0) for r in reports),
    }

    html_path = os.path.join(output_dir, f"drift_report_{ts}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(env.get_template("report.html.j2").render(**data))

    txt_path = os.path.join(output_dir, f"drift_report_{ts}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(env.get_template("report.txt.j2").render(**data))

    json_path = os.path.join(output_dir, f"drift_report_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in reports], f, ensure_ascii=False, indent=2)

    return {"html": html_path, "txt": txt_path, "json": json_path}
