"""配置漂移检测核心.

基于解析后的键值字典 (kvshell/ini/raw),对比 baseline,输出:

- ``changed``  值变更
- ``added``    新增 key
- ``removed``  删除 key

并基于变更内容生成 ``修复命令``.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from configdrift.parsers import strip_comments


def syntax_check_cmd(service: str, config_path: str) -> str:
    """返回各服务的配置语法检查命令."""
    mapping = {
        "nginx": f"nginx -t -c {config_path}",
        "mysql": f"mysqld --verbose --help 1>/dev/null",
        "redis": f"redis-server {config_path} --test-memory 0",
        "kafka": f"bash -c 'cd /opt/kafka && bin/kafka-server-start.sh -version'",
    }
    return mapping.get(service, f"# no syntax check for {service}")


@dataclass
class DriftItem:
    """单条漂移明细."""

    key: str
    drift_type: str  # changed / added / removed
    baseline: Any = None
    current: Any = None
    baseline_text: str = ""
    current_text: str = ""
    diff: str = ""


@dataclass
class DriftReport:
    """某台服务器某服务的检测结果."""

    server: str
    service: str
    timestamp: str = ""
    drift_items: List[DriftItem] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)

    @property
    def has_drift(self) -> bool:
        return bool(self.drift_items)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def detect_drift(baseline: Dict[str, Any],
                 current: Dict[str, Any],
                 baseline_text: str = "",
                 current_text: str = "",
                 auto_strip_comments: bool = True) -> List[DriftItem]:
    """比较两份字典,返回漂移列表.

    Args:
        auto_strip_comments: 自动去除 baseline_text / current_text 中的注释行,
            用于减少仅注释差异导致的误报.
    """
    items: List[DriftItem] = []
    keys = set(baseline.keys()) | set(current.keys())

    # 先清洗注释,减少行级 diff 的误报
    if auto_strip_comments:
        baseline_text = strip_comments(baseline_text)
        current_text = strip_comments(current_text)

    diff_text = ""
    if baseline_text and current_text:
        diff_text = "\n".join(
            difflib.unified_diff(
                baseline_text.splitlines(),
                current_text.splitlines(),
                fromfile="baseline",
                tofile="current",
                lineterm="",
            )
        )

    for k in sorted(keys):
        if k in baseline and k in current:
            if baseline[k] != current[k]:
                items.append(DriftItem(
                    key=k,
                    drift_type="changed",
                    baseline=baseline[k],
                    current=current[k],
                    baseline_text=str(baseline[k]),
                    current_text=str(current[k]),
                ))
        elif k not in baseline and k in current:
            items.append(DriftItem(
                key=k,
                drift_type="added",
                current=current[k],
                current_text=str(current[k]),
            ))
        elif k in baseline and k not in current:
            items.append(DriftItem(
                key=k,
                drift_type="removed",
                baseline=baseline[k],
                baseline_text=str(baseline[k]),
            ))
    if diff_text and items:
        # 把行级 diff 附加到第一条,便于报告展示
        items[0].diff = diff_text
    return items


def summarize(items: List[DriftItem]) -> Dict[str, int]:
    """统计 changed/added/removed 数量."""
    stat = {"changed": 0, "added": 0, "removed": 0}
    for it in items:
        stat[it.drift_type] = stat.get(it.drift_type, 0) + 1
    stat["total"] = len(items)
    return stat


def build_repair_commands(service: str, config_path: str,
                          items: List[DriftItem]) -> List[str]:
    """根据漂移生成修复命令 (恢复为 baseline).

    增强点:
    1. 前置语法检查,确保修改前原始配置语法正确
    2. 备份原始配置
    3. 执行 sed 修改
    4. 再次语法检查
    5. 最后 reload
    """
    if not items:
        return []
    cmds: List[str] = []
    sudo_prefix = "sudo "
    check = syntax_check_cmd(service, config_path)
    # 前置检查 + 备份
    cmds.append(f"# === {service} 修复脚本 ===")
    cmds.append(f"# 前置语法检查")
    cmds.append(f"{sudo_prefix}{check} || {{ echo '语法检查失败,中止修复'; exit 1; }}")
    cmds.append(f"{sudo_prefix}cp -a {config_path} {config_path}.$(date +%Y%m%d_%H%M%S).bak")
    cmds.append(f"# 应用修复")
    for it in items:
        if it.drift_type == "changed":
            if " :: " in it.key:
                sec, key = it.key.split(" :: ", 1)
                cmds.append(
                    f"{sudo_prefix}sed -i 's/^{key}[ =].*/{key} = {_escape(it.baseline_text)}/' {config_path}"
                )
            else:
                cmds.append(
                    f"{sudo_prefix}sed -i 's/^{it.key}[ =].*/{it.key} {_escape(it.baseline_text)};/' {config_path}"
                )
        elif it.drift_type == "added":
            cmds.append(
                f"{sudo_prefix}sed -i '/^{it.key}[ =]/d' {config_path}"
            )
        elif it.drift_type == "removed":
            if " :: " in it.key:
                sec, key = it.key.split(" :: ", 1)
                cmds.append(
                    f"{sudo_prefix}bash -c \"echo '{key} = {_escape(it.baseline_text)}' >> {config_path}\""
                )
            else:
                cmds.append(
                    f"{sudo_prefix}bash -c \"echo '{it.key} {_escape(it.baseline_text)};' >> {config_path}\""
                )
    cmds.append(f"# 修改后语法检查")
    cmds.append(f"{sudo_prefix}{check} || {{ echo '修改后语法错误,请回滚'; exit 1; }}")
    cmds.append(f"# 重载服务")
    cmds.append(f"{sudo_prefix}{_reload_cmd(service)}")
    return cmds


def _reload_cmd(service: str) -> str:
    mapping = {
        "nginx": "nginx -s reload",
        "mysql": "systemctl restart mysql",
        "redis": "systemctl restart redis",
        "kafka": "systemctl restart kafka",
    }
    return mapping.get(service, f"systemctl restart {service}")


def _escape(v: str) -> str:
    return str(v).replace("'", "'\\''")
