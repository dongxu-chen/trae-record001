#!/usr/bin/env python3
"""
eBPF无侵入MySQL死锁检测系统
用户态采集程序 - 基于BCC
"""

import ctypes
import time
import threading
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, Set, List, Optional, Tuple

try:
    from bcc import BPF
    BCC_AVAILABLE = True
except ImportError:
    BCC_AVAILABLE = False
    print("警告: BCC未安装，eBPF功能不可用")

try:
    from prometheus_client import (
        Counter, Gauge, Histogram, start_http_server
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("警告: prometheus_client未安装，指标输出不可用")

from config import Config
from dingtalk_alert import DingTalkAlerter


class LockEvent(ctypes.Structure):
    """锁等待事件数据结构 (与内核态对应)"""
    _fields_ = [
        ("timestamp", ctypes.c_uint64),
        ("pid", ctypes.c_uint32),
        ("tid", ctypes.c_uint32),
        ("lock_addr", ctypes.c_uint64),
        ("lock_type", ctypes.c_uint32),
        ("event_type", ctypes.c_uint32),
        ("wait_duration", ctypes.c_uint64),
        ("comm", ctypes.c_char * 16),
    ]


LOCK_TYPE_NAMES = {
    1: "FUTEX",
    2: "MUTEX",
    3: "RWSEM",
}

EVENT_TYPE_NAMES = {
    1: "WAIT_START",
    2: "WAIT_END",
}


class WaitGraph:
    """等待图 - 用于死锁检测"""
    
    def __init__(self):
        # tid -> 等待的锁地址集合
        self.waiting_for: Dict[int, Set[int]] = defaultdict(set)
        # 锁地址 -> 持有该锁的tid集合
        self.holders: Dict[int, Set[int]] = defaultdict(set)
        # tid -> 持有锁的集合
        self.holds: Dict[int, Set[int]] = defaultdict(set)
        # 事件时间戳
        self.event_times: Dict[int, int] = {}
        
    def add_wait(self, tid: int, lock_addr: int, timestamp: int):
        """添加等待关系"""
        self.waiting_for[tid].add(lock_addr)
        self.event_times[tid] = timestamp
        
    def remove_wait(self, tid: int, lock_addr: int):
        """移除等待关系"""
        if tid in self.waiting_for:
            self.waiting_for[tid].discard(lock_addr)
            if not self.waiting_for[tid]:
                del self.waiting_for[tid]
                
    def add_holder(self, tid: int, lock_addr: int):
        """添加锁持有者"""
        self.holders[lock_addr].add(tid)
        self.holds[tid].add(lock_addr)
        
    def remove_holder(self, tid: int, lock_addr: int):
        """移除锁持有者"""
        if lock_addr in self.holders:
            self.holders[lock_addr].discard(tid)
            if not self.holders[lock_addr]:
                del self.holders[lock_addr]
        if tid in self.holds:
            self.holds[tid].discard(lock_addr)
            if not self.holds[tid]:
                del self.holds[tid]
                
    def detect_cycle(self, start_tid: int) -> Optional[List[int]]:
        """
        DFS检测死锁环路
        返回环路中的tid列表，如果无环路返回None
        """
        visited = set()
        path = []
        
        def dfs(tid: int, depth: int = 0) -> bool:
            if depth > 20:  # 限制搜索深度
                return False
                
            if tid in path:
                # 找到环路
                idx = path.index(tid)
                path.append(tid)
                return True
                
            if tid in visited:
                return False
                
            visited.add(tid)
            path.append(tid)
            
            # 查找该线程等待的所有锁
            for lock_addr in self.waiting_for.get(tid, set()):
                # 查找持有该锁的所有线程
                for holder_tid in self.holders.get(lock_addr, set()):
                    if dfs(holder_tid, depth + 1):
                        return True
                        
            path.pop()
            return False
            
        if dfs(start_tid) and len(path) >= 2:
            return path
        return None
        
    def get_wait_chain(self, tid: int) -> List[Tuple[int, int, int]]:
        """获取完整等待链"""
        chain = []
        current = tid
        seen = set()
        
        while current and current not in seen:
            seen.add(current)
            locks = self.waiting_for.get(current, set())
            if not locks:
                break
                
            lock_addr = next(iter(locks))
            holders = self.holders.get(lock_addr, set())
            if not holders:
                break
                
            holder = next(iter(holders))
            chain.append((current, lock_addr, holder))
            current = holder
            
        return chain


class EBPFDeadlockDetector:
    """eBPF死锁检测器"""
    
    def __init__(self):
        self.bpf: Optional[BPF] = None
        self.wait_graph = WaitGraph()
        self.running = False
        self.event_count = 0
        self.deadlock_count = 0
        self.mysql_pids: Set[int] = set()
        
        # Prometheus指标
        self.metrics = {}
        if PROMETHEUS_AVAILABLE:
            self._init_metrics()
            
        # 钉钉告警
        self.alerter = DingTalkAlerter()
        
        # 事件历史 (用于调试和分析)
        self.event_history = deque(maxlen=10000)
        
        # 检测统计
        self.stats = {
            'total_events': 0,
            'wait_start': 0,
            'wait_end': 0,
            'mysql_events': 0,
            'deadlocks_detected': 0,
            'avg_wait_us': 0,
            'max_wait_us': 0,
        }
        
    def _init_metrics(self):
        """初始化Prometheus指标"""
        self.metrics['lock_events_total'] = Counter(
            'mysql_lock_events_total',
            'Total lock wait events',
            ['lock_type', 'event_type']
        )
        self.metrics['lock_wait_duration_seconds'] = Histogram(
            'mysql_lock_wait_duration_seconds',
            'Lock wait duration in seconds',
            ['lock_type'],
            buckets=[0.000001, 0.00001, 0.0001, 0.001, 0.01, 0.1, 1.0, 10.0]
        )
        self.metrics['waiting_threads'] = Gauge(
            'mysql_waiting_threads',
            'Number of threads waiting for locks'
        )
        self.metrics['held_locks'] = Gauge(
            'mysql_held_locks',
            'Number of currently held locks'
        )
        self.metrics['deadlocks_detected_total'] = Counter(
            'mysql_deadlocks_detected_total',
            'Total number of deadlocks detected'
        )
        
    def load_bpf_program(self, bpf_file: str = "ebpf_probes.c"):
        """加载eBPF程序"""
        if not BCC_AVAILABLE:
            raise RuntimeError("BCC不可用，请先安装bcc")
            
        print("正在加载eBPF探针...")
        
        with open(bpf_file, 'r') as f:
            bpf_text = f.read()
            
        self.bpf = BPF(text=bpf_text)
        
        # 挂载kprobes
        self.bpf.attach_kprobe(event="mutex_lock", fn_name="kprobe_mutex_lock")
        self.bpf.attach_kretprobe(event="mutex_lock", fn_name="kretprobe_mutex_lock")
        
        try:
            self.bpf.attach_kprobe(event="down_read", fn_name="kprobe_down_read")
            self.bpf.attach_kretprobe(event="down_read", fn_name="kretprobe_down_read")
            self.bpf.attach_kprobe(event="down_write", fn_name="kprobe_down_write")
            self.bpf.attach_kretprobe(event="down_write", fn_name="kretprobe_down_write")
        except Exception as e:
            print(f"警告: rwsem探针加载失败 (可能内核符号不同): {e}")
            
        print("eBPF探针加载完成!")
        
    def discover_mysql_processes(self):
        """发现MySQL进程"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    name = proc.info['name']
                    if 'mysqld' in name or 'mysql' in name:
                        self.mysql_pids.add(proc.info['pid'])
                        print(f"发现MySQL进程: PID={proc.info['pid']}, name={name}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            print("警告: psutil未安装，无法自动发现MySQL进程")
            
        print(f"共发现 {len(self.mysql_pids)} 个MySQL进程")
        
    def handle_lock_event(self, ctx, data, size):
        """处理来自eBPF的锁等待事件"""
        event = ctypes.cast(data, ctypes.POINTER(LockEvent)).contents
        
        self.event_count += 1
        self.stats['total_events'] += 1
        
        # 过滤MySQL事件 (如果配置了MySQL进程过滤)
        is_mysql = event.pid in self.mysql_pids
        if is_mysql:
            self.stats['mysql_events'] += 1
            
        event_type = event.event_type
        lock_type = event.lock_type
        tid = event.tid
        lock_addr = event.lock_addr
        
        # 更新Prometheus指标
        if PROMETHEUS_AVAILABLE:
            lock_type_name = LOCK_TYPE_NAMES.get(lock_type, "UNKNOWN")
            event_type_name = EVENT_TYPE_NAMES.get(event_type, "UNKNOWN")
            self.metrics['lock_events_total'].labels(
                lock_type=lock_type_name,
                event_type=event_type_name
            ).inc()
            
            if event_type == 2 and event.wait_duration > 0:  # WAIT_END
                duration_sec = event.wait_duration / 1e9
                self.metrics['lock_wait_duration_seconds'].labels(
                    lock_type=lock_type_name
                ).observe(duration_sec)
                
                wait_us = event.wait_duration / 1e3
                self.stats['avg_wait_us'] = (
                    self.stats['avg_wait_us'] * (self.stats['wait_end'] - 1) + wait_us
                ) / self.stats['wait_end'] if self.stats['wait_end'] > 0 else wait_us
                self.stats['max_wait_us'] = max(self.stats['max_wait_us'], wait_us)
        
        if event_type == 1:  # WAIT_START
            self.stats['wait_start'] += 1
            self.wait_graph.add_wait(tid, lock_addr, event.timestamp)
            
            # 尝试检测死锁 (只有MySQL相关事件才检测，避免检测无关进程)
            if is_mysql or not self.mysql_pids:
                cycle = self.wait_graph.detect_cycle(tid)
                if cycle:
                    self._handle_deadlock(cycle, event)
            
        elif event_type == 2:  # WAIT_END
            self.stats['wait_end'] += 1
            self.wait_graph.remove_wait(tid, lock_addr)
            # 假设获取锁成功，标记为持有者
            self.wait_graph.add_holder(tid, lock_addr)
            
        # 记录事件历史
        self.event_history.append({
            'timestamp': event.timestamp,
            'pid': event.pid,
            'tid': event.tid,
            'lock_addr': hex(lock_addr),
            'lock_type': LOCK_TYPE_NAMES.get(lock_type, "UNKNOWN"),
            'event_type': EVENT_TYPE_NAMES.get(event_type, "UNKNOWN"),
            'wait_duration_us': event.wait_duration / 1e3 if event_type == 2 else 0,
            'comm': event.comm.decode('utf-8', errors='replace').strip('\x00'),
            'is_mysql': is_mysql,
        })
        
    def _handle_deadlock(self, cycle: List[int], trigger_event):
        """处理检测到的死锁"""
        self.deadlock_count += 1
        self.stats['deadlocks_detected'] += 1
        
        if PROMETHEUS_AVAILABLE:
            self.metrics['deadlocks_detected_total'].inc()
            
        # 获取等待链详情
        wait_chain = self.wait_graph.get_wait_chain(cycle[0])
        
        print("\n" + "=" * 80)
        print("🔴 检测到死锁!")
        print("=" * 80)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
        print(f"触发线程: {trigger_event.tid}")
        print(f"环路: {' → '.join(map(str, cycle))}")
        print(f"\n等待链详情:")
        for waiter, lock_addr, holder in wait_chain:
            print(f"  线程 {waiter} 等待锁 {hex(lock_addr)} (被 {holder} 持有)")
        print("=" * 80 + "\n")
        
        # 发送钉钉告警
        if self.alerter.enabled:
            self._send_deadlock_alert(cycle, wait_chain, trigger_event)
            
    def _send_deadlock_alert(self, cycle: List[int], wait_chain: List, event):
        """发送死锁钉钉告警"""
        chain_text = "\n".join([
            f"- 线程 {waiter} 等待锁 {hex(lock_addr)} (被 {holder} 持有)"
            for waiter, lock_addr, holder in wait_chain
        ])
        
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'transactions': [
                {
                    'transaction_id': f"TID-{tid}",
                    'thread_id': str(tid),
                    'queries': [],
                    'holds': [{'table': f'lock-{hex(l)}', 'mode': 'HOLD'} for l in self.wait_graph.holds.get(tid, set())],
                    'waiting_for': None if not self.wait_graph.waiting_for.get(tid) else {
                        'table': f'lock-{hex(next(iter(self.wait_graph.waiting_for[tid])))}',
                        'mode': 'WAIT'
                    }
                }
                for tid in cycle
            ]
        }
        
        self.alerter.alert_deadlock(alert_data)
        
    def event_poll_loop(self):
        """事件轮询循环"""
        while self.running:
            self.bpf.ring_buffer_poll(100)
            
            # 更新Gauge指标
            if PROMETHEUS_AVAILABLE:
                self.metrics['waiting_threads'].set(len(self.wait_graph.waiting_for))
                self.metrics['held_locks'].set(len(self.wait_graph.holders))
                
            time.sleep(0.001)  # 1ms轮询间隔，保证实时性
            
    def start(self):
        """启动检测器"""
        if self.running:
            print("检测器已在运行")
            return
            
        self.load_bpf_program()
        self.discover_mysql_processes()
        
        # 注册事件回调
        self.bpf["lock_events"].open_ring_buffer(self.handle_lock_event)
        
        self.running = True
        
        # 启动事件处理线程
        self.poll_thread = threading.Thread(target=self.event_poll_loop, daemon=True)
        self.poll_thread.start()
        
        # 启动Prometheus HTTP服务器
        if PROMETHEUS_AVAILABLE and Config.PROMETHEUS_ENABLED:
            start_http_server(Config.PROMETHEUS_PORT)
            print(f"Prometheus指标服务已启动: http://0.0.0.0:{Config.PROMETHEUS_PORT}/metrics")
            
        print("\neBPF死锁检测器已启动!")
        print(f"  - 监控进程: {self.mysql_pids if self.mysql_pids else '所有进程'}")
        print(f"  - 按 Ctrl+C 停止\n")
        
    def stop(self):
        """停止检测器"""
        self.running = False
        if hasattr(self, 'poll_thread'):
            self.poll_thread.join(timeout=2)
        print("eBPF死锁检测器已停止")
        
    def print_stats(self):
        """打印统计信息"""
        print("\n" + "-" * 60)
        print("📊 eBPF死锁检测器统计")
        print("-" * 60)
        print(f"总事件数: {self.stats['total_events']}")
        print(f"  - 等待开始: {self.stats['wait_start']}")
        print(f"  - 等待结束: {self.stats['wait_end']}")
        print(f"MySQL相关事件: {self.stats['mysql_events']}")
        print(f"检测到死锁: {self.stats['deadlocks_detected']}")
        print(f"平均等待时长: {self.stats['avg_wait_us']:.2f} µs")
        print(f"最大等待时长: {self.stats['max_wait_us']:.2f} µs")
        print(f"当前等待线程: {len(self.wait_graph.waiting_for)}")
        print(f"当前持有锁: {len(self.wait_graph.holders)}")
        print("-" * 60 + "\n")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="eBPF无侵入MySQL死锁检测器")
    parser.add_argument("--pid", type=int, nargs="*", help="指定监控的MySQL PID(可多个)")
    parser.add_argument("--no-mysql-filter", action="store_true", help="不过滤MySQL进程，监控所有进程")
    parser.add_argument("--stats-interval", type=int, default=10, help="打印统计信息的间隔(秒)")
    
    args = parser.parse_args()
    
    detector = EBPFDeadlockDetector()
    
    if args.pid:
        detector.mysql_pids = set(args.pid)
        print(f"使用指定的MySQL PID: {detector.mysql_pids}")
    elif args.no_mysql_filter:
        detector.mysql_pids = set()
        print("禁用MySQL进程过滤，监控所有进程的锁事件")
        
    try:
        detector.start()
        
        # 主循环，定期打印统计
        while True:
            time.sleep(args.stats_interval)
            detector.print_stats()
            
    except KeyboardInterrupt:
        print("\n收到停止信号...")
    finally:
        detector.stop()


if __name__ == "__main__":
    main()
