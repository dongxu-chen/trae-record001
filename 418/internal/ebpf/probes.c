package ebpf

//go:build ignore

#include <linux/bpf.h>
#include <linux/sched.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

typedef struct {
    __u64 ts;
    __u32 pid;
    __u32 tgid;
    char comm[16];
} exec_event_t;

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, sizeof(__u32));
    __uint(max_entries, 128);
} exec_events SEC(".maps");

typedef struct {
    __u64 ts;
    __u64 delta_ns;
    __u32 pid;
    __u32 tgid;
    char fname[64];
} open_event_t;

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, sizeof(__u32));
    __uint(max_entries, 128);
} open_events SEC(".maps");

typedef struct {
    __u64 ts;
    __u64 pid_tgid;
    char comm[16];
} sched_switch_event_t;

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, sizeof(__u32));
    __uint(max_entries, 128);
} sched_events SEC(".maps");

typedef struct {
    __u64 ts;
    __u32 pid;
    __u32 tgid;
    __u64 nanos;
} nanosleep_event_t;

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, sizeof(__u32));
    __uint(max_entries, 128);
} sleep_events SEC(".maps");

SEC("tracepoint/sched/sched_process_exec")
int trace_sched_process_exec(struct trace_event_raw_sched_process_exec *ctx) {
    exec_event_t ev = {};
    ev.ts = bpf_ktime_get_ns();
    ev.pid = bpf_get_current_pid_tgid() >> 32;
    ev.tgid = bpf_get_current_pid_tgid();
    bpf_get_current_comm(&ev.comm, sizeof(ev.comm));
    bpf_perf_event_output(ctx, &exec_events, BPF_F_CURRENT_CPU, &ev, sizeof(ev));
    return 0;
}

SEC("tracepoint/sched/sched_process_fork")
int trace_sched_process_fork(struct trace_event_raw_sched_process_fork *ctx) {
    exec_event_t ev = {};
    ev.ts = bpf_ktime_get_ns();
    ev.pid = ctx->child_pid;
    ev.tgid = ctx->child_pid;
    bpf_get_current_comm(&ev.comm, sizeof(ev.comm));
    bpf_perf_event_output(ctx, &exec_events, BPF_F_CURRENT_CPU, &ev, sizeof(ev));
    return 0;
}

SEC("kprobe/vfs_open")
int kprobe_vfs_open(struct pt_regs *ctx) {
    open_event_t ev = {};
    ev.ts = bpf_ktime_get_ns();
    ev.pid = bpf_get_current_pid_tgid() >> 32;
    ev.tgid = bpf_get_current_pid_tgid();
    bpf_probe_read_user_str(&ev.fname, sizeof(ev.fname), (void *)ctx);
    bpf_perf_event_output(ctx, &open_events, BPF_F_CURRENT_CPU, &ev, sizeof(ev));
    return 0;
}

SEC("tracepoint/sched/sched_switch")
int trace_sched_switch(struct trace_event_raw_sched_switch *ctx) {
    sched_switch_event_t ev = {};
    ev.ts = bpf_ktime_get_ns();
    ev.pid_tgid = bpf_get_current_pid_tgid();
    bpf_get_current_comm(&ev.comm, sizeof(ev.comm));
    bpf_perf_event_output(ctx, &sched_events, BPF_F_CURRENT_CPU, &ev, sizeof(ev));
    return 0;
}

SEC("kprobe/hrtimer_nanosleep")
int kprobe_hrtimer_nanosleep(struct pt_regs *ctx) {
    nanosleep_event_t ev = {};
    ev.ts = bpf_ktime_get_ns();
    ev.pid = bpf_get_current_pid_tgid() >> 32;
    ev.tgid = bpf_get_current_pid_tgid();
    bpf_perf_event_output(ctx, &sleep_events, BPF_F_CURRENT_CPU, &ev, sizeof(ev));
    return 0;
}

char _license[] SEC("license") = "GPL";
