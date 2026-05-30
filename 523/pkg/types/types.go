package types

import (
	"time"
)

type EventType string

const (
	EventSyscall    EventType = "syscall"
	EventMount      EventType = "mount"
	EventCapability EventType = "capability"
	EventProcess    EventType = "process"
	EventFile       EventType = "file"
	EventNetwork    EventType = "network"
)

type RiskLevel string

const (
	RiskInfo     RiskLevel = "INFO"
	RiskLow      RiskLevel = "LOW"
	RiskMedium   RiskLevel = "MEDIUM"
	RiskHigh     RiskLevel = "HIGH"
	RiskCritical RiskLevel = "CRITICAL"
)

type ContainerInfo struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Image       string            `json:"image"`
	PID         int               `json:"pid"`
	PIDNS       uint64            `json:"pid_ns"`
	MNTNS       uint64            `json:"mnt_ns"`
	NETNS       uint64            `json:"net_ns"`
	UserNS      uint64            `json:"user_ns"`
	IPAddress   string            `json:"ip_address"`
	Privileged  bool              `json:"privileged"`
	Capabilities []string         `json:"capabilities"`
	Mounts      []MountPoint      `json:"mounts"`
	Labels      map[string]string `json:"labels"`
	CreatedAt   time.Time         `json:"created_at"`
}

type MountPoint struct {
	Source      string `json:"source"`
	Destination string `json:"destination"`
	Mode        string `json:"mode"`
	RW          bool   `json:"rw"`
	IsSensitive bool   `json:"is_sensitive"`
}

type ProcessInfo struct {
	PID          int       `json:"pid"`
	PPID         int       `json:"ppid"`
	Comm         string    `json:"comm"`
	Exe          string    `json:"exe"`
	CmdLine      []string  `json:"cmdline"`
	UID          uint32    `json:"uid"`
	GID          uint32    `json:"gid"`
	ContainerID  string    `json:"container_id"`
	StartTime    time.Time `json:"start_time"`
	CapEffective uint64    `json:"cap_effective"`
	CapPermitted uint64    `json:"cap_permitted"`
}

type BPFEvent struct {
	EventType   EventType `json:"event_type"`
	Timestamp   time.Time `json:"timestamp"`
	PID         uint32    `json:"pid"`
	PPID        uint32    `json:"ppid"`
	UID         uint32    `json:"uid"`
	GID         uint32    `json:"gid"`
	Comm        string    `json:"comm"`
	PIDNS       uint64    `json:"pid_ns"`
	MNTNS       uint64    `json:"mnt_ns"`

	SyscallNr   uint64   `json:"syscall_nr,omitempty"`
	SyscallName string   `json:"syscall_name,omitempty"`
	Args        []uint64 `json:"args,omitempty"`
	Retval      int64    `json:"retval,omitempty"`

	MountSource string `json:"mount_source,omitempty"`
	MountTarget string `json:"mount_target,omitempty"`
	MountFlags  uint64 `json:"mount_flags,omitempty"`
	FSType      string `json:"fs_type,omitempty"`

	CapAction   string `json:"cap_action,omitempty"`
	CapNumber   uint32 `json:"cap_number,omitempty"`
	CapName     string `json:"cap_name,omitempty"`

	FileName    string `json:"file_name,omitempty"`
	FileFlags   uint32 `json:"file_flags,omitempty"`
}

type BehaviorProfile struct {
	ContainerID   string    `json:"container_id"`
	ProcessTree   map[int]*ProcessNode `json:"process_tree"`
	SyscallFreq   map[string]int `json:"syscall_frequency"`
	MountHistory  []MountEvent `json:"mount_history"`
	CapUsage      map[string]int `json:"capability_usage"`
	FileAccess    map[string]int `json:"file_access"`
	FirstSeen     time.Time `json:"first_seen"`
	LastUpdated   time.Time `json:"last_updated"`
	RiskScore     float64   `json:"risk_score"`
	Whitelist     *MountWhitelist `json:"whitelist,omitempty"`
}

