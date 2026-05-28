"""Redis 集群拓扑采集器。

负责：
- 通过任意种子节点连接集群并获取完整拓扑（CLUSTER NODES / CLUSTER INFO）。
- 对每个节点执行 INFO、INFO STATS、INFO COMMANDSTATS、SLOWLOG 等采集。
- 输出标准化的数据结构供后续分析模块使用。
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from redis import Redis
from redis.cluster import ClusterNode, RedisCluster
from redis.exceptions import (
    ConnectionError,
    RedisError,
    TimeoutError as RedisTimeoutError,
)

log = logging.getLogger(__name__)


TOTAL_SLOTS = 16384


@dataclass
class NodeInfo:
    node_id: str
    host: str
    port: int
    cport: int
    flags: List[str]
    role: str                 # master / slave / myself
    master_id: Optional[str]
    slots: List[Tuple[int, int]] = field(default_factory=list)
    ping_sent: int = 0
    pong_recv: int = 0
    config_epoch: int = 0
    link_state: str = ""
    info: Dict[str, Any] = field(default_factory=dict)
    commandstats: Dict[str, Any] = field(default_factory=dict)
    slowlog: List[Dict[str, Any]] = field(default_factory=list)
    reachable: bool = True
    error: Optional[str] = None
    # 复制延迟连续采样
    replication_lag_samples: List[float] = field(default_factory=list)   # 秒数
    replication_lag_max_sec: float = 0.0
    replication_lag_avg_sec: float = 0.0
    replication_lag_p95_sec: float = 0.0
    # 性能指标（供槽位分配权重使用）
    perf_score: float = 0.0   # 综合性能评分，越高表示性能越强
    perf_baseline_qps: float = 0.0
    perf_cpu_available: float = 1.0   # 0~1，剩余CPU容量比例
    perf_mem_available: float = 1.0   # 0~1，剩余内存容量比例


@dataclass
class ClusterTopology:
    """标准化的集群拓扑数据结构。"""

    seed: str
    cluster_state: str = "unknown"
    cluster_slots_assigned: int = 0
    cluster_slots_ok: int = 0
    cluster_slots_pfail: int = 0
    cluster_slots_fail: int = 0
    cluster_known_nodes: int = 0
    cluster_size: int = 0
    cluster_current_epoch: int = 0
    cluster_my_epoch: int = 0
    nodes: Dict[str, NodeInfo] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    # ---- 便捷属性 ----
    @property
    def masters(self) -> List[NodeInfo]:
        return [n for n in self.nodes.values() if n.role == "master"]

    @property
    def slaves(self) -> List[NodeInfo]:
        return [n for n in self.nodes.values() if n.role == "slave"]

    @property
    def master_slave_map(self) -> Dict[str, List[NodeInfo]]:
        m: Dict[str, List[NodeInfo]] = {}
        for n in self.nodes.values():
            if n.role == "slave" and n.master_id:
                m.setdefault(n.master_id, []).append(n)
        return m

    def slot_count(self, node: NodeInfo) -> int:
        return sum(end - start + 1 for start, end in node.slots)


# ============== 解析辅助 ==============

def _parse_cluster_nodes(raw: str) -> Dict[str, NodeInfo]:
    """解析 CLUSTER NODES 的原始字符串。"""
    nodes: Dict[str, NodeInfo] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 8:
            continue
        node_id = parts[0]
        addr = parts[1]
        # host:port@cport[,channel]
        host_port = addr.split(",")[0]
        if "@" in host_port:
            host_port_cport = host_port.split("@")
            host_port = host_port_cport[0]
        host, port_s = host_port.rsplit(":", 1)
        port = int(port_s)
        flags = parts[2].split(",")
        master_id = None if parts[3] == "-" else parts[3]
        ping_sent = int(parts[4])
        pong_recv = int(parts[5])
        config_epoch = int(parts[6])
        link_state = parts[7]

        role = "master"
        if "slave" in flags or "replica" in flags:
            role = "slave"
        if "myself" in flags:
            role = "slave" if master_id else "master"

        slots: List[Tuple[int, int]] = []
        for slot_spec in parts[8:]:
            if slot_spec.startswith("["):
                # 迁移中的槽位: [slot-<-node_id] 或 [slot->-node_id]
                continue
            if "-" in slot_spec:
                start, end = slot_spec.split("-", 1)
                slots.append((int(start), int(end)))
            else:
                s = int(slot_spec)
                slots.append((s, s))

        nodes[node_id] = NodeInfo(
            node_id=node_id,
            host=host,
            port=port,
            cport=port + 10000,
            flags=flags,
            role=role,
            master_id=master_id,
            slots=slots,
            ping_sent=ping_sent,
            pong_recv=pong_recv,
            config_epoch=config_epoch,
            link_state=link_state,
        )
    return nodes


def _parse_info(raw: str) -> Dict[str, Any]:
    """把 INFO 的多行 key:value 输出解析为 dict。"""
    data: Dict[str, Any] = {}
    current_section: Dict[str, Any] = {}
    data["__root__"] = current_section
    for line in raw.splitlines():
        if not line:
            continue
        if line.startswith("#"):
            section = line.lstrip("#").strip()
            current_section = {}
            data[section] = current_section
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        current_section[k.strip()] = _coerce(v.strip())
    return data


def _coerce(value: str) -> Any:
    """简单类型推断。"""
    if not value:
        return ""
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_commandstats(info: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """从 INFO COMMANDSTATS 输出提取命令统计。"""
    stats: Dict[str, Dict[str, Any]] = {}
    cmd_section = info.get("Commandstats")
    if not cmd_section:
        return stats
    for k, v in cmd_section.items():
        if not k.startswith("cmdstat_"):
            continue
        name = k[len("cmdstat_"):]
        parsed: Dict[str, Any] = {}
        for pair in str(v).split(","):
            if "=" not in pair:
                continue
            pk, _, pv = pair.partition("=")
            try:
                parsed[pk] = float(pv)
            except ValueError:
                parsed[pk] = pv
        stats[name] = parsed
    return stats


# ============== 客户端封装 ==============

def _mk_client(host: str, port: int, cfg: Dict[str, Any]) -> Redis:
    rcfg = cfg.get("redis", {})
    kwargs: Dict[str, Any] = dict(
        host=host,
        port=port,
        socket_timeout=rcfg.get("socket_timeout", 2.0),
        socket_connect_timeout=rcfg.get("socket_connect_timeout", 2.0),
        retry_on_timeout=rcfg.get("retry_on_timeout", True),
    )
    if rcfg.get("password"):
        kwargs["password"] = rcfg["password"]
    return Redis(**kwargs)


def _safe_run(client: Redis, fn) -> Tuple[bool, Any, Optional[str]]:
    try:
        return True, fn(client), None
    except (ConnectionError, RedisTimeoutError, RedisError) as e:
        log.warning("redis 调用失败: %s", e)
        return False, None, str(e)


# ============== 采集主流程 ==============

def collect_topology(cfg: Dict[str, Any]) -> ClusterTopology:
    """通过配置的种子节点采集整个集群拓扑与各节点指标。"""
    rcfg = cfg["redis"]
    seed_host = rcfg["host"]
    seed_port = int(rcfg.get("port", 6379))
    seed_label = f"{seed_host}:{seed_port}"

    seed_client = _mk_client(seed_host, seed_port, cfg)

    ok, cluster_info_raw, err = _safe_run(seed_client, lambda c: c.execute_command("CLUSTER INFO"))
    if not ok:
        raise ConnectionError(f"无法连接种子节点 {seed_label}: {err}")

    cluster_info = _parse_info(cluster_info_raw.decode() if isinstance(cluster_info_raw, bytes) else cluster_info_raw)
    root = cluster_info.get("__root__", {})

    ok, nodes_raw, err = _safe_run(seed_client, lambda c: c.execute_command("CLUSTER NODES"))
    if not ok or not nodes_raw:
        raise ConnectionError(f"获取 CLUSTER NODES 失败: {err}")

    nodes = _parse_cluster_nodes(nodes_raw.decode() if isinstance(nodes_raw, bytes) else nodes_raw)

    topo = ClusterTopology(
        seed=seed_label,
        cluster_state=root.get("cluster_state", "unknown"),
        cluster_slots_assigned=int(root.get("cluster_slots_assigned", 0)),
        cluster_slots_ok=int(root.get("cluster_slots_ok", 0)),
        cluster_slots_pfail=int(root.get("cluster_slots_pfail", 0)),
        cluster_slots_fail=int(root.get("cluster_slots_fail", 0)),
        cluster_known_nodes=int(root.get("cluster_known_nodes", 0)),
        cluster_size=int(root.get("cluster_size", 0)),
        cluster_current_epoch=int(root.get("cluster_current_epoch", 0)),
        cluster_my_epoch=int(root.get("cluster_my_epoch", 0)),
        nodes=nodes,
    )

    # 逐个节点采集详细信息
    for n in nodes.values():
        client = _mk_client(n.host, n.port, cfg)
        ok, info_raw, err = _safe_run(client, lambda c: c.info())
        if not ok:
            n.reachable = False
            n.error = err or "info failed"
            continue
        n.info = info_raw if isinstance(info_raw, dict) else _parse_info(str(info_raw))
        n.commandstats = _parse_commandstats(n.info)
        ok, slowlog, _ = _safe_run(
            client,
            lambda c: c.execute_command("SLOWLOG", "GET", cfg["report"].get("top_n_slowlog", 20)),
        )
        if ok and slowlog:
            n.slowlog = _normalize_slowlog(slowlog)
    return topo


def _normalize_slowlog(raw: Iterable[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in raw:
        # SLOWLOG GET 返回顺序: id, timestamp, duration, cmd+args, client, client_name
        try:
            out.append({
                "id": item[0],
                "timestamp": item[1],
                "duration_us": item[2],
                "command": b" ".join(item[3]).decode(errors="ignore") if isinstance(item[3], (list, tuple)) else str(item[3]),
                "client": item[4] if len(item) > 4 else "",
                "name": item[5] if len(item) > 5 else "",
            })
        except Exception:  # pragma: no cover
            continue
    return out


def _get_repl_offsets(client: Redis) -> Tuple[str, int]:
    """获取节点的复制偏移量信息，返回 (role, offset)。"""
    ok, info_raw, _ = _safe_run(client, lambda c: c.info("replication"))
    if not ok or not isinstance(info_raw, dict):
        return "unknown", 0
    role = info_raw.get("role", "unknown")
    if role == "master":
        return "master", int(info_raw.get("master_repl_offset", 0) or 0)
    else:
        return "slave", int(info_raw.get("slave_repl_offset", 0) or 0)


def sample_replication_lag(
    topo: ClusterTopology,
    cfg: Dict[str, Any],
    duration_sec: float = 1.0,
    interval_sec: float = 0.1,
) -> None:
    """连续采样复制延迟，写入每个 slave 节点。

    默认采样 1 秒，每 100ms 一次，共 10 次。
    """
    import statistics

    sample_cfg = cfg.get("redis", {}).get("replication_lag_sample", {})
    duration_sec = float(sample_cfg.get("duration_sec", duration_sec))
    interval_sec = float(sample_cfg.get("interval_sec", interval_sec))

    # 预创建所有节点的客户端
    clients: Dict[str, Redis] = {}
    for n in topo.nodes.values():
        if not n.reachable:
            continue
        clients[n.node_id] = _mk_client(n.host, n.port, cfg)

    master_offsets: Dict[str, List[Tuple[float, int]]] = {}
    slave_offsets: Dict[str, List[Tuple[float, int]]] = {}

    # 开始采样
    start = time.time()
    next_time = start
    while time.time() - start < duration_sec:
        t = time.time()
        # 采样所有 master 的偏移
        for n in topo.nodes.values():
            if n.role != "master" or not n.reachable or n.node_id not in clients:
                continue
            _, off = _get_repl_offsets(clients[n.node_id])
            master_offsets.setdefault(n.node_id, []).append((t, off))
        # 采样所有 slave 的偏移
        for n in topo.nodes.values():
            if n.role != "slave" or not n.reachable or n.node_id not in clients:
                continue
            _, off = _get_repl_offsets(clients[n.node_id])
            slave_offsets.setdefault(n.node_id, []).append((t, off))
        next_time += interval_sec
        sleep_for = next_time - time.time()
        if sleep_for > 0:
            time.sleep(sleep_for)

    # 计算每个 slave 的延迟
    for n in topo.nodes.values():
        if n.role != "slave" or not n.master_id:
            continue
        m_samples = master_offsets.get(n.master_id, [])
        s_samples = slave_offsets.get(n.node_id, [])
        if not m_samples or not s_samples:
            continue
        # 估算 master 的字节/秒速率
        if len(m_samples) >= 2:
            m_dt = m_samples[-1][0] - m_samples[0][0]
            m_do = m_samples[-1][1] - m_samples[0][1]
            bytes_per_sec = max(m_do / max(m_dt, 0.001), 1.0)
        else:
            bytes_per_sec = 1.0
        # 对每个 slave 采样点，用线性插值找对应时间 master 的偏移
        lags: List[float] = []
        for st, so in s_samples:
            # 找到 st 前后两个 master 采样点
            m_prev = m_samples[0]
            m_next = m_samples[-1]
            for mt, mo in m_samples:
                if mt <= st:
                    m_prev = (mt, mo)
                else:
                    m_next = (mt, mo)
                    break
            if m_prev[0] == m_next[0]:
                m_off = m_prev[1]
            else:
                ratio = (st - m_prev[0]) / (m_next[0] - m_prev[0])
                m_off = m_prev[1] + (m_next[1] - m_prev[1]) * ratio
            lag_bytes = max(m_off - so, 0)
            lag_sec = lag_bytes / bytes_per_sec
            lags.append(lag_sec)
        if lags:
            n.replication_lag_samples = lags
            n.replication_lag_max_sec = max(lags)
            n.replication_lag_avg_sec = statistics.mean(lags)
            sorted_lags = sorted(lags)
            p95_idx = int(len(sorted_lags) * 0.95)
            n.replication_lag_p95_sec = sorted_lags[min(p95_idx, len(sorted_lags) - 1)]

    # 关闭客户端
    for c in clients.values():
        try:
            c.close()
        except Exception:
            pass


def compute_performance_scores(topo: ClusterTopology, cfg: Dict[str, Any]) -> None:
    """计算每个 master 节点的性能评分，用于槽位分配权重。

    评分 = min(剩余CPU比例, 剩余内存比例) * 100，越高表示可承载更多槽位。
    """
    thr = cfg.get("redis", {}).get("threshold", {})
    cpu_cap = float(thr.get("cpu_usage_percent", 80.0)) / 100.0
    mem_cap = float(thr.get("mem_usage_percent", 85.0)) / 100.0

    for n in topo.nodes.values():
        if n.role != "master" or not n.reachable or not isinstance(n.info, dict):
            continue
        mem = n.info.get("Memory", {}) or {}
        cpu = n.info.get("CPU", {}) or {}
        used_mem = float(mem.get("used_memory", 0) or 0)
        max_mem = float(mem.get("maxmemory", 0) or 0)
        # 内存可用比例：1 - (已用 / 上限 * 告警阈值)
        if max_mem > 0:
            mem_used_ratio = used_mem / max_mem
            mem_avail = max(0.0, 1.0 - (mem_used_ratio / max(mem_cap, 0.01)))
        else:
            mem_avail = 1.0
        # CPU 可用比例：1 - (当前使用率 / 告警阈值)
        uptime = float(n.info.get("Server", {}).get("uptime_in_seconds", 1) or 1)
        cpu_total = float(cpu.get("used_cpu_sys", 0) or 0) + float(cpu.get("used_cpu_user", 0) or 0)
        cpu_used_ratio = min(1.0, cpu_total / max(uptime, 1))
        cpu_avail = max(0.0, 1.0 - (cpu_used_ratio / max(cpu_cap, 0.01)))
        n.perf_cpu_available = cpu_avail
        n.perf_mem_available = mem_avail
        # 综合评分：木桶原则，取瓶颈资源
        n.perf_score = min(cpu_avail, mem_avail) * 100.0


@dataclass
class KeySample:
    """采样到的 key 信息。"""
    key: str
    type: str = ""
    size_bytes: int = 0
    freq: int = 0
    ttl: int = -1
    encoding: str = ""
    node_id: str = ""


@dataclass
class HotKeyReport:
    """热点 key 采样结果。"""
    samples: List[KeySample] = field(default_factory=list)
    total_scanned: int = 0
    by_freq: List[KeySample] = field(default_factory=list)    # 按频率降序
    by_size: List[KeySample] = field(default_factory=list)    # 按大小降序
    maxmemory_policy: str = ""


@dataclass
class SlowlogEntry:
    """标准化的慢查询条目。"""
    id: int
    timestamp: int
    duration_us: int
    command: str          # 原始命令
    cmd_pattern: str      # 聚合后的模式（如 GET ?）
    args_count: int = 0
    client: str = ""
    name: str = ""
    node_id: str = ""


@dataclass
class SlowlogPattern:
    """慢查询模式聚合。"""
    pattern: str
    count: int
    total_duration_us: int
    max_duration_us: int
    avg_duration_us: float
    sample_commands: List[str] = field(default_factory=list)


@dataclass
class MemoryTypeReport:
    """各数据类型内存占比。"""
    by_type: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # type -> {count, total_size, avg_size}
    total_sampled_keys: int = 0
    total_sampled_size: int = 0
    top_large_keys: List[KeySample] = field(default_factory=list)


def sample_hot_keys(
    topo: ClusterTopology,
    cfg: Dict[str, Any],
) -> HotKeyReport:
    """通过 SCAN + OBJECT FREQ/MEMORY USAGE 采样热点 key。

    在所有 master 节点上使用 SCAN 抽样（默认 500 个 key），
    如果 maxmemory-policy 为 LFU 则使用 OBJECT FREQ 获取频率。
    """
    hk_cfg = cfg.get("redis", {}).get("hotkey_sample", {})
    max_keys_per_node = int(hk_cfg.get("max_keys_per_node", 500))
    scan_count = int(hk_cfg.get("scan_count", 500))

    report = HotKeyReport()
    all_samples: List[KeySample] = []

    for n in topo.nodes.values():
        if n.role != "master" or not n.reachable:
            continue
        client = _mk_client(n.host, n.port, cfg)
        try:
            # 获取 maxmemory-policy
            ok, mem_info, _ = _safe_run(client, lambda c: c.info("memory"))
            if ok and isinstance(mem_info, dict):
                report.maxmemory_policy = str(mem_info.get("maxmemory_policy", ""))
            is_lfu = "lfu" in report.maxmemory_policy.lower()

            # SCAN 抽样
            cursor = 0
            scanned = 0
            for _ in range(50):  # 最多 50 次 SCAN 迭代
                ok, result, _ = _safe_run(
                    client,
                    lambda c: c.scan(cursor=cursor, count=scan_count),
                )
                if not ok or not result:
                    break
                cursor, keys = result
                for key in keys:
                    ks = KeySample(key=key.decode() if isinstance(key, bytes) else str(key))
                    ks.node_id = n.node_id
                    all_samples.append(ks)
                    scanned += 1
                    if scanned >= max_keys_per_node:
                        break
                if cursor == 0 or scanned >= max_keys_per_node:
                    break
            report.total_scanned += scanned

            # 对抽样到的 key 批量获取属性
            for ks in all_samples:
                if ks.node_id != n.node_id:
                    continue
                try:
                    pipe = client.pipeline(transaction=False)
                    pipe.type(ks.key)
                    pipe.memory_usage(ks.key, samples=0)
                    if is_lfu:
                        pipe.object_freq(ks.key)
                    pipe.ttl(ks.key)
                    pipe.object_encoding(ks.key)
                    results = pipe.execute()
                    ks.type = str(results[0]) if results[0] else "none"
                    ks.size_bytes = int(results[1]) if results[1] else 0
                    idx = 2
                    if is_lfu:
                        ks.freq = int(results[idx]) if results[idx] else 0
                        idx += 1
                    ks.ttl = int(results[idx]) if results[idx] else -1
                    ks.encoding = str(results[idx + 1]) if len(results) > idx + 1 and results[idx + 1] else ""
                except Exception:
                    pass
        finally:
            try:
                client.close()
            except Exception:
                pass

    report.samples = all_samples
    # 按频率排序（仅 LFU 模式有意义）
    if "lfu" in report.maxmemory_policy.lower():
        report.by_freq = sorted(all_samples, key=lambda k: k.freq, reverse=True)[:20]
    # 按大小排序
    report.by_size = sorted(all_samples, key=lambda k: k.size_bytes, reverse=True)[:20]
    return report


def collect_slowlog_entries(
    topo: ClusterTopology,
    cfg: Dict[str, Any],
) -> List[SlowlogEntry]:
    """收集所有节点的慢查询并标准化。"""
    entries: List[SlowlogEntry] = []
    top_n = int(cfg["report"].get("top_n_slowlog", 20))
    for n in topo.nodes.values():
        if not n.reachable:
            continue
        client = _mk_client(n.host, n.port, cfg)
        ok, raw, _ = _safe_run(
            client,
            lambda c: c.execute_command("SLOWLOG", "GET", max(top_n * 5, 100)),
        )
        try:
            client.close()
        except Exception:
            pass
        if not ok or not raw:
            continue
        for item in raw:
            try:
                cmd_bytes = item[3]
                cmd_str = b" ".join(cmd_bytes).decode(errors="ignore") if isinstance(cmd_bytes, (list, tuple)) else str(cmd_bytes)
                parts = cmd_str.split()
                # 聚合模式：命令名 + 参数个数标识
                cmd_name = parts[0].upper() if parts else "UNKNOWN"
                # 简单模式：命令名 + 参数数量
                arg_count = max(len(parts) - 1, 0)
                cmd_pattern = f"{cmd_name}({'?' * min(arg_count, 3)})" if arg_count > 0 else cmd_name
                entry = SlowlogEntry(
                    id=int(item[0]),
                    timestamp=int(item[1]),
                    duration_us=int(item[2]),
                    command=cmd_str,
                    cmd_pattern=cmd_pattern,
                    args_count=arg_count,
                    client=str(item[4]) if len(item) > 4 else "",
                    name=str(item[5]) if len(item) > 5 else "",
                    node_id=n.node_id,
                )
                entries.append(entry)
            except Exception:
                continue
    return entries


def analyze_slowlog_patterns(
    entries: List[SlowlogEntry],
    top_n: int = 10,
) -> List[SlowlogPattern]:
    """聚合慢查询模式，返回 Top-N。"""
    buckets: Dict[str, SlowlogPattern] = {}
    for e in entries:
        p = buckets.get(e.cmd_pattern)
        if p is None:
            p = SlowlogPattern(pattern=e.cmd_pattern, count=0, total_duration_us=0, max_duration_us=0, avg_duration_us=0.0)
            buckets[e.cmd_pattern] = p
        p.count += 1
        p.total_duration_us += e.duration_us
        p.max_duration_us = max(p.max_duration_us, e.duration_us)
        if len(p.sample_commands) < 3:
            p.sample_commands.append(e.command)
    for p in buckets.values():
        p.avg_duration_us = p.total_duration_us / p.count if p.count else 0.0
    return sorted(buckets.values(), key=lambda x: x.total_duration_us, reverse=True)[:top_n]


def analyze_memory_types(
    hotkey_report: HotKeyReport,
    top_n: int = 10,
) -> MemoryTypeReport:
    """基于采样 key 分析各数据类型内存占比。"""
    rep = MemoryTypeReport()
    for ks in hotkey_report.samples:
        t = ks.type or "unknown"
        if t not in rep.by_type:
            rep.by_type[t] = {"count": 0, "total_size": 0, "avg_size": 0.0}
        entry = rep.by_type[t]
        entry["count"] += 1
        entry["total_size"] += ks.size_bytes
        rep.total_sampled_keys += 1
        rep.total_sampled_size += ks.size_bytes
    for t, entry in rep.by_type.items():
        entry["avg_size"] = entry["total_size"] / entry["count"] if entry["count"] else 0.0
    rep.top_large_keys = sorted(hotkey_report.samples, key=lambda k: k.size_bytes, reverse=True)[:top_n]
    return rep
