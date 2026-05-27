package detector

import (
	"bytes"
	"fmt"
	"net"
	"strings"
	"sync"
	"time"

	"container-security-monitor/pkg/config"
	"container-security-monitor/pkg/ebpf"
	"container-security-monitor/pkg/rules"
)

type SecurityAlert struct {
	RuleName    string                 `json:"rule_name"`
	Severity    string                 `json:"severity"`
	Message     string                 `json:"message"`
	Remediation string                 `json:"remediation"`
	ContainerID string                 `json:"container_id"`
	PID         uint32                 `json:"pid"`
	PPID        uint32                 `json:"ppid"`
	UID         uint32                 `json:"uid"`
	Comm        string                 `json:"comm"`
	Timestamp   time.Time              `json:"timestamp"`
	Tags        []string               `json:"tags"`
	Fields      map[string]interface{} `json:"fields"`
	Blocked     bool                   `json:"blocked"`
}

type WhitelistManager struct {
	mu        sync.RWMutex
	processes map[string]config.ProcessWhitelist
	networks  map[string]config.NetworkWhitelist
}

func NewWhitelistManager(whitelistCfg config.WhitelistConfig) *WhitelistManager {
	wm := &WhitelistManager{
		processes: make(map[string]config.ProcessWhitelist),
		networks:  make(map[string]config.NetworkWhitelist),
	}

	for _, p := range whitelistCfg.Processes {
		key := fmt.Sprintf("%s:%s", p.Comm, p.ContainerID)
		wm.processes[key] = p
	}

	for _, n := range whitelistCfg.Networks {
		key := fmt.Sprintf("%s:%d:%s:%s", n.IP, n.Port, n.Protocol, n.ContainerID)
		wm.networks[key] = n
	}

	return wm
}

func (wm *WhitelistManager) IsProcessWhitelisted(comm, containerID string) bool {
	wm.mu.RLock()
	defer wm.mu.RUnlock()

	key := fmt.Sprintf("%s:%s", comm, containerID)
	if _, ok := wm.processes[key]; ok {
		return true
	}

	genericKey := fmt.Sprintf("%s:*", comm)
	if _, ok := wm.processes[genericKey]; ok {
		return true
	}

	return false
}

func (wm *WhitelistManager) IsNetworkWhitelisted(ip string, port uint16, protocol, containerID string) bool {
	wm.mu.RLock()
	defer wm.mu.RUnlock()

	key := fmt.Sprintf("%s:%d:%s:%s", ip, port, protocol, containerID)
	if _, ok := wm.networks[key]; ok {
		return true
	}

	genericKey := fmt.Sprintf("%s:*:%s:%s", ip, protocol, containerID)
	if _, ok := wm.networks[genericKey]; ok {
		return true
	}

	ipGeneric := fmt.Sprintf("%s:%d:%s:*", ip, port, protocol)
	if _, ok := wm.networks[ipGeneric]; ok {
		return true
	}

	return false
}

func (wm *WhitelistManager) AddProcessWhitelist(w config.ProcessWhitelist) {
	wm.mu.Lock()
	defer wm.mu.Unlock()

	key := fmt.Sprintf("%s:%s", w.Comm, w.ContainerID)
	wm.processes[key] = w
}

func (wm *WhitelistManager) AddNetworkWhitelist(w config.NetworkWhitelist) {
	wm.mu.Lock()
	defer wm.mu.Unlock()

	key := fmt.Sprintf("%s:%d:%s:%s", w.IP, w.Port, w.Protocol, w.ContainerID)
	wm.networks[key] = w
}

func (wm *WhitelistManager) RemoveProcessWhitelist(comm, containerID string) {
	wm.mu.Lock()
	defer wm.mu.Unlock()

	key := fmt.Sprintf("%s:%s", comm, containerID)
	delete(wm.processes, key)
}

func (wm *WhitelistManager) RemoveNetworkWhitelist(ip string, port uint16, protocol, containerID string) {
	wm.mu.Lock()
	defer wm.mu.Unlock()

	key := fmt.Sprintf("%s:%d:%s:%s", ip, port, protocol, containerID)
	delete(wm.networks, key)
}

type Detector struct {
	ruleEngine *rules.Engine
	whitelist  *WhitelistManager
}

func NewDetector(ruleEngine *rules.Engine, whitelistCfg config.WhitelistConfig) *Detector {
	return &Detector{
		ruleEngine: ruleEngine,
		whitelist:  NewWhitelistManager(whitelistCfg),
	}
}