type ProcessNode struct {
	PID         int           `json:"pid"`
	PPID        int           `json:"ppid"`
	Comm        string        `json:"comm"`
	Exe         string        `json:"exe"`
	CmdLine     []string      `json:"cmdline"`
	Children    []*ProcessNode `json:"children"`
	IsSuspicious bool          `json:"is_suspicious"`
	RiskTags    []string      `json:"risk_tags"`
}

type MountEvent struct {
	Timestamp   time.Time `json:"timestamp"`
	Source      string    `json:"source"`
	Target      string    `json:"target"`
	Flags       uint64    `json:"flags"`
	PID         uint32    `json:"pid"`
	IsSuspicious bool     `json:"is_suspicious"`
	Reason      string    `json:"reason,omitempty"`
}

type DetectionRule struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Description string    `json:"description"`
	Severity    RiskLevel `json:"severity"`
	Category    string    `json:"category"`
	Condition   RuleCondition `json:"condition"`
	Score       float64   `json:"score"`
	Mitigation  string    `json:"mitigation"`
}

type RuleCondition struct {
	EventType  EventType            `json:"event_type"`
	Operator   string               `json:"operator"`
	Fields     map[string]string    `json:"fields"`
	Subrules   []RuleCondition      `json:"subrules,omitempty"`
}

type Alert struct {
	ID            string    `json:"id"`
	Timestamp     time.Time `json:"timestamp"`
	Severity      RiskLevel `json:"severity"`
	Title         string    `json:"title"`
	Description   string    `json:"description"`
	ContainerID   string    `json:"container_id"`
	ContainerName string    `json:"container_name"`
	ProcessPID    int       `json:"process_pid"`
	ProcessComm   string    `json:"process_comm"`
	RuleID        string    `json:"rule_id"`
	RiskScore     float64   `json:"risk_score"`
	Evidence      []string  `json:"evidence"`
	AttackPath    *AttackChain `json:"attack_path,omitempty"`
	Mitigation    string    `json:"mitigation"`
}

type AttackChain struct {
	ContainerID string        `json:"container_id"`
	Steps       []AttackStep  `json:"steps"`
	TotalScore  float64       `json:"total_score"`
	Description string        `json:"description"`
}

type AttackStep struct {
	Sequence    int       `json:"sequence"`
	Phase       string    `json:"phase"`
	Action      string    `json:"action"`
	PID         uint32    `json:"pid"`
	Comm        string    `json:"comm"`
	Timestamp   time.Time `json:"timestamp"`
	RiskScore   float64   `json:"risk_score"`
	Evidence    string    `json:"evidence"`
}

type RiskAssessment struct {
	ContainerID   string    `json:"container_id"`
	ContainerName string    `json:"container_name"`
	OverallScore  float64   `json:"overall_score"`
	RiskLevel     RiskLevel `json:"risk_level"`
	AlertsCount   map[RiskLevel]int `json:"alerts_count"`
	TopRisks      []Alert   `json:"top_risks"`
	AttackPaths   []AttackChain `json:"attack_paths"`
	LastUpdated   time.Time `json:"last_updated"`
}

const (
	CapChown          = 0
	CapDacOverride    = 1
	CapDacReadSearch  = 2
	CapFowner         = 3
	CapFsetid         = 4
	CapKill           = 5
	CapSetgid         = 6
	CapSetuid         = 7
	CapSetpcap        = 8
	CapLinuxImmutable = 9
	CapNetBindService = 10
	CapNetBroadcast   = 11
	CapNetAdmin       = 12
	CapNetRaw         = 13
	CapIpcLock        = 14
	CapIpcOwner       = 15
	CapSysModule      = 16
	CapSysRawio       = 17
	CapSysChroot      = 18
	CapSysPtrace      = 19
	CapSysPacct       = 20
	CapSysAdmin       = 21
	CapSysBoot        = 22
	CapSysNice        = 23
	CapSysResource    = 24
	CapSysTime        = 25
	CapSysTtyConfig   = 26
	CapMknod          = 27
	CapLease          = 28
	CapAuditWrite     = 29
	CapAuditControl   = 30
	CapSetfcap        = 31
	CapMacOverride    = 32
	CapMacAdmin       = 33
	CapSyslog         = 34
	CapWakeAlarm      = 35
	CapBlockSuspend   = 36
	CapAuditRead      = 37
	CapPernice        = 38
)

