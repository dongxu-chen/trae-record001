#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_core_read.h>

#define TASK_COMM_LEN 16
#define MAX_PATH_LEN 256
#define CONTAINER_ID_LEN 64

struct process_event {
    __u32 pid;
    __u32 ppid;
    __u32 uid;
    __u32 gid;
    char comm[TASK_COMM_LEN];
    char container_id[CONTAINER_ID_LEN];
    __u64 timestamp;
    __u32 event_type;
};

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, sizeof(__u32));
} process_events SEC(".maps");

static __always_inline void get_container_id(char *container_id) {
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    struct cgroup *cgrp;
    const char *path;
    int i, j = 0;

    cgrp = BPF_CORE_READ(task, cgroups, subsys[0], cgroup);
    path = BPF_CORE_READ(cgrp, kn, name);

    for (i = 0; i < 128 && j < CONTAINER_ID_LEN - 1; i++) {
        if (path[i] == '\0') break;
        if (path[i] >= '0' && path[i] <= '9') {
            container_id[j++] = path[i];
        } else if (path[i] >= 'a' && path[i] <= 'f') {
            container_id[j++] = path[i];
        }
    }
    container_id[j] = '\0';
}

SEC("tp/sched/sched_process_exec")
int handle_exec(struct trace_event_raw_sched_process_exec *ctx) {
    struct process_event e = {};
    __u64 pid_tgid = bpf_get_current_pid_tgid();

    e.pid = pid_tgid >> 32;
    e.ppid = BPF_CORE_READ((struct task_struct *)bpf_get_current_task(), real_parent, pid);
    e.uid = bpf_get_current_uid_gid() >> 32;
    e.gid = bpf_get_current_uid_gid();
    e.timestamp = bpf_ktime_get_ns();
    e.event_type = 1;

    bpf_get_current_comm(&e.comm, sizeof(e.comm));
    get_container_id(e.container_id);

    bpf_perf_event_output(ctx, &process_events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tp/sched/sched_process_fork")
int handle_fork(struct trace_event_raw_sched_process_fork *ctx) {
    struct process_event e = {};
    __u64 pid_tgid = bpf_get_current_pid_tgid();

    e.pid = ctx->child_pid;
    e.ppid = pid_tgid >> 32;
    e.uid = bpf_get_current_uid_gid() >> 32;
    e.gid = bpf_get_current_uid_gid();
    e.timestamp = bpf_ktime_get_ns();
    e.event_type = 2;

    bpf_get_current_comm(&e.comm, sizeof(e.comm));
    get_container_id(e.container_id);

    bpf_perf_event_output(ctx, &process_events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tp/sched/sched_process_exit")
int handle_exit(struct trace_event_raw_sched_process_exit *ctx) {
    struct process_event e = {};
    __u64 pid_tgid = bpf_get_current_pid_tgid();

    e.pid = pid_tgid >> 32;
    e.ppid = BPF_CORE_READ((struct task_struct *)bpf_get_current_task(), real_parent, pid);
    e.uid = bpf_get_current_uid_gid() >> 32;
    e.gid = bpf_get_current_uid_gid();
    e.timestamp = bpf_ktime_get_ns();
    e.event_type = 3;

    bpf_get_current_comm(&e.comm, sizeof(e.comm));
    get_container_id(e.container_id);

    bpf_perf_event_output(ctx, &process_events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

char _license[] SEC("license") = "GPL";