func NewDetectorWithWhitelist(ruleEngine *rules.Engine, whitelist *WhitelistManager) *Detector {
	return &Detector{
		ruleEngine: ruleEngine,
		whitelist:  whitelist,
	}
}

func (d *Detector) ProcessEvent(event interface{}) []*SecurityAlert {
	var alerts []*SecurityAlert

	switch e := event.(type) {
	case ebpf.ProcessEvent:
		alerts = d.processProcessEvent(e)
	case ebpf.FileEvent:
		alerts = d.processFileEvent(e)
	case ebpf.NetworkEvent:
		alerts = d.processNetworkEvent(e)
	}

	return alerts
}

func (d *Detector) processProcessEvent(event ebpf.ProcessEvent) []*SecurityAlert {
	var alerts []*SecurityAlert

	comm := bytesToString(event.Comm[:])
	containerID := bytesToString(event.ContainerID[:])

	if containerID == "" {
		return alerts
	}

	eventData := map[string]interface{}{
		"pid":         event.PID,
		"ppid":        event.PPID,
		"uid":         event.UID,
		"gid":         event.GID,
		"comm":        comm,
		"container_id": containerID,
		"event_type":  event.EventType,
	}

	matchedRules := d.ruleEngine.Match("process", eventData)
	for _, rule := range matchedRules {
		alert := d.createAlert(rule, eventData)
		alerts = append(alerts, alert)
	}

	if d.isPrivilegeEscalation(event) {
		alert := &SecurityAlert{
			RuleName:    "privilege_escalation",
			Severity:    "critical",
			Message:     fmt.Sprintf("Privilege escalation detected: %s (PID: %d) running as root", comm, event.PID),
			Remediation: "Investigate the process immediately. Check for suspicious activity. Consider blocking the container.",
			ContainerID: containerID,
			PID:         event.PID,
			PPID:        event.PPID,
			UID:         event.UID,
			Comm:        comm,
			Timestamp:   time.Now(),
			Tags:        []string{"privilege-escalation", "process", "critical"},
			Fields:      eventData,
		}
		alerts = append(alerts, alert)
	}

	if d.isReverseShell(comm) && !d.whitelist.IsProcessWhitelisted(comm, containerID) {
		alert := &SecurityAlert{
			RuleName:    "reverse_shell_detected",
			Severity:    "critical",
			Message:     fmt.Sprintf("Potential reverse shell detected: %s (PID: %d)", comm, event.PID),
			Remediation: "Terminate the process immediately. Investigate the network connections and source of attack.",
			ContainerID: containerID,
			PID:         event.PID,
			PPID:        event.PPID,
			UID:         event.UID,
			Comm:        comm,
			Timestamp:   time.Now(),
			Tags:        []string{"reverse-shell", "network", "critical"},
			Fields:      eventData,
		}
		alerts = append(alerts, alert)
	}

	return alerts
}

func (d *Detector) processFileEvent(event ebpf.FileEvent) []*SecurityAlert {
	var alerts []*SecurityAlert

	comm := bytesToString(event.Comm[:])
	containerID := bytesToString(event.ContainerID[:])
	filename := bytesToString(event.Filename[:])

	if containerID == "" {
		return alerts
	}

	eventData := map[string]interface{}{
		"pid":          event.PID,
		"uid":          event.UID,
		"comm":         comm,
		"container_id": containerID,
		"filename":     filename,
		"event_type":   event.EventType,
		"mode":         event.Mode,
	}

	matchedRules := d.ruleEngine.Match("file", eventData)
	for _, rule := range matchedRules {
		alert := d.createAlert(rule, eventData)
		alerts = append(alerts, alert)
	}

	if d.isSensitiveFileAccess(filename) {
		alert := &SecurityAlert{
			RuleName:    "sensitive_file_access",
			Severity:    "high",
			Message:     fmt.Sprintf("Sensitive file access detected: %s accessed %s", comm, filename),
			Remediation: "Review the file access. Verify if this is legitimate activity. Consider restricting access.",
			ContainerID: containerID,
			PID:         event.PID,
			UID:         event.UID,
			Comm:        comm,
			Timestamp:   time.Now(),
			Tags:        []string{"file-access", "sensitive", "high"},
			Fields:      eventData,
		}
		alerts = append(alerts, alert)
	}

	return alerts
}

