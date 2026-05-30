package behavior

import (
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/security/container-escape-detector/pkg/types"
)

type Config struct {
	BaselineMode        bool
	BaselineDuration    int
	AnomalyThreshold    float64
	ProcessTreeDepth    int
	MaxHistorySize      int
}

type Analyzer struct {
	profiles     map[string]*types.BehaviorProfile
	mu           sync.RWMutex
	logger       *logrus.Logger
	baselineMode bool
	baselineEnd  time.Time
	thresholds   *DetectionThresholds
	config       *Config
	whitelist    *types.MountWhitelist
}

type DetectionThresholds struct {
	SyscallAnomalyScore   float64
	ProcessAnomalyScore   float64
	MountSuspiciousScore  float64
	CapAbuseScore         float64
	FileAccessScore       float64
	OverallRiskThreshold  float64
}

func DefaultThresholds() *DetectionThresholds {
	return &DetectionThresholds{
		SyscallAnomalyScore:   5.0,
		ProcessAnomalyScore:   10.0,
		MountSuspiciousScore:  15.0,
		CapAbuseScore:         20.0,
		FileAccessScore:       8.0,
		OverallRiskThreshold:  25.0,
	}
}

func NewAnalyzer(logger *logrus.Logger, config *Config) *Analyzer {
	if config == nil {
		config = &Config{
			BaselineMode:     false,
			BaselineDuration: 300,
			AnomalyThreshold: 2.0,
			ProcessTreeDepth: 10,
			MaxHistorySize:   10000,
		}
	}

	baselineEnd := time.Time{}
	if config.BaselineMode {
		baselineEnd = time.Now().Add(time.Duration(config.BaselineDuration) * time.Second)
	}

	return &Analyzer{
		profiles:     make(map[string]*types.BehaviorProfile),
		logger:       logger,
		baselineMode: config.BaselineMode,
		baselineEnd:  baselineEnd,
		thresholds:   DefaultThresholds(),
		config:       config,
	}
}

func (a *Analyzer) Analyze(event *types.BPFEvent, container *types.ContainerInfo) *types.BehaviorProfile {
	return a.ProcessEvent(event, container)
}

func (a *Analyzer) ProcessEvent(event *types.BPFEvent, container *types.ContainerInfo) *types.BehaviorProfile {
	if container == nil {
		return nil
	}

	containerID := container.ID

	a.mu.Lock()
	defer a.mu.Unlock()

	profile, exists := a.profiles[containerID]
	if !exists {
		profile = a.createProfile(containerID)
		a.profiles[containerID] = profile
	}

	a.updateProfile(profile, event, container)
	profile.LastUpdated = time.Now()

	return profile
}

func (a *Analyzer) createProfile(containerID string) *types.BehaviorProfile {
	return &types.BehaviorProfile{
		ContainerID:  containerID,
		ProcessTree:  make(map[int]*types.ProcessNode),
		SyscallFreq:  make(map[string]int),
		MountHistory: make([]types.MountEvent, 0),
		CapUsage:     make(map[string]int),
		FileAccess:   make(map[string]int),
		FirstSeen:    time.Now(),
		LastUpdated:  time.Now(),
		RiskScore:    0.0,
	}
}

func (a *Analyzer) updateProfile(profile *types.BehaviorProfile, event *types.BPFEvent, container *types.ContainerInfo) {
	pid := int(event.PID)
	ppid := int(event.PPID)

	node, exists := profile.ProcessTree[pid]
	if !exists {
		node = &types.ProcessNode{
			PID:         pid,
			PPID:        ppid,
			Comm:        event.Comm,
			Children:    make([]*types.ProcessNode, 0),
			RiskTags:    make([]string, 0),
		}
		profile.ProcessTree[pid] = node

		if parent, ok := profile.ProcessTree[ppid]; ok {
			parent.Children = append(parent.Children, node)
		}
	}

	node.Comm = event.Comm

	switch event.EventType {
	case types.EventSyscall:
		a.analyzeSyscall(profile, event, node, container)

	case types.EventMount:
		a.analyzeMount(profile, event, node)

	case types.EventCapability:
		a.analyzeCapability(profile, event, node)

	case types.EventProcess:
		a.analyzeProcess(profile, event, node)

	case types.EventFile:
		a.analyzeFileAccess(profile, event, node)
	}

	profile.RiskScore = a.calculateOverallRisk(profile)
}

