package ebpf

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/sirupsen/logrus"
)

type KprobeManager struct {
	mu         sync.RWMutex
	probes     map[string]*Kprobe
	running    bool
	cancelFunc context.CancelFunc
}

type Kprobe struct {
	Name    string
	Type    string
	Handler string
	Enabled bool
}

var kprobeDefinitions = []*Kprobe{
	{Name: "p_process_exec", Type: "kprobe", Handler: "sched_process_exec", Enabled: true},
	{Name: "p_process_fork", Type: "kprobe", Handler: "_do_fork", Enabled: true},
	{Name: "p_process_exit", Type: "kprobe", Handler: "do_exit", Enabled: true},
	{Name: "p_sys_openat", Type: "kprobe", Handler: "sys_openat", Enabled: true},
	{Name: "p_sys_read", Type: "kprobe", Handler: "sys_read", Enabled: true},
	{Name: "p_sys_write", Type: "kprobe", Handler: "sys_write", Enabled: true},
	{Name: "p_sys_connect", Type: "kprobe", Handler: "sys_connect", Enabled: true},
	{Name: "p_sys_accept", Type: "kprobe", Handler: "sys_accept4", Enabled: true},
}

func NewKprobeManager() *KprobeManager {
	return &KprobeManager{
		probes: make(map[string]*Kprobe),
	}
}

func (km *KprobeManager) Load() error {
	logrus.Info("Initializing kprobe manager...")

	for _, probe := range kprobeDefinitions {
		if err := km.registerProbe(probe); err != nil {
			logrus.Warnf("Failed to register kprobe %s: %v", probe.Name, err)
		} else {
			km.probes[probe.Name] = probe
			logrus.Debugf("Registered kprobe: %s -> %s", probe.Name, probe.Handler)
		}
	}

	if len(km.probes) == 0 {
		return fmt.Errorf("no kprobes could be registered")
	}

	logrus.Infof("Successfully registered %d kprobes", len(km.probes))
	return nil
}

func (km *KprobeManager) registerProbe(probe *Kprobe) error {
	cmd := exec.Command("bash", "-c",
		fmt.Sprintf("echo '%s:%s' >> /sys/kernel/debug/tracing/kprobe_events", probe.Name, probe.Handler))

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("kprobe registration failed: %v, output: %s", err, string(output))
	}

	return nil
}

func (km *KprobeManager) enableProbe(probe *Kprobe) error {
	enablePath := fmt.Sprintf("/sys/kernel/debug/tracing/events/kprobes/%s/enable", probe.Name)

	cmd := exec.Command("bash", "-c", fmt.Sprintf("echo 1 > %s", enablePath))
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to enable probe %s: %v, output: %s", probe.Name, err, string(output))
	}

	return nil
}

func (km *KprobeManager) disableProbe(probe *Kprobe) error {
	enablePath := fmt.Sprintf("/sys/kernel/debug/tracing/events/kprobes/%s/enable", probe.Name)

	cmd := exec.Command("bash", "-c", fmt.Sprintf("echo 0 > %s", enablePath))
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to disable probe %s: %v, output: %s", probe.Name, err, string(output))
	}

	return nil
}

func (km *KprobeManager) Run(ctx context.Context, eventChan chan<- interface{}) error {
	km.mu.Lock()
	km.running = true
	km.mu.Unlock()

	ctx, cancel := context.WithCancel(ctx)
	km.cancelFunc = cancel

	for _, probe := range km.probes {
		if err := km.enableProbe(probe); err != nil {
			logrus.Errorf("Failed to enable probe %s: %v", probe.Name, err)
		}
	}

	defer func() {
		for _, probe := range km.probes {
			if err := km.disableProbe(probe); err != nil {
				logrus.Errorf("Failed to disable probe %s: %v", probe.Name, err)
			}
		}
	}()

	tracePipe, err := os.Open("/sys/kernel/debug/tracing/trace_pipe")
	if err != nil {
		return fmt.Errorf("failed to open trace_pipe: %v", err)
	}
	defer tracePipe.Close()

	go km.readTracePipe(ctx, tracePipe, eventChan)

	logrus.Info("Kprobe monitoring started")
	<-ctx.Done()
	logrus.Info("Kprobe monitoring stopped")

	return nil
}

func (km *KprobeManager) readTracePipe(ctx context.Context, pipe *os.File, eventChan chan<- interface{}) {
	buf := make([]byte, 4096)

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		n, err := pipe.Read(buf)
		if err != nil {
			if ctx.Err() != nil {
				return
			}
			logrus.Errorf("Error reading trace_pipe: %v", err)
			time.Sleep(100 * time.Millisecond)
			continue
		}

		if n > 0 {
			line := string(buf[:n])
			event := km.parseTraceLine(line)
			if event != nil {
				select {
				case eventChan <- event:
				default:
					logrus.Warn("Event channel full, dropping event")
				}
			}
		}
	}
}