var CapabilityNames = map[uint32]string{
	0:  "CHOWN",
	1:  "DAC_OVERRIDE",
	2:  "DAC_READ_SEARCH",
	3:  "FOWNER",
	4:  "FSETID",
	5:  "KILL",
	6:  "SETGID",
	7:  "SETUID",
	8:  "SETPCAP",
	9:  "LINUX_IMMUTABLE",
	10: "NET_BIND_SERVICE",
	11: "NET_BROADCAST",
	12: "NET_ADMIN",
	13: "NET_RAW",
	14: "IPC_LOCK",
	15: "IPC_OWNER",
	16: "SYS_MODULE",
	17: "SYS_RAWIO",
	18: "SYS_CHROOT",
	19: "SYS_PTRACE",
	20: "SYS_PACCT",
	21: "SYS_ADMIN",
	22: "SYS_BOOT",
	23: "SYS_NICE",
	24: "SYS_RESOURCE",
	25: "SYS_TIME",
	26: "SYS_TTY_CONFIG",
	27: "MKNOD",
	28: "LEASE",
	29: "AUDIT_WRITE",
	30: "AUDIT_CONTROL",
	31: "SETFCAP",
	32: "MAC_OVERRIDE",
	33: "MAC_ADMIN",
	34: "SYSLOG",
	35: "WAKE_ALARM",
	36: "BLOCK_SUSPEND",
	37: "AUDIT_READ",
	38: "PERNICE",
}