func (a *Analyzer) analyzeSyscall(profile *types.BehaviorProfile, event *types.BPFEvent, node *types.ProcessNode, container *types.ContainerInfo) {
	if event.SyscallName == "" {
		event.SyscallName = types.SyscallNames[event.SyscallNr]
	}

	profile.SyscallFreq[event.SyscallName]++

	if a.isDangerousSyscall(event.SyscallNr) {
		score := a.getDangerousSyscallScore(event.SyscallNr)
		a.addRiskTag(node, fmt.Sprintf("dangerous_syscall:%s", event.SyscallName), score)

		if event.SyscallNr == 165 || event.SyscallNr == 166 {
			a.addRiskTag(node, "mount_syscall_used", 15.0)
		}

		if event.SyscallNr == 101 {
			a.addRiskTag(node, "ptrace_used", 20.0)
		}

		if event.SyscallNr == 175 || event.SyscallNr == 176 {
			a.addRiskTag(node, "kernel_module_operation", 30.0)
		}

		if event.SyscallNr == 307 {
			a.addRiskTag(node, "setns_used", 25.0)
		}

		if event.SyscallNr == 271 {
			a.addRiskTag(node, "unshare_used", 20.0)
		}
	}

	if !a.baselineMode || time.Now().After(a.baselineEnd) {
		if profile.SyscallFreq[event.SyscallName] == 1 && a.isRareSyscall(event.SyscallName) {
			a.addRiskTag(node, fmt.Sprintf("rare_syscall:%s", event.SyscallName), 5.0)
		}
	}
}

func (a *Analyzer) analyzeMount(profile *types.BehaviorProfile, event *types.BPFEvent, node *types.ProcessNode) {
	mountEvent := types.MountEvent{
		Timestamp:  event.Timestamp,
		Source:     event.MountSource,
		Target:     event.MountTarget,
		Flags:      event.MountFlags,
		PID:        event.PID,
	}

	if a.IsWhitelistedMount(event) {
		profile.MountHistory = append(profile.MountHistory, mountEvent)
		return
	}

	if a.isSensitiveMount(event) {
		mountEvent.IsSuspicious = true
		mountEvent.Reason = a.getSuspiciousMountReason(event)
		a.addRiskTag(node, "sensitive_mount", a.thresholds.MountSuspiciousScore)

		if strings.Contains(event.MountTarget, "/proc") || strings.Contains(event.MountSource, "/proc") {
			a.addRiskTag(node, "proc_mount_attempt", 25.0)
		}

		if strings.Contains(event.MountTarget, "/sys") || strings.Contains(event.MountSource, "/sys") {
			a.addRiskTag(node, "sys_mount_attempt", 25.0)
		}

		if strings.Contains(event.MountSource, "/var/run/docker.sock") {
			a.addRiskTag(node, "docker_socket_mount", 40.0)
		}

		if event.MountFlags&0x20 != 0 {
			a.addRiskTag(node, "read_write_mount", 10.0)
		}
	}

	profile.MountHistory = append(profile.MountHistory, mountEvent)
}

func (a *Analyzer) analyzeCapability(profile *types.BehaviorProfile, event *types.BPFEvent, node *types.ProcessNode) {
	if event.CapName == "" {
		event.CapName = types.CapabilityNames[event.CapNumber]
	}

	profile.CapUsage[event.CapName]++

	if a.isDangerousCapability(event.CapNumber) {
		a.addRiskTag(node, fmt.Sprintf("capability_used:%s", event.CapName), a.thresholds.CapAbuseScore)

		if event.CapNumber == types.CapSysAdmin {
			a.addRiskTag(node, "sys_admin_cap_used", 35.0)
		}

		if event.CapNumber == types.CapSysModule {
			a.addRiskTag(node, "sys_module_cap_used", 40.0)
		}

		if event.CapNumber == types.CapSysPtrace {
			a.addRiskTag(node, "sys_ptrace_cap_used", 30.0)
		}

		if event.CapNumber == types.CapNetAdmin {
			a.addRiskTag(node, "net_admin_cap_used", 25.0)
		}

		if event.CapNumber == types.CapSysRawio {
			a.addRiskTag(node, "sys_rawio_cap_used", 35.0)
		}
	}

	if event.CapAction == "commit_creds" {
		if event.UID == 0 || event.GID == 0 {
			a.addRiskTag(node, "privilege_escalation_detected", 45.0)
		}
	}
}

