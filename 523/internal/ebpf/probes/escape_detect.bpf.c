#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_core_read.h>

#define TASK_COMM_LEN 16
#define PATH_MAX 4096

struct event {
    u64 timestamp;
    u32 pid;
    u32 ppid;
    u32 uid;
    u32 gid;
    char comm[TASK_COMM_LEN];
    u64 pid_ns;
    u64 mnt_ns;
    u32 event_type;
    u64 syscall_nr;
    u64 args[6];
    s64 retval;
    char mount_source[256];
    char mount_target[256];
    char fs_type[32];
    u64 mount_flags;
    u32 cap_action;
    u32 cap_number;
    char file_name[256];
    u32 file_flags;
};

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __uint(key_size, sizeof(u32));
    __uint(value_size, sizeof(u32));
    __uint(max_entries, 1024);
} events SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, u32);
    __type(value, u64);
} pid_to_pidns SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, u32);
    __type(value, u64);
} pid_to_mntns SEC(".maps");

static __always_inline u64 get_current_pid_ns(void) {
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    u64 pid_ns = 0;
    BPF_CORE_READ_INTO(&pid_ns, task, nsproxy, pid_ns_for_children, ns.inum);
    return pid_ns;
}

static __always_inline u64 get_current_mnt_ns(void) {
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    u64 mnt_ns = 0;
    BPF_CORE_READ_INTO(&mnt_ns, task, nsproxy, mnt_ns, ns.inum);
    return mnt_ns;
}

static __always_inline void fill_common_fields(struct event *e, u32 event_type) {
    e->timestamp = bpf_ktime_get_ns();
    e->pid = bpf_get_current_pid_tgid() >> 32;
    e->ppid = BPF_CORE_READ((struct task_struct *)bpf_get_current_task(), real_parent, pid);
    e->uid = bpf_get_current_uid_gid() & 0xFFFFFFFF;
    e->gid = bpf_get_current_uid_gid() >> 32;
    bpf_get_current_comm(&e->comm, sizeof(e->comm));
    e->pid_ns = get_current_pid_ns();
    e->mnt_ns = get_current_mnt_ns();
    e->event_type = event_type;

    u32 pid = e->pid;
    u64 pidns = e->pid_ns;
    u64 mntns = e->mnt_ns;
    bpf_map_update_elem(&pid_to_pidns, &pid, &pidns, BPF_ANY);
    bpf_map_update_elem(&pid_to_mntns, &pid, &mntns, BPF_ANY);
}

