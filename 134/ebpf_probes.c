/*
 * eBPF无侵入MySQL锁等待事件采集探针
 * 内核态程序 - 捕获futex/mutex/rwsem锁等待事件
 */

#include <uapi/linux/ptrace.h>
#include <uapi/linux/bpf.h>
#include <linux/sched.h>
#include <linux/futex.h>

// 锁类型定义
#define LOCK_TYPE_FUTEX    1
#define LOCK_TYPE_MUTEX    2
#define LOCK_TYPE_RWSEM    3

// 事件类型定义
#define EVENT_WAIT_START   1
#define EVENT_WAIT_END     2

// 锁等待事件数据结构
struct lock_event {
    u64 timestamp;         // 事件时间戳 (纳秒)
    u32 pid;               // 进程ID
    u32 tid;               // 线程ID
    u64 lock_addr;         // 锁地址
    u32 lock_type;         // 锁类型
    u32 event_type;        // 事件类型
    u64 wait_duration;     // 等待时长 (纳秒)
    char comm[16];         // 进程名
};

// 等待中的锁信息 (tid -> waiting_lock)
struct waiting_lock {
    u64 start_time;        // 等待开始时间
    u64 lock_addr;         // 锁地址
    u32 lock_type;         // 锁类型
};

// BPF映射: 记录正在等待锁的线程
BPF_HASH(waiting_locks, u32, struct waiting_lock);

// BPF环缓冲区: 发送事件到用户空间
BPF_RINGBUF_OUTPUT(lock_events, 1 << 20);  // 1MB环缓冲区

// 辅助函数: 提交事件到环缓冲区
static __always_inline void submit_lock_event(
    u32 lock_type,
    u32 event_type,
    u64 lock_addr,
    u64 wait_duration
) {
    struct lock_event *event;
    u32 tid = bpf_get_current_pid_tgid();
    u32 pid = tid >> 32;
    u64 ts = bpf_ktime_get_ns();
    
    event = lock_events.ringbuf_reserve(sizeof(struct lock_event));
    if (!event) {
        return;
    }
    
    event->timestamp = ts;
    event->pid = pid;
    event->tid = tid;
    event->lock_addr = lock_addr;
    event->lock_type = lock_type;
    event->event_type = event_type;
    event->wait_duration = wait_duration;
    bpf_get_current_comm(&event->comm, sizeof(event->comm));
    
    lock_events.ringbuf_submit(event, 0);
}

/* ==================== futex 追踪 ==================== */

// sys_enter_futex tracepoint 数据结构
struct futex_enter_args {
    u64 __unused__;
    u32 syscall_nr;
    u64 uaddr;
    u32 op;
    u32 val;
    u64 utime;
    u64 uaddr2;
    u32 val3;
};

TRACEPOINT_PROBE(syscalls, sys_enter_futex) {
    u32 op = args->op & FUTEX_CMD_MASK;
    
    // 只追踪等待操作
    if (op != FUTEX_WAIT && op != FUTEX_WAIT_PRIVATE) {
        return 0;
    }
    
    u32 tid = bpf_get_current_pid_tgid();
    u64 now = bpf_ktime_get_ns();
    
    // 记录等待开始
    struct waiting_lock wl = {
        .start_time = now,
        .lock_addr = args->uaddr,
        .lock_type = LOCK_TYPE_FUTEX
    };
    waiting_locks.update(&tid, &wl);
    
    // 提交等待开始事件
    submit_lock_event(LOCK_TYPE_FUTEX, EVENT_WAIT_START, args->uaddr, 0);
    
    return 0;
}

// sys_exit_futex tracepoint 数据结构
struct futex_exit_args {
    u64 __unused__;
    u32 syscall_nr;
    s64 ret;
};

TRACEPOINT_PROBE(syscalls, sys_exit_futex) {
    u32 tid = bpf_get_current_pid_tgid();
    struct waiting_lock *wl;
    
    wl = waiting_locks.lookup(&tid);
    if (!wl) {
        return 0;
    }
    
    u64 now = bpf_ktime_get_ns();
    u64 duration = now - wl->start_time;
    
    // 提交等待结束事件
    submit_lock_event(LOCK_TYPE_FUTEX, EVENT_WAIT_END, wl->lock_addr, duration);
    
    // 清理记录
    waiting_locks.delete(&tid);
    
    return 0;
}

