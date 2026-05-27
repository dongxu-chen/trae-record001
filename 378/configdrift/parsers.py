"""配置文件解析器.

把原始配置文本转换成可比较的 ``Dict[str, Any]`` 结构.支持:

- ``kvshell``: Nginx / Redis / Kafka 这类 ``key value;`` 或 ``key=value`` 风格.
- ``ini``: MySQL / INI 风格 (含 section).
- ``raw``: 按行保持原始格式,仅做逐行 diff.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Dict


class ConfigParser(ABC):
    """抽象解析器基类."""

    name: str = "base"

    @abstractmethod
    def parse(self, text: str) -> Dict[str, Any]:
        """将文本解析为字典."""

    @abstractmethod
    def serialize(self, data: Dict[str, Any]) -> str:
        """将字典序列化为配置文本 (用于修复命令)."""


def strip_comments(text: str,
                   line_markers: tuple = ("#", ";", "//"),
                   inline_markers: tuple = ("#", "//")) -> str:
    """去除配置文件中的注释行.

    Args:
        line_markers: 整行注释的起始标记 (行首出现即视为注释行)
        inline_markers: 行尾注释的起始标记 (出现在行中间即视为注释,需谨慎使用)

    说明:
        ``;`` 只作为整行注释标记 (INI 风格),不作为行尾注释,
        避免截断 Nginx 的 ``listen 80;`` 这类语法.
    """
    cleaned: list = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        # 整行注释,直接丢弃
        if any(line.startswith(m) for m in line_markers):
            continue
        # 行尾注释 (仅处理 # 和 //,不处理 ; 避免误伤)
        for m in inline_markers:
            pos = line.find(m)
            if pos > 0:
                # 简单判断: 不在引号内
                before = line[:pos]
                if before.count('"') % 2 == 0 and before.count("'") % 2 == 0:
                    line = line[:pos].rstrip()
                break
        if line:
            cleaned.append(line)
    return "\n".join(cleaned)


def _is_comment(line: str) -> bool:
    return re.match(r"^\s*[#;]", line) is not None


class KVShellParser(ConfigParser):
    """支持 ``key value;``, ``key=value``,``key value`` 三种形态.

    Nginx: ``worker_processes auto;`` / ``listen 80;``
    Redis/Kafka: ``bind 127.0.0.1`` / ``port=9092``
    """

    name = "kvshell"

    KEY_RE = re.compile(r"^\s*([A-Za-z_][\w\.\-]*)\s*[= ]\s*(.+?)\s*;?\s*$")

    def parse(self, text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        section_stack: list = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line or _is_comment(line):
                continue
            # 处理 nginx 的 block
            if line.endswith("{"):
                section = line.rstrip("{").strip()
                section_stack.append(section)
                continue
            if line == "}":
                if section_stack:
                    section_stack.pop()
                continue
            m = self.KEY_RE.match(raw)
            if not m:
                continue
            key = m.group(1)
            value = m.group(2).strip()
            # section 作为 key 的前缀,保证块内 key 不冲突
            prefix = " > ".join(section_stack)
            full_key = f"{prefix} :: {key}" if prefix else key
            # 尝试数值化
            value = _coerce_value(value)
            result[full_key] = value
        return result

    def serialize(self, data: Dict[str, Any]) -> str:
        lines: list = []
        for k, v in data.items():
            if " :: " in k:
                lines.append(f"# {k} = {v}")
            else:
                lines.append(f"{k} {v};")
        return "\n".join(lines) + "\n"


class IniParser(ConfigParser):
    """解析 INI (MySQL) 配置.支持多行 [section]. """

    name = "ini"

    def parse(self, text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        section = "__root__"
        for raw in text.splitlines():
            line = raw.strip()
            if not line or _is_comment(line):
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip()
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            full_key = f"{section} :: {k}"
            result[full_key] = _coerce_value(v)
        return result

    def serialize(self, data: Dict[str, Any]) -> str:
        sections: Dict[str, list] = {}
        for k, v in data.items():
            if " :: " in k:
                sec, key = k.split(" :: ", 1)
            else:
                sec, key = "__root__", k
            sections.setdefault(sec, []).append(f"{key} = {v}")
        out = []
        for sec, items in sections.items():
            if sec != "__root__":
                out.append(f"[{sec}]")
            out.extend(items)
        return "\n".join(out) + "\n"


class RawParser(ConfigParser):
    """按行比较,key = 行号,value = 行内容."""

    name = "raw"

    def parse(self, text: str) -> Dict[str, Any]:
        return {f"L{i:04d}": ln for i, ln in enumerate(text.splitlines(), 1)}

    def serialize(self, data: Dict[str, Any]) -> str:
        return "\n".join(v for _, v in sorted(data.items())) + "\n"


PARSERS: Dict[str, ConfigParser] = {
    "kvshell": KVShellParser(),
    "ini": IniParser(),
    "auto": KVShellParser(),  # 默认
    "raw": RawParser(),
}


def get_parser(name: str) -> ConfigParser:
    return PARSERS.get(name, PARSERS["auto"])


def _coerce_value(v: str) -> Any:
    """把字符串转成 int/float/bool,失败则保持原样."""
    if v.lower() in ("true", "yes", "on"):
        return True
    if v.lower() in ("false", "no", "off"):
        return False
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v