var SyscallNames = map[uint64]string{
	0:   "read",
	1:   "write",
	2:   "open",
	3:   "close",
	4:   "stat",
	5:   "fstat",
	6:   "lstat",
	7:   "poll",
	8:   "lseek",
	9:   "mmap",
	10:  "mprotect",
	11:  "munmap",
	12:  "brk",
	13:  "rt_sigaction",
	14:  "rt_sigprocmask",
	15:  "rt_sigreturn",
	16:  "ioctl",
	17:  "pread64",
	18:  "pwrite64",
	19:  "readv",
	20:  "writev",
	21:  "access",
	22:  "pipe",
	23:  "select",
	24:  "sched_yield",
	25:  "mremap",
	26:  "msync",
	27:  "mincore",
	28:  "madvise",
	29:  "shmget",
	30:  "shmat",
	31:  "shmctl",
	32:  "dup",
	33:  "dup2",
	34:  "pause",
	35:  "nanosleep",
	36:  "getitimer",
	37:  "alarm",
	38:  "setitimer",
	39:  "getpid",
	40:  "sendfile",
	41:  "socket",
	42:  "connect",
	43:  "accept",
	44:  "sendto",
	45:  "recvfrom",
	46:  "sendmsg",
	47:  "recvmsg",
	48:  "shutdown",
	49:  "bind",
	50:  "listen",
	51:  "getsockname",
	52:  "getpeername",
	53:  "socketpair",
	54:  "setsockopt",
	55:  "getsockopt",
	56:  "clone",
	57:  "fork",
	58:  "vfork",
	59:  "execve",
	60:  "exit",
	61:  "wait4",
	62:  "kill",
	63:  "uname",
	64:  "semget",
	65:  "semop",
	66:  "semctl",
	67:  "shmdt",
	68:  "msgget",
	69:  "msgsnd",
	70:  "msgrcv",
	71:  "msgctl",
	72:  "fcntl",
	73:  "flock",
	74:  "fsync",
	75:  "fdatasync",
	76:  "truncate",
	77:  "ftruncate",
	78:  "getdents",
	79:  "getcwd",
	80:  "chdir",
	81:  "fchdir",
	82:  "rename",
	83:  "mkdir",
	84:  "rmdir",
	85:  "creat",
	86:  "link",
	87:  "unlink",
	88:  "symlink",
	89:  "readlink",
	90:  "chmod",
	91:  "fchmod",
	92:  "chown",
	93:  "fchown",
	94:  "lchown",
	95:  "umask",
	96:  "gettimeofday",
	97:  "getrlimit",
	98:  "getrusage",
	99:  "sysinfo",
	100: "times",
	101: "ptrace",
	102: "getuid",
	103: "syslog",
	104: "getgid",
	105: "setuid",
	106: "setgid",
	107: "geteuid",
	108: "getegid",
	109: "setpgid",
	110: "getppid",
	111: "getpgrp",
	112: "setsid",
	113: "setreuid",
	114: "setregid",
	115: "getgroups",
	116: "setgroups",
	117: "setresuid",
	118: "getresuid",
	119: "setresgid",
	120: "getresgid",
	121: "getpgid",
	122: "setfsuid",
	123: "setfsgid",
	124: "getsid",
	125: "capget",
	126: "capset",
	127: "rt_sigpending",
	128: "rt_sigtimedwait",
	129: "rt_sigqueueinfo",
	130: "rt_sigsuspend",
	131: "sigaltstack",
	132: "utime",
	133: "mknod",
	134: "uselib",
	135: "personality",
	136: "ustat",
	137: "statfs",
	138: "fstatfs",
	139: "sysfs",
	140: "getpriority",
	141: "setpriority",
	142: "sched_setparam",
	143: "sched_getparam",
	144: "sched_setscheduler",
	145: "sched_getscheduler",
	146: "sched_get_priority_max",
	147: "sched_get_priority_min",
	148: "sched_rr_get_interval",
	149: "mlock",
	150: "munlock",
	151: "mlockall",
	152: "munlockall",
	153: "vhangup",
	154: "modify_ldt",
	155: "pivot_root",
	156: "_sysctl",
	157: "prctl",
	158: "arch_prctl",
	159: "adjtimex",
	160: "setrlimit",
	161: "chroot",
	162: "sync",
	163: "acct",
	164: "settimeofday",
	165: "mount",
	166: "umount2",
	167: "swapon",
	168: "swapoff",
	169: "reboot",
	170: "sethostname",
	171: "setdomainname",
	172: "iopl",
	173: "ioperm",
	174: "create_module",
	175: "init_module",
	176: "delete_module",
	177: "get_kernel_syms",
	178: "query_module",
	179: "quotactl",
	180: "nfsservctl",
	181: "getpmsg",
	182: "putpmsg",
	183: "afs_syscall",
	184: "tuxcall",
	185: "security",
	186: "gettid",
	187: "readahead",
	188: "setxattr",
	189: "lsetxattr",
	190: "fsetxattr",
	191: "getxattr",
	192: "lgetxattr",
	193: "fgetxattr",
	194: "listxattr",
	195: "llistxattr",
	196: "flistxattr",
	197: "removexattr",
	198: "lremovexattr",
	199: "fremovexattr",
	200: "tkill",
	201: "time",
	202: "futex",
	203: "sched_setaffinity",
	204: "sched_getaffinity",
	205: "set_thread_area",
	206: "io_setup",
	207: "io_destroy",
	208: "io_getevents",
	209: "io_submit",
	210: "io_cancel",
	211: "get_thread_area",
	212: "lookup_dcookie",
	213: "epoll_create",
	214: "epoll_ctl_old",
	215: "epoll_wait_old",
	216: "remap_file_pages",
	217: "getdents64",
	218: "set_tid_address",
	219: "restart_syscall",
	220: "semtimedop",
	221: "fadvise64",
	222: "timer_create",
	223: "timer_settime",
	224: "timer_gettime",
	225: "timer_delete",
	226: "clock_settime",
	227: "clock_gettime",
	228: "clock_getres",
	229: "clock_nanosleep",
	230: "exit_group",
	231: "epoll_wait",
	232: "epoll_ctl",
	233: "tgkill",
	234: "utimes",
	235: "vserver",
	236: "mbind",
	237: "set_mempolicy",
	238: "get_mempolicy",
	239: "mq_open",
	240: "mq_unlink",
	241: "mq_timedsend",
	242: "mq_timedreceive",
	243: "mq_notify",
	244: "mq_getsetattr",
	245: "kexec_load",
	246: "waitid",
	247: "add_key",
	248: "request_key",
	249: "keyctl",
	250: "ioprio_set",
	251: "ioprio_get",
	252: "inotify_init",
	253: "inotify_add_watch",
	254: "inotify_rm_watch",
	255: "migrate_pages",
	256: "openat",
	257: "mkdirat",
	258: "mknodat",
	259: "fchownat",
	260: "futimesat",
	261: "newfstatat",
	262: "unlinkat",
	263: "renameat",
	264: "linkat",
	265: "symlinkat",
	266: "readlinkat",
	267: "fchmodat",
	268: "faccessat",
	269: "pselect6",
	270: "ppoll",
	271: "unshare",
	272: "set_robust_list",
	273: "get_robust_list",
	274: "splice",
	275: "tee",
	276: "sync_file_range",
	277: "vmsplice",
	278: "move_pages",
	279: "utimensat",
	280: "epoll_pwait",
	281: "signalfd",
	282: "timerfd_create",
	283: "eventfd",
	284: "fallocate",
	285: "timerfd_settime",
	286: "timerfd_gettime",
	287: "accept4",
	288: "signalfd4",
	289: "eventfd2",
	290: "epoll_create1",
	291: "dup3",
	292: "pipe2",
	293: "inotify_init1",
	294: "preadv",
	295: "pwritev",
	296: "rt_tgsigqueueinfo",
	297: "perf_event_open",
	298: "recvmmsg",
	299: "fanotify_init",
	300: "fanotify_mark",
	301: "prlimit64",
	302: "name_to_handle_at",
	303: "open_by_handle_at",
	304: "clock_adjtime",
	305: "syncfs",
	306: "sendmmsg",
	307: "setns",
	308: "getcpu",
	309: "process_vm_readv",
	310: "process_vm_writev",
	311: "kcmp",
	312: "finit_module",
	313: "sched_setattr",
	314: "sched_getattr",
	315: "renameat2",
	316: "seccomp",
	317: "getrandom",
	318: "memfd_create",
	319: "kexec_file_load",
	320: "bpf",
	321: "execveat",
	322: "userfaultfd",
	323: "membarrier",
	324: "mlock2",
	325: "copy_file_range",
	326: "preadv2",
	327: "pwritev2",
	328: "pkey_mprotect",
	329: "pkey_alloc",
	330: "pkey_free",
	331: "statx",
	332: "io_pgetevents",
	333: "rseq",
}

