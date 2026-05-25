import json
import re
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Union


_SLOW_LINE_RE = re.compile(r"\bCOLLSCAN\b|\bIXSCAN\b|\bFETCH\b|\bdocsExamined\b|\bkeysExamined\b")


def normalize_query(query: Dict) -> Dict:
    if not isinstance(query, dict):
        return query
    normalized: Dict = {}
    for k, v in query.items():
        if k.startswith("$") and k in ("$in", "$nin", "$all"):
            normalized[k] = [{"$elemMatch": "?"}]
        elif isinstance(v, dict):
            normalized[k] = normalize_query(v)
        elif isinstance(v, list):
            normalized[k] = {"$elemMatch": "?"}
        elif isinstance(v, (str, int, float, bool)):
            normalized[k] = "?"
        else:
            normalized[k] = "?"
    return normalized


def extract_query_pattern(doc: Dict) -> str:
    op = doc.get("op") or doc.get("command_name") or "QUERY"
    ns = doc.get("ns") or "{}.{}".format(doc.get("db", ""), doc.get("collection", ""))
    filter_doc = (
        doc.get("filter")
        or doc.get("query")
        or _extract_filter_from_command(doc.get("command", {}))
        or {}
    )
    sort = doc.get("sort") or (doc.get("command") or {}).get("sort") or None
    projection = doc.get("projection") or (doc.get("command") or {}).get("projection") or None

    pattern = {
        "op": op,
        "ns": ns,
        "filter": normalize_query(filter_doc) if isinstance(filter_doc, dict) else {},
    }
    if sort:
        pattern["sort"] = normalize_query(sort) if isinstance(sort, dict) else sort
    if projection:
        pattern["projection"] = normalize_query(projection) if isinstance(projection, dict) else projection
    return json.dumps(pattern, sort_keys=True, ensure_ascii=False)


def _extract_filter_from_command(command) -> Dict:
    if not isinstance(command, dict):
        return {}
    for key in ("filter", "query", "pipeline"):
        if key in command:
            return command[key]
    return {}


def parse_json_line(line: str) -> Optional[Dict]:
    line = line.strip()
    if not line:
        return None
    if line.startswith("{"):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None
    return _parse_text_log_line(line)


_TEXT_RE = re.compile(
    r"^\s*(?P<ts>\S+)\s+(?P<sev>\w)\s+(?P<cid>[-\w]+)\s+"
    r"(?:(?P<ctx>[-@\w]+)\s+)?"
    r"\[(?P<conn>[^\]]+)\]\s+"
    r"(?P<msg>.*)$"
)


def _extract_balanced_object(text: str, start: int) -> Dict:
    """从 text[start] 开始抽取成对大括号的对象，转换为 dict。"""
    if start >= len(text) or text[start] != "{":
        return {}
    depth = 0
    in_str = False
    str_ch = ""
    escape = False
    i = start
    while i < len(text):
        ch = text[i]
        if escape:
            escape = False
            i += 1
            continue
        if ch == "\\":
            escape = True
            i += 1
            continue
        if in_str:
            if ch == str_ch:
                in_str = False
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = True
            str_ch = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                raw = text[start : i + 1]
                return _safe_parse_jsonish(raw)
        i += 1
    return {}


def _safe_parse_jsonish(raw: str) -> Dict:
    """将 MongoDB 日志里的对象字符串转换为 dict，兼容单引号/未加引号键/ISODate。"""
    if not raw:
        return {}
    # 简化处理：去掉 ISODate(...)、NumberLong(...) 等包装，替换为内部值占位
    raw2 = re.sub(r"ISODate\(('[^']*'|\"[^\"]*\")\)", r"\1", raw)
    raw2 = re.sub(r"ObjectId\(('[^']*'|\"[^\"]*\")\)", r"\1", raw2)
    raw2 = re.sub(r"NumberLong\((\d+)\)", r"\1", raw2)
    raw2 = re.sub(r"NumberInt\((\d+)\)", r"\1", raw2)
    try:
        return json.loads(raw2)
    except json.JSONDecodeError:
        pass
    # 尝试 eval（受限）：先把单引号统一并给键加引号
    try:
        converted = _jsonify_keys(raw2)
        return json.loads(converted)
    except Exception:
        return {}


