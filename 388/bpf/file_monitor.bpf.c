#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_core_read.h>

#define TASK_COMM_LEN 16
#define MAX_PATH_LEN 256
#define CONTAINER_ID_LEN 64

struct file_event {
    __u32 pid;
    __u32 uid;
    char comm[TASK_COMM_LEN];
    char container_id[CONTAINER_ID_LEN];
    char filename[MAX_PATH_LEN];
    __u64 timestamp;
    __u32 event_type;
    __u32 mode;
};

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, sizeof(__u32));
} file_events SEC(".maps");

static __always_inline void get_container_id(char *container_id) {
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    struct cgroup *cgrp;
    const char *path;
    int i, j = 0;

    cgrp = BPF_CORE_READ(task, cgroups, subsys[0], cgroup);
    path = BPF_CORE_READ(cgrp, kn, name);

    for (i = 0; i < 128 && j < CONTAINER_ID_LEN - 1; i++) {
        if (path[i] == '\0') break;
        if ((path[i] >= '0' && path[i] <= '9') || 
            (path[i] >= 'a' && path[i] <= 'f')) {
            container_id[j++] = path[i];
        }
    }
    container_id[j] = '\0';
}

SEC("tracepoint/syscalls/sys_enter_openat")
int handle_openat(struct trace_event_raw_sys_enter *ctx) {
    struct file_event e = {};
    __u64 pid_tgid = bpf_get_current_pid_tgid();

    e.pid = pid_tgid >> 32;
    e.uid = bpf_get_current_uid_gid() >> 32;
    e.timestamp = bpf_ktime_get_ns();
    e.event_type = 1;
    e.mode = (__u32)ctx->args[3];

    bpf_get_current_comm(&e.comm, sizeof(e.comm));
    bpf_probe_read_user_str(&e.filename, sizeof(e.filename), (void *)ctx->args[1]);
    get_container_id(e.container_id);

    bpf_perf_event_output(ctx, &file_events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_read")
int handle_read(struct trace_event_raw_sys_enter *ctx) {
    struct file_event e = {};
    __u64 pid_tgid = bpf_get_current_pid_tgid();

    e.pid = pid_tgid >> 32;
    e.uid = bpf_get_current_uid_gid() >> 32;
    e.timestamp = bpf_ktime_get_ns();
    e.event_type = 2;

    bpf_get_current_comm(&e.comm, sizeof(e.comm));
    get_container_id(e.container_id);

    bpf_perf_event_output(ctx, &file_events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_write")
int handle_write(struct trace_event_raw_sys_enter *ctx) {
    struct file_event e = {};
    __u64 pid_tgid = bpf_get_current_pid_tgid();

    e.pid = pid_tgid >> 32;
    e.uid = bpf_get_current_uid_gid() >> 32;
    e.timestamp = bpf_ktime_get_ns();
    e.event_type = 3;

    bpf_get_current_comm(&e.comm, sizeof(e.comm));
    get_container_id(e.container_id);

    bpf_perf_event_output(ctx, &file_events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_unlinkat")
int handle_unlinkat(struct trace_event_raw_sys_enter *ctx) {
    struct file_event e = {};
    __u64 pid_tgid = bpf_get_current_pid_tgid();

    e.pid = pid_tgid >> 32;
    e.uid = bpf_get_current_uid_gid() >> 32;
    e.timestamp = bpf_ktime_get_ns();
    e.event_type = 4;

    bpf_get_current_comm(&e.comm, sizeof(e.comm));
    bpf_probe_read_user_str(&e.filename, sizeof(e.filename), (void *)ctx->args[1]);
    get_container_id(e.container_id);

    bpf_perf_event_output(ctx, &file_events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

char _license[] SEC("license") = "GPL";