SEC("tracepoint/syscalls/sys_enter_mount")
int tracepoint_sys_enter_mount(struct trace_event_raw_sys_enter *ctx) {
    struct event e = {};
    fill_common_fields(&e, 2);

    e.syscall_nr = 165;
    e.args[0] = ctx->args[0];
    e.args[1] = ctx->args[1];
    e.args[2] = ctx->args[2];
    e.args[3] = ctx->args[3];
    e.args[4] = ctx->args[4];

    const char *source = (const char *)ctx->args[0];
    const char *target = (const char *)ctx->args[1];
    const char *fstype = (const char *)ctx->args[2];
    e.mount_flags = ctx->args[3];

    if (source)
        bpf_probe_read_user_str(&e.mount_source, sizeof(e.mount_source), source);
    if (target)
        bpf_probe_read_user_str(&e.mount_target, sizeof(e.mount_target), target);
    if (fstype)
        bpf_probe_read_user_str(&e.fs_type, sizeof(e.fs_type), fstype);

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_exit_mount")
int tracepoint_sys_exit_mount(struct trace_event_raw_sys_exit *ctx) {
    struct event e = {};
    fill_common_fields(&e, 2);
    e.syscall_nr = 165;
    e.retval = ctx->ret;
    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_umount2")
int tracepoint_sys_enter_umount2(struct trace_event_raw_sys_enter *ctx) {
    struct event e = {};
    fill_common_fields(&e, 2);
    e.syscall_nr = 166;

    const char *target = (const char *)ctx->args[0];
    if (target)
        bpf_probe_read_user_str(&e.mount_target, sizeof(e.mount_target), target);

    e.mount_flags = ctx->args[1];
    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_chroot")
int tracepoint_sys_enter_chroot(struct trace_event_raw_sys_enter *ctx) {
    struct event e = {};
    fill_common_fields(&e, 1);
    e.syscall_nr = 161;

    const char *path = (const char *)ctx->args[0];
    if (path)
        bpf_probe_read_user_str(&e.file_name, sizeof(e.file_name), path);

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_pivot_root")
int tracepoint_sys_enter_pivot_root(struct trace_event_raw_sys_enter *ctx) {
    struct event e = {};
    fill_common_fields(&e, 1);
    e.syscall_nr = 155;

    const char *new_root = (const char *)ctx->args[0];
    const char *put_old = (const char *)ctx->args[1];

    if (new_root)
        bpf_probe_read_user_str(&e.mount_source, sizeof(e.mount_source), new_root);
    if (put_old)
        bpf_probe_read_user_str(&e.mount_target, sizeof(e.mount_target), put_old);

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_setns")
int tracepoint_sys_enter_setns(struct trace_event_raw_sys_enter *ctx) {
    struct event e = {};
    fill_common_fields(&e, 1);
    e.syscall_nr = 307;
    e.args[0] = ctx->args[0];
    e.args[1] = ctx->args[1];
    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_unshare")
int tracepoint_sys_enter_unshare(struct trace_event_raw_sys_enter *ctx) {
    struct event e = {};
    fill_common_fields(&e, 1);
    e.syscall_nr = 271;
    e.args[0] = ctx->args[0];
    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_ptrace")
int tracepoint_sys_enter_ptrace(struct trace_event_raw_sys_enter *ctx) {
    struct event e = {};
    fill_common_fields(&e, 1);
    e.syscall_nr = 101;
    e.args[0] = ctx->args[0];
    e.args[1] = ctx->args[1];
    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_init_module")
int tracepoint_sys_enter_init_module(struct trace_event_raw_sys_enter *ctx) {
    struct event e = {};
    fill_common_fields(&e, 1);
    e.syscall_nr = 175;
    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_delete_module")
int tracepoint_sys_enter_delete_module(struct trace_event_raw_sys_enter *ctx) {
    struct event e = {};
    fill_common_fields(&e, 1);
    e.syscall_nr = 176;
    const char *name = (const char *)ctx->args[0];
    if (name)
        bpf_probe_read_user_str(&e.file_name, sizeof(e.file_name), name);
    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_execve")
int tracepoint_sys_enter_execve(struct trace_event_raw_sys_enter *ctx) {
    struct event e = {};
    fill_common_fields(&e, 4);
    e.syscall_nr = 59;

    const char *filename = (const char *)ctx->args[0];
    if (filename)
        bpf_probe_read_user_str(&e.file_name, sizeof(e.file_name), filename);

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_openat")
int tracepoint_sys_enter_openat(struct trace_event_raw_sys_enter *ctx) {
    struct event e = {};
    fill_common_fields(&e, 5);
    e.syscall_nr = 257;

    const char *filename = (const char *)ctx->args[1];
    if (filename)
        bpf_probe_read_user_str(&e.file_name, sizeof(e.file_name), filename);
    e.file_flags = ctx->args[2];

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_mknod")
int tracepoint_sys_enter_mknod(struct trace_event_raw_sys_enter *ctx) {
    struct event e = {};
    fill_common_fields(&e, 1);
    e.syscall_nr = 133;

    const char *pathname = (const char *)ctx->args[0];
    if (pathname)
        bpf_probe_read_user_str(&e.file_name, sizeof(e.file_name), pathname);
    e.args[1] = ctx->args[1];
    e.args[2] = ctx->args[2];

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("kprobe/cap_capable")
int BPF_KPROBE(cap_capable, const struct cred *cred, u32 cap, int audit, int cap_opt) {
    struct event e = {};
    fill_common_fields(&e, 3);
    e.cap_action = 1;
    e.cap_number = cap;
    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

SEC("kprobe/commit_creds")
int BPF_KPROBE(commit_creds, const struct cred *new) {
    struct event e = {};
    fill_common_fields(&e, 3);
    e.cap_action = 2;

    kuid_t uid = BPF_CORE_READ(new, uid);
    kgid_t gid = BPF_CORE_READ(new, gid);
    kernel_cap_t cap_eff = BPF_CORE_READ(new, cap_effective);
    kernel_cap_t cap_perm = BPF_CORE_READ(new, cap_permitted);

    e.uid = uid.val;
    e.gid = gid.val;
    e.args[0] = cap_eff.val[0];
    e.args[1] = cap_perm.val[0];

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