func (a *Analyzer) analyzeProcess(profile *types.BehaviorProfile, event *types.BPFEvent, node *types.ProcessNode) {
	node.Exe = event.FileName
	node.CmdLine = strings.Split(event.FileName, " ")

	if a.isSuspiciousProcess(event.FileName, event.Comm) {
		a.addRiskTag(node, fmt.Sprintf("suspicious_process:%s", event.Comm), a.thresholds.ProcessAnomalyScore)
	}

	if event.UID == 0 && event.Comm != "bash" && event.Comm != "sh" {
		a.addRiskTag(node, "root_process_spawn", 15.0)
	}

	if a.isShellProcess(event.Comm) {
		a.addRiskTag(node, "shell_spawned_in_container", 10.0)
	}

	if a.isDebuggingTool(event.Comm) {
		a.addRiskTag(node, fmt.Sprintf("debugging_tool_used:%s", event.Comm), 20.0)
	}
}

func (a *Analyzer) analyzeFileAccess(profile *types.BehaviorProfile, event *types.BPFEvent, node *types.ProcessNode) {
	if event.FileName != "" {
		profile.FileAccess[event.FileName]++

		if a.isSensitiveFilePath(event.FileName) {
			a.addRiskTag(node, fmt.Sprintf("sensitive_file_access:%s", event.FileName), a.thresholds.FileAccessScore)
		}

		if strings.Contains(event.FileName, "/var/run/docker.sock") {
			a.addRiskTag(node, "docker_socket_access", 50.0)
		}

		if strings.Contains(event.FileName, "/proc/sys") || strings.Contains(event.FileName, "/sys/kernel") {
			a.addRiskTag(node, "kernel_parameter_access", 30.0)
		}

		if strings.Contains(event.FileName, "/dev/") && (strings.Contains(event.FileName, "sda") || strings.Contains(event.FileName, "nvme")) {
			a.addRiskTag(node, "raw_disk_access", 40.0)
		}

		if event.FileFlags&01 != 0 || event.FileFlags&0200000 != 0 {
			if a.isSensitiveFilePath(event.FileName) {
				a.addRiskTag(node, "sensitive_file_write", 25.0)
			}
		}
	}
}

func (a *Analyzer) addRiskTag(node *types.ProcessNode, tag string, score float64) {
	node.IsSuspicious = true
	for _, existing := range node.RiskTags {
		if existing == tag {
			return
		}
	}
	node.RiskTags = append(node.RiskTags, tag)
}

func (a *Analyzer) isDangerousSyscall(syscallNr uint64) bool {
	_, exists := types.DangerousSyscalls[syscallNr]
	return exists
}

func (a *Analyzer) getDangerousSyscallScore(syscallNr uint64) float64 {
	highRisk := map[uint64]bool{
		165: true,
		175: true,
		176: true,
		307: true,
		101: true,
	}
	if highRisk[syscallNr] {
		return 20.0
	}
	return 10.0
}