/* ==================== mutex 追踪 ==================== */

// mutex_lock kprobe: 捕获互斥锁等待开始
int kprobe_mutex_lock(struct pt_regs *ctx, struct mutex *lock) {
    u32 tid = bpf_get_current_pid_tgid();
    u64 now = bpf_ktime_get_ns();
    
    // 尝试立即获取锁，如果失败则会等待
    // 这里我们记录所有mutex_lock调用
    struct waiting_lock wl = {
        .start_time = now,
        .lock_addr = (u64)lock,
        .lock_type = LOCK_TYPE_MUTEX
    };
    waiting_locks.update(&tid, &wl);
    
    submit_lock_event(LOCK_TYPE_MUTEX, EVENT_WAIT_START, (u64)lock, 0);
    
    return 0;
}

// mutex_lock kretprobe: 捕获互斥锁等待结束
int kretprobe_mutex_lock(struct pt_regs *ctx) {
    u32 tid = bpf_get_current_pid_tgid();
    struct waiting_lock *wl;
    
    wl = waiting_locks.lookup(&tid);
    if (!wl) {
        return 0;
    }
    
    u64 now = bpf_ktime_get_ns();
    u64 duration = now - wl->start_time;
    
    submit_lock_event(LOCK_TYPE_MUTEX, EVENT_WAIT_END, wl->lock_addr, duration);
    
    waiting_locks.delete(&tid);
    
    return 0;
}

/* ==================== rw_semaphore 追踪 ==================== */

// down_read kprobe: 捕获读信号量等待
int kprobe_down_read(struct pt_regs *ctx, struct rw_semaphore *sem) {
    u32 tid = bpf_get_current_pid_tgid();
    u64 now = bpf_ktime_get_ns();
    
    struct waiting_lock wl = {
        .start_time = now,
        .lock_addr = (u64)sem,
        .lock_type = LOCK_TYPE_RWSEM
    };
    waiting_locks.update(&tid, &wl);
    
    submit_lock_event(LOCK_TYPE_RWSEM, EVENT_WAIT_START, (u64)sem, 0);
    
    return 0;
}

// down_read kretprobe: 读信号量获取成功
int kretprobe_down_read(struct pt_regs *ctx) {
    u32 tid = bpf_get_current_pid_tgid();
    struct waiting_lock *wl;
    
    wl = waiting_locks.lookup(&tid);
    if (!wl) {
        return 0;
    }
    
    u64 now = bpf_ktime_get_ns();
    u64 duration = now - wl->start_time;
    
    submit_lock_event(LOCK_TYPE_RWSEM, EVENT_WAIT_END, wl->lock_addr, duration);
    
    waiting_locks.delete(&tid);
    
    return 0;
}

// down_write kprobe: 捕获写信号量等待
int kprobe_down_write(struct pt_regs *ctx, struct rw_semaphore *sem) {
    u32 tid = bpf_get_current_pid_tgid();
    u64 now = bpf_ktime_get_ns();
    
    struct waiting_lock wl = {
        .start_time = now,
        .lock_addr = (u64)sem,
        .lock_type = LOCK_TYPE_RWSEM
    };
    waiting_locks.update(&tid, &wl);
    
    submit_lock_event(LOCK_TYPE_RWSEM, EVENT_WAIT_START, (u64)sem, 0);
    
    return 0;
}

// down_write kretprobe: 写信号量获取成功
int kretprobe_down_write(struct pt_regs *ctx) {
    u32 tid = bpf_get_current_pid_tgid();
    struct waiting_lock *wl;
    
    wl = waiting_locks.lookup(&tid);
    if (!wl) {
        return 0;
    }
    
    u64 now = bpf_ktime_get_ns();
    u64 duration = now - wl->start_time;
    
    submit_lock_event(LOCK_TYPE_RWSEM, EVENT_WAIT_END, wl->lock_addr, duration);
    
    waiting_locks.delete(&tid);
    
    return 0;
}

/* ==================== 辅助统计映射 ==================== */

// 锁等待时长直方图
BPF_HISTOGRAM(lock_wait_hist, u64, 64);

// 按锁类型统计等待次数
BPF_ARRAY(lock_type_count, u64, 4);