func (d *Detector) processNetworkEvent(event ebpf.NetworkEvent) []*SecurityAlert {
	var alerts []*SecurityAlert

	comm := bytesToString(event.Comm[:])
	containerID := bytesToString(event.ContainerID[:])

	if containerID == "" {
		return alerts
	}

	saddr := intToIP(event.Saddr)
	daddr := intToIP(event.Daddr)

	if d.whitelist.IsNetworkWhitelisted(daddr, event.Dport, "tcp", containerID) {
		return alerts
	}

	eventData := map[string]interface{}{
		"pid":          event.PID,
		"uid":          event.UID,
		"comm":         comm,
		"container_id": containerID,
		"saddr":        saddr,
		"daddr":        daddr,
		"sport":        event.Sport,
		"dport":        event.Dport,
		"protocol":     event.Protocol,
		"event_type":   event.EventType,
	}

	matchedRules := d.ruleEngine.Match("network", eventData)
	for _, rule := range matchedRules {
		alert := d.createAlert(rule, eventData)
		alerts = append(alerts, alert)
	}

	if d.isSuspiciousOutboundConnection(saddr, daddr, event.Dport) {
		alert := &SecurityAlert{
			RuleName:    "suspicious_outbound_connection",
			Severity:    "medium",
			Message:     fmt.Sprintf("Suspicious outbound connection: %s -> %s:%d", saddr, daddr, event.Dport),
			Remediation: "Review the destination IP and port. Verify if this is expected traffic.",
			ContainerID: containerID,
			PID:         event.PID,
			UID:         event.UID,
			Comm:        comm,
			Timestamp:   time.Now(),
			Tags:        []string{"network", "outbound", "suspicious"},
			Fields:      eventData,
		}
		alerts = append(alerts, alert)
	}

	return alerts
}

func (d *Detector) createAlert(rule *rules.Rule, fields map[string]interface{}) *SecurityAlert {
	message := rule.Output
	for k, v := range fields {
		message = strings.ReplaceAll(message, "%"+k+"%", fmt.Sprintf("%v", v))
	}

	return &SecurityAlert{
		RuleName:    rule.Name,
		Severity:    rule.Severity,
		Message:     message,
		Remediation: rule.Remediation,
		ContainerID: getFieldString(fields, "container_id"),
		PID:         getFieldUint32(fields, "pid"),
		PPID:        getFieldUint32(fields, "ppid"),
		UID:         getFieldUint32(fields, "uid"),
		Comm:        getFieldString(fields, "comm"),
		Timestamp:   time.Now(),
		Tags:        rule.Tags,
		Fields:      fields,
	}
}

func (d *Detector) isPrivilegeEscalation(event ebpf.ProcessEvent) bool {
	return event.UID == 0 && event.PID != 1
}

func (d *Detector) isReverseShell(comm string) bool {
	shellKeywords := []string{"bash", "sh", "nc", "netcat", "ncat", "socat", "python", "perl", "ruby"}
	commLower := strings.ToLower(comm)

	for _, kw := range shellKeywords {
		if strings.Contains(commLower, kw) {
			return true
		}
	}
	return false
}

func (d *Detector) isSensitiveFileAccess(filename string) bool {
	sensitiveFiles := []string{
		"/etc/passwd", "/etc/shadow", "/etc/group", "/etc/gshadow",
		"/root", "/.ssh", "/.kube", "/var/run/docker.sock",
		"/proc/self/environ", "/proc/self/mem",
	}
	for _, sf := range sensitiveFiles {
		if strings.HasPrefix(filename, sf) {
			return true
		}
	}
	return false
}

func (d *Detector) isSuspiciousOutboundConnection(saddr, daddr string, dport uint16) bool {
	suspiciousPorts := []uint16{22, 23, 3389, 4444, 5555, 6666, 7777, 8888, 9999}
	for _, port := range suspiciousPorts {
		if dport == port {
			return true
		}
	}

	if strings.HasPrefix(daddr, "10.") || strings.HasPrefix(daddr, "192.168.") || strings.HasPrefix(daddr, "172.") {
		return false
	}

	return false
}

func (d *Detector) GetWhitelistManager() *WhitelistManager {
	return d.whitelist
}

func bytesToString(b []byte) string {
	n := bytes.IndexByte(b, 0)
	if n == -1 {
		return string(b)
	}
	return string(b[:n])
}

func intToIP(ip uint32) string {
	return net.IPv4(byte(ip>>24), byte(ip>>16), byte(ip>>8), byte(ip)).String()
}

func getFieldString(fields map[string]interface{}, key string) string {
	if v, ok := fields[key].(string); ok {
		return v
	}
	return ""
}

func getFieldUint32(fields map[string]interface{}, key string) uint32 {
	if v, ok := fields[key].(uint32); ok {
		return v
	}
	return 0
}