func (a *Analyzer) isRareSyscall(name string) bool {
	commonSyscalls := map[string]bool{
		"read":    true,
		"write":   true,
		"open":    true,
		"openat":  true,
		"close":   true,
		"mmap":    true,
		"mprotect": true,
		"munmap":  true,
		"brk":     true,
		"ioctl":   true,
		"pread64": true,
		"pwrite64": true,
		"fstat":   true,
		"lseek":   true,
		"poll":    true,
		"access":  true,
		"select":  true,
		"rt_sigprocmask": true,
		"rt_sigaction":  true,
		"exit_group":    true,
		"futex":         true,
		"getpid":        true,
		"getdents64":    true,
		"stat":          true,
		"lstat":         true,
		"execve":        true,
		"clone":         true,
		"wait4":         true,
		"kill":          true,
		"pipe":          true,
		"dup2":          true,
		"fcntl":         true,
		"chdir":         true,
		"getcwd":        true,
		"readlink":      true,
		"sysinfo":       true,
		"uname":         true,
		"arch_prctl":    true,
		"getrlimit":     true,
		"setrlimit":     true,
		"prctl":         true,
		"shutdown":      true,
	}
	return !commonSyscalls[name]
}

func (a *Analyzer) isSensitiveMount(event *types.BPFEvent) bool {
	for _, sp := range types.SensitivePaths {
		if strings.HasPrefix(event.MountSource, sp) || strings.HasPrefix(event.MountTarget, sp) {
			return true
		}
	}

	if strings.Contains(event.MountSource, "docker") || strings.Contains(event.MountSource, "containerd") {
		return true
	}

	if strings.Contains(event.FSType, "cgroup") || strings.Contains(event.FSType, "proc") || strings.Contains(event.FSType, "sysfs") {
		return true
	}

	return false
}

func (a *Analyzer) IsWhitelistedMount(event *types.BPFEvent) bool {
	if a.whitelist == nil {
		return false
	}

	for _, entry := range a.whitelist.Paths {
		sourceMatch := entry.Source == event.MountSource
		targetMatch := entry.Target == event.MountTarget
		fsMatch := entry.FSType == "" || entry.FSType == event.FSType

		if sourceMatch && targetMatch && fsMatch {
			return true
		}
	}

	return false
}

func (a *Analyzer) SetMountWhitelist(whitelist *types.MountWhitelist) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.whitelist = whitelist
}

func (a *Analyzer) getSuspiciousMountReason(event *types.BPFEvent) string {
	var reasons []string

	for _, sp := range types.SensitivePaths {
		if strings.HasPrefix(event.MountSource, sp) {
			reasons = append(reasons, fmt.Sprintf("source_matches_sensitive_path:%s", sp))
		}
		if strings.HasPrefix(event.MountTarget, sp) {
			reasons = append(reasons, fmt.Sprintf("target_matches_sensitive_path:%s", sp))
		}
	}

	if strings.Contains(event.MountSource, "docker.sock") {
		reasons = append(reasons, "docker_socket_mount")
	}

	return strings.Join(reasons, ",")
}

func (a *Analyzer) isDangerousCapability(capNr uint32) bool {
	dangerousCaps := map[uint32]bool{
		types.CapSysAdmin:    true,
		types.CapSysModule:   true,
		types.CapSysPtrace:   true,
		types.CapSysRawio:    true,
		types.CapNetAdmin:    true,
		types.CapSysChroot:   true,
		types.CapSysBoot:     true,
		types.CapSysPacct:    true,
		types.CapSysAdmin:    true,
		types.CapMknod:       true,
		types.CapSysResource: true,
		types.CapSysTime:     true,
		types.CapSetfcap:     true,
		types.CapAuditControl: true,
		types.CapMacAdmin:    true,
	}
	return dangerousCaps[capNr]
}

func (a *Analyzer) isSuspiciousProcess(filename, comm string) bool {
	suspicious := []string{
		"nmap", "masscan", "metasploit", "msfconsole", "nc", "netcat",
		"ncat", "socat", "cryptsetup", "truecrypt", "veracrypt",
		"chroot", "pivot_root", "unshare", "nsenter",
	}

	for _, s := range suspicious {
		if strings.Contains(strings.ToLower(filename), s) || strings.Contains(strings.ToLower(comm), s) {
			return true
		}
	}
	return false
}

func (a *Analyzer) isShellProcess(comm string) bool {
	shells := map[string]bool{
		"bash": true, "sh": true, "zsh": true, "ksh": true,
		"csh": true, "tcsh": true, "fish": true, "dash": true,
	}
	return shells[comm]
}