var SensitivePaths = []string{
	"/proc",
	"/sys",
	"/dev",
	"/var/run/docker.sock",
	"/var/lib/docker",
	"/etc",
	"/root",
	"/home",
	"/boot",
	"/usr/bin",
	"/usr/sbin",
	"/lib",
	"/lib64",
}

type MountWhitelist struct {
	Paths             []MountWhitelistEntry `json:"paths" yaml:"paths"`
	ContainerPatterns []string              `json:"container_patterns" yaml:"container_patterns"`
}

type MountWhitelistEntry struct {
	Source      string `json:"source" yaml:"source"`
	Target      string `json:"target" yaml:"target"`
	FSType      string `json:"fs_type,omitempty" yaml:"fs_type,omitempty"`
	Description string `json:"description,omitempty" yaml:"description,omitempty"`
}

var DangerousSyscalls = map[uint64]string{
	105: "setuid",
	106: "setgid",
	165: "mount",
	166: "umount2",
	161: "chroot",
	101: "ptrace",
	175: "init_module",
	176: "delete_module",
	155: "pivot_root",
	271: "unshare",
	307: "setns",
	169: "reboot",
	170: "sethostname",
	172: "iopl",
	173: "ioperm",
	159: "adjtimex",
	164: "settimeofday",
	127: "mknod",
	320: "bpf",
}