def _jsonify_keys(s: str) -> str:
    """对类似 { status: "active", age: { $gt: 18 } } 的字符串加引号使之合法 JSON。"""
    out = []
    i = 0
    in_str = False
    str_ch = ""
    while i < len(s):
        ch = s[i]
        if in_str:
            out.append(ch)
            if ch == str_ch and s[i - 1] != "\\":
                in_str = False
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = True
            str_ch = ch
            out.append('"')
            i += 1
            continue
        # 匹配裸键: 字母/$_ 开头，后接 :
        m = re.match(r"([A-Za-z_$][A-Za-z0-9_$]*)\s*:", s[i:])
        if m and (i == 0 or s[i - 1] in "{, \t"):
            out.append('"' + m.group(1) + '"')
            i += len(m.group(1))
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _parse_text_log_line(line: str) -> Optional[Dict]:
    m = _TEXT_RE.match(line)
    if not m:
        return None
    msg = m.group("msg")
    if "slow" not in msg.lower() and not _SLOW_LINE_RE.search(msg):
        return None
    doc = {
        "ts": m.group("ts"),
        "severity": m.group("sev"),
        "component": m.group("ctx"),
        "raw": msg,
    }
    doc.update(_extract_text_fields(msg))
    if "duration" not in doc:
        return None
    return doc


def _extract_text_fields(msg: str) -> Dict:
    fields: Dict = {}
    m = re.search(r"(\w+)\s+(\w+)", msg)
    if m:
        fields["op"] = m.group(1)
    m = re.search(r"(\w+\.\w+)\s+(command|query|update|remove|insert|getmore)", msg)
    if m:
        fields["ns"] = m.group(1)
    m = re.search(r"command:\s+(\w+)", msg)
    if m:
        fields["command_name"] = m.group(1)
    m = re.search(r"filter:\s+(\{)", msg)
    if m:
        fields["filter"] = _extract_balanced_object(msg, m.start(1))
    if not fields.get("filter"):
        m = re.search(r"query:\s+(\{)", msg)
        if m:
            fields["filter"] = _extract_balanced_object(msg, m.start(1))
    m = re.search(r"planSummary:\s+([A-Z]+)\s+(\{[^}]*\})?", msg)
    if m:
        fields["planSummary"] = m.group(1)
    m = re.search(r"keysExamined:(\d+)", msg)
    if m:
        fields["keysExamined"] = int(m.group(1))
    m = re.search(r"docsExamined:(\d+)", msg)
    if m:
        fields["docsExamined"] = int(m.group(1))
    m = re.search(r"nreturned:(\d+)", msg)
    if m:
        fields["nreturned"] = int(m.group(1))
    m = re.search(r"(\d+)ms$", msg)
    if m:
        fields["duration"] = int(m.group(1))
    return fields


def parse_file(path: Union[str, Path]) -> Iterator[Dict]:
    p = Path(path)
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            doc = parse_json_line(line)
            if doc:
                yield doc


def parse_iterable(lines: Iterable[str]) -> Iterator[Dict]:
    for line in lines:
        doc = parse_json_line(line)
        if doc:
            yield doc


def from_profile_entry(doc: Dict) -> Dict:
    command = doc.get("command") or {}
    ns = doc.get("ns", "")
    if "." in ns:
        db, coll = ns.split(".", 1)
    else:
        db, coll = ns, ""
    return {
        "ts": doc.get("ts"),
        "op": doc.get("op"),
        "ns": ns,
        "db": db,
        "collection": coll,
        "duration": doc.get("millis") or doc.get("durationMillis") or 0,
        "keysExamined": doc.get("keysExamined", 0),
        "docsExamined": doc.get("docsExamined", 0),
        "nreturned": doc.get("nreturned", 0),
        "filter": doc.get("query") or (command.get("filter") if isinstance(command, dict) else None) or {},
        "sort": doc.get("sort") or (command.get("sort") if isinstance(command, dict) else None),
        "projection": doc.get("projection") or (command.get("projection") if isinstance(command, dict) else None),
        "planSummary": doc.get("planSummary"),
        "command": command if isinstance(command, dict) else {},
        "raw": doc,
    }