func (km *KprobeManager) parseTraceLine(line string) interface{} {
	parts := strings.Fields(line)
	if len(parts) < 5 {
		return nil
	}

	eventType := ""
	for _, part := range parts {
		if strings.HasPrefix(part, "p_process_") || strings.HasPrefix(part, "p_sys_") {
			eventType = part
			break
		}
	}

	switch {
	case strings.Contains(eventType, "process_exec") || strings.Contains(eventType, "process_fork") || strings.Contains(eventType, "process_exit"):
		return km.parseProcessEvent(parts)
	case strings.Contains(eventType, "sys_openat"):
		return km.parseFileEvent(parts, 1)
	case strings.Contains(eventType, "sys_read"):
		return km.parseFileEvent(parts, 2)
	case strings.Contains(eventType, "sys_write"):
		return km.parseFileEvent(parts, 3)
	case strings.Contains(eventType, "sys_connect"):
		return km.parseNetworkEvent(parts, 1)
	case strings.Contains(eventType, "sys_accept"):
		return km.parseNetworkEvent(parts, 2)
	}

	return nil
}

func (km *KprobeManager) parseProcessEvent(parts []string) *ProcessEvent {
	event := &ProcessEvent{
		Timestamp: uint64(time.Now().UnixNano()),
	}

	for i, part := range parts {
		if strings.HasPrefix(part, "pid=") {
			pid, _ := strconv.ParseUint(strings.TrimPrefix(part, "pid="), 10, 32)
			event.PID = uint32(pid)
		}
		if strings.HasPrefix(part, "ppid=") {
			ppid, _ := strconv.ParseUint(strings.TrimPrefix(part, "ppid="), 10, 32)
			event.PPID = uint32(ppid)
		}
		if strings.HasPrefix(part, "uid=") {
			uid, _ := strconv.ParseUint(strings.TrimPrefix(part, "uid="), 10, 32)
			event.UID = uint32(uid)
		}
		if strings.HasPrefix(part, "comm=") {
			comm := strings.TrimPrefix(part, "comm=")
			copy(event.Comm[:], comm)
		}
		_ = i
	}

	copy(event.ContainerID[:], GetCurrentContainerID())

	return event
}

func (km *KprobeManager) parseFileEvent(parts []string, eventType uint32) *FileEvent {
	event := &FileEvent{
		EventType: eventType,
		Timestamp: uint64(time.Now().UnixNano()),
	}

	for _, part := range parts {
		if strings.HasPrefix(part, "pid=") {
			pid, _ := strconv.ParseUint(strings.TrimPrefix(part, "pid="), 10, 32)
			event.PID = uint32(pid)
		}
		if strings.HasPrefix(part, "uid=") {
			uid, _ := strconv.ParseUint(strings.TrimPrefix(part, "uid="), 10, 32)
			event.UID = uint32(uid)
		}
		if strings.HasPrefix(part, "comm=") {
			comm := strings.TrimPrefix(part, "comm=")
			copy(event.Comm[:], comm)
		}
		if strings.HasPrefix(part, "fname=") {
			fname := strings.TrimPrefix(part, "fname=")
			copy(event.Filename[:], fname)
		}
	}

	copy(event.ContainerID[:], GetCurrentContainerID())

	return event
}

func (km *KprobeManager) parseNetworkEvent(parts []string, eventType uint32) *NetworkEvent {
	event := &NetworkEvent{
		EventType: eventType,
		Timestamp: uint64(time.Now().UnixNano()),
	}

	for _, part := range parts {
		if strings.HasPrefix(part, "pid=") {
			pid, _ := strconv.ParseUint(strings.TrimPrefix(part, "pid="), 10, 32)
			event.PID = uint32(pid)
		}
		if strings.HasPrefix(part, "uid=") {
			uid, _ := strconv.ParseUint(strings.TrimPrefix(part, "uid="), 10, 32)
			event.UID = uint32(uid)
		}
		if strings.HasPrefix(part, "comm=") {
			comm := strings.TrimPrefix(part, "comm=")
			copy(event.Comm[:], comm)
		}
		if strings.HasPrefix(part, "daddr=") {
			daddr := strings.TrimPrefix(part, "daddr=")
			parts := strings.Split(daddr, ".")
			if len(parts) == 4 {
				var ip uint32
				for i, p := range parts {
					octet, _ := strconv.ParseUint(p, 10, 8)
					ip |= uint32(octet) << uint(24-i*8)
				}
				event.Daddr = ip
			}
		}
		if strings.HasPrefix(part, "dport=") {
			dport, _ := strconv.ParseUint(strings.TrimPrefix(part, "dport="), 10, 16)
			event.Dport = uint16(dport)
		}
	}

	copy(event.ContainerID[:], GetCurrentContainerID())

	return event
}

func (km *KprobeManager) Close() {
	km.mu.Lock()
	defer km.mu.Unlock()

	if km.cancelFunc != nil {
		km.cancelFunc()
	}

	for name, probe := range km.probes {
		if err := km.disableProbe(probe); err != nil {
			logrus.Errorf("Failed to disable probe %s: %v", name, err)
		}

		cmd := exec.Command("bash", "-c",
			fmt.Sprintf("echo '-:%s' >> /sys/kernel/debug/tracing/kprobe_events", name))
		if output, err := cmd.CombinedOutput(); err != nil {
			logrus.Errorf("Failed to unregister probe %s: %v, output: %s", name, err, string(output))
		}

		delete(km.probes, name)
	}

	km.running = false
	logrus.Info("Kprobe manager closed")
}

func (km *KprobeManager) IsRunning() bool {
	km.mu.RLock()
	defer km.mu.RUnlock()
	return km.running
}

func (km *KprobeManager) GetRegisteredProbes() []string {
	km.mu.RLock()
	defer km.mu.RUnlock()

	var probes []string
	for name := range km.probes {
		probes = append(probes, name)
	}
	return probes
}