func (a *Analyzer) isDebuggingTool(comm string) bool {
	tools := map[string]bool{
		"gdb":    true, "strace": true, "ltrace": true,
		"objdump": true, "readelf": true, "nm": true,
		"tcpdump": true, "wireshark": true, "tshark": true,
	}
	return tools[comm]
}

func (a *Analyzer) isSensitiveFilePath(path string) bool {
	for _, sp := range types.SensitivePaths {
		if strings.HasPrefix(path, sp) {
			return true
		}
	}

	sensitivePatterns := []string{
		".ssh/id_", ".docker/config.json", ".kube/config",
		"/etc/shadow", "/etc/passwd", "/etc/sudoers",
	}

	for _, sp := range sensitivePatterns {
		if strings.Contains(path, sp) {
			return true
		}
	}

	return false
}

func (a *Analyzer) calculateOverallRisk(profile *types.BehaviorProfile) float64 {
	var totalRisk float64

	for _, node := range profile.ProcessTree {
		if node.IsSuspicious {
			totalRisk += float64(len(node.RiskTags)) * 10.0
		}
	}

	for _, mountEvent := range profile.MountHistory {
		if mountEvent.IsSuspicious {
			totalRisk += a.thresholds.MountSuspiciousScore
		}
	}

	for capName, count := range profile.CapUsage {
		if count > 0 && a.isDangerousCapabilityByName(capName) {
			totalRisk += a.thresholds.CapAbuseScore * float64(count)
		}
	}

	return totalRisk
}

func (a *Analyzer) isDangerousCapabilityByName(name string) bool {
	for capNum, capName := range types.CapabilityNames {
		if capName == name && a.isDangerousCapability(capNum) {
			return true
		}
	}
	return false
}

func (a *Analyzer) GetProfile(containerID string) (*types.BehaviorProfile, bool) {
	a.mu.RLock()
	defer a.mu.RUnlock()

	profile, exists := a.profiles[containerID]
	return profile, exists
}

func (a *Analyzer) GetAllProfiles() []*types.BehaviorProfile {
	a.mu.RLock()
	defer a.mu.RUnlock()

	profiles := make([]*types.BehaviorProfile, 0, len(a.profiles))
	for _, p := range a.profiles {
		profiles = append(profiles, p)
	}
	return profiles
}

func (a *Analyzer) IsBaselineMode() bool {
	return a.baselineMode && time.Now().Before(a.baselineEnd)
}

func (a *Analyzer) GetRiskLevel(score float64) types.RiskLevel {
	switch {
	case score >= 100.0:
		return types.RiskCritical
	case score >= 50.0:
		return types.RiskHigh
	case score >= 25.0:
		return types.RiskMedium
	case score >= 10.0:
		return types.RiskLow
	default:
		return types.RiskInfo
	}
}

func (a *Analyzer) CleanupOldProfiles(maxAge time.Duration) {
	a.mu.Lock()
	defer a.mu.Unlock()

	cutoff := time.Now().Add(-maxAge)
	for id, profile := range a.profiles {
		if profile.LastUpdated.Before(cutoff) {
			delete(a.profiles, id)
		}
	}
}

func (a *Analyzer) GetProcessNode(containerID string, pid int) (*types.ProcessNode, bool) {
	a.mu.RLock()
	defer a.mu.RUnlock()

	profile, exists := a.profiles[containerID]
	if !exists {
		return nil, false
	}

	node, exists := profile.ProcessTree[pid]
	return node, exists
}

func (a *Analyzer) GetProcessRoot(containerID string, pid int) *types.ProcessNode {
	a.mu.RLock()
	defer a.mu.RUnlock()

	profile, exists := a.profiles[containerID]
	if !exists {
		return nil
	}

	node, exists := profile.ProcessTree[pid]
	if !exists {
		return nil
	}

	for {
		parent, exists := profile.ProcessTree[node.PPID]
		if !exists || parent.PID == node.PID {
			break
		}
		node = parent
	}

	return node
}
