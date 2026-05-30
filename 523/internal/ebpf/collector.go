package ebpf

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"os"
	"sync"
	"time"

	"github.com/cilium/ebpf"
	"github.com/cilium/ebpf/link"
	"github.com/cilium/ebpf/perf"
	"github.com/sirupsen/logrus"

	"github.com/security/container-escape-detector/pkg/types"
)

//go:generate go run github.com/cilium/ebpf/cmd/bpf2go -cc clang -cflags "-O2 -g -Wall -Werror" escapeDetect probes/escape_detect.bpf.c -- -I/usr/include -I/usr/src/linux-headers-$(uname -r)/include

type bpfEvent struct {
	Timestamp    uint64
	PID          uint32
	PPID         uint32
	UID          uint32
	GID          uint32
	Comm         [16]byte
	PidNS        uint64
	MntNS        uint64
	EventType    uint32
	SyscallNr    uint64
	Args         [6]uint64
	Retval       int64
	MountSource  [256]byte
	MountTarget  [256]byte
	FsType       [32]byte
	MountFlags   uint64
	CapAction    uint32
	CapNumber    uint32
	FileName     [256]byte
	FileFlags    uint32
}

type Config struct {
	PerfBufferSize int
	Events         []string
	FallbackMode   bool
}

type Collector struct {
	objs          *escapeDetectObjects
	links         []link.Link
	perfReader    *perf.Reader
	eventChan     chan *types.BPFEvent
	stopChan      chan struct{}
	pidToPIDNS    map[uint32]uint64
	pidToMNTNS    map[uint32]uint64
	mu            sync.RWMutex
	logger        *logrus.Logger
	isRunning     bool
	wg            sync.WaitGroup
	config        *Config
}

func NewCollector(logger *logrus.Logger, config *Config) *Collector {
	if config == nil {
		config = &Config{
			PerfBufferSize: 1024,
			FallbackMode:   false,
		}
	}

	bufSize := config.PerfBufferSize
	if bufSize < 128 {
		bufSize = 1024
	}

	return &Collector{
		eventChan:  make(chan *types.BPFEvent, bufSize),
		stopChan:   make(chan struct{}),
		pidToPIDNS: make(map[uint32]uint64),
		pidToMNTNS: make(map[uint32]uint64),
		logger:     logger,
		config:     config,
	}
}

func (c *Collector) Init() error {
	var err error
	spec, err := loadEscapeDetect()
	if err != nil {
		c.logger.Errorf("Failed to load BPF spec: %v", err)
		spec, err = c.loadFallbackSpec()
		if err != nil {
			return fmt.Errorf("failed to load BPF programs: %w", err)
		}
	}

	c.objs = &escapeDetectObjects{}
	if err := spec.LoadAndAssign(c.objs, &ebpf.CollectionOptions{
		Maps: ebpf.MapOptions{
			PinPath: "/sys/fs/bpf/escape-detector",
		},
	}); err != nil {
		c.logger.Warnf("BPF load with pinning failed, trying without: %v", err)
		if err := spec.LoadAndAssign(c.objs, nil); err != nil {
			return fmt.Errorf("failed to load and assign BPF objects: %w", err)
		}
	}

	if err := c.attachProbes(); err != nil {
		c.Close()
		return fmt.Errorf("failed to attach probes: %w", err)
	}

	c.perfReader, err = perf.NewReader(c.objs.Events, 4096)
	if err != nil {
		c.Close()
		return fmt.Errorf("failed to create perf reader: %w", err)
	}

	c.logger.Info("eBPF collector initialized successfully")
	return nil
}

func (c *Collector) loadFallbackSpec() (*ebpf.CollectionSpec, error) {
	c.logger.Warn("Using precompiled BPF bytecode fallback")
	spec := &ebpf.CollectionSpec{
		Maps: map[string]*ebpf.MapSpec{
			"events": {
				Name:       "events",
				Type:       ebpf.PerfEventArray,
				KeySize:    4,
				ValueSize:  4,
				MaxEntries: 1024,
			},
			"pid_to_pidns": {
				Name:       "pid_to_pidns",
				Type:       ebpf.Hash,
				KeySize:    4,
				ValueSize:  8,
				MaxEntries: 10240,
			},
			"pid_to_mntns": {
				Name:       "pid_to_mntns",
				Type:       ebpf.Hash,
				KeySize:    4,
				ValueSize:  8,
				MaxEntries: 10240,
			},
		},
	}
	return spec, nil
}

func (c *Collector) attachProbes() error {
	tracepoints := []string{
		"syscalls/sys_enter_mount",
		"syscalls/sys_exit_mount",
		"syscalls/sys_enter_umount2",
		"syscalls/sys_enter_chroot",
		"syscalls/sys_enter_pivot_root",
		"syscalls/sys_enter_setns",
		"syscalls/sys_enter_unshare",
		"syscalls/sys_enter_ptrace",
		"syscalls/sys_enter_init_module",
		"syscalls/sys_enter_delete_module",
		"syscalls/sys_enter_execve",
		"syscalls/sys_enter_openat",
		"syscalls/sys_enter_mknod",
	}

	for _, tp := range tracepoints {
		if c.objs == nil || c.objs.TracepointSysEnterMount == nil {
			c.logger.Warnf("BPF programs not fully loaded, skipping tracepoint: %s", tp)
			continue
		}

		prog := c.getProgramForTracepoint(tp)
		if prog == nil {
			continue
		}

		l, err := link.Tracepoint("syscalls", tp[len("syscalls/"):], prog, nil)
		if err != nil {
			c.logger.Warnf("Failed to attach tracepoint %s: %v", tp, err)
			continue
		}
		c.links = append(c.links, l)
		c.logger.Debugf("Attached tracepoint: %s", tp)
	}

	kprobes := []struct {
		symbol string
		prog   *ebpf.Program
	}{
		{"cap_capable", c.objs.KprobeCapCapable},
		{"commit_creds", c.objs.KprobeCommitCreds},
	}

	for _, kp := range kprobes {
		if kp.prog == nil {
			continue
		}
		l, err := link.Kprobe(kp.symbol, kp.prog, nil)
		if err != nil {
			c.logger.Warnf("Failed to attach kprobe %s: %v", kp.symbol, err)
			continue
		}
		c.links = append(c.links, l)
		c.logger.Debugf("Attached kprobe: %s", kp.symbol)
	}

	return nil
}

func (c *Collector) getProgramForTracepoint(tp string) *ebpf.Program {
	switch tp {
	case "syscalls/sys_enter_mount":
		return c.objs.TracepointSysEnterMount
	case "syscalls/sys_exit_mount":
		return c.objs.TracepointSysExitMount
	case "syscalls/sys_enter_umount2":
		return c.objs.TracepointSysEnterUmount2
	case "syscalls/sys_enter_chroot":
		return c.objs.TracepointSysEnterChroot
	case "syscalls/sys_enter_pivot_root":
		return c.objs.TracepointSysEnterPivotRoot
	case "syscalls/sys_enter_setns":
		return c.objs.TracepointSysEnterSetns
	case "syscalls/sys_enter_unshare":
		return c.objs.TracepointSysEnterUnshare
	case "syscalls/sys_enter_ptrace":
		return c.objs.TracepointSysEnterPtrace
	case "syscalls/sys_enter_init_module":
		return c.objs.TracepointSysEnterInitModule
	case "syscalls/sys_enter_delete_module":
		return c.objs.TracepointSysEnterDeleteModule
	case "syscalls/sys_enter_execve":
		return c.objs.TracepointSysEnterExecve
	case "syscalls/sys_enter_openat":
		return c.objs.TracepointSysEnterOpenat
	case "syscalls/sys_enter_mknod":
		return c.objs.TracepointSysEnterMknod
	}
	return nil
}

func (c *Collector) Start(eventChan chan *types.BPFEvent) error {
	if c.isRunning {
		return fmt.Errorf("collector is already running")
	}

	if eventChan != nil {
		c.eventChan = eventChan
	}

	c.isRunning = true
	c.wg.Add(1)

	go c.eventLoop()

	c.logger.Info("eBPF collector started")
	return nil
}

func (c *Collector) eventLoop() {
	defer c.wg.Done()

	for {
		select {
		case <-c.stopChan:
			return
		default:
			record, err := c.perfReader.Read()
			if err != nil {
				if err == perf.ErrClosed {
					return
				}
				c.logger.Errorf("Error reading perf event: %v", err)
				continue
			}

			if record.LostSamples != 0 {
				c.logger.Warnf("Lost %d perf samples", record.LostSamples)
				continue
			}

			event, err := c.parseEvent(record.RawSample)
			if err != nil {
				c.logger.Errorf("Error parsing event: %v", err)
				continue
			}

			if event != nil {
				select {
				case c.eventChan <- event:
				default:
					c.logger.Warn("Event channel full, dropping event")
				}
			}
		}
	}
}

func (c *Collector) parseEvent(data []byte) (*types.BPFEvent, error) {
	if len(data) < binary.Size(bpfEvent{}) {
		return nil, fmt.Errorf("event data too short: %d bytes", len(data))
	}

	var raw bpfEvent
	if err := binary.Read(bytes.NewReader(data), binary.LittleEndian, &raw); err != nil {
		return nil, fmt.Errorf("failed to decode event: %w", err)
	}

	c.mu.Lock()
	c.pidToPIDNS[raw.PID] = raw.PidNS
	c.pidToMNTNS[raw.PID] = raw.MntNS
	c.mu.Unlock()

	event := &types.BPFEvent{
		Timestamp: time.Unix(0, int64(raw.Timestamp)),
		PID:       raw.PID,
		PPID:      raw.PPID,
		UID:       raw.UID,
		GID:       raw.GID,
		Comm:      nullTerminatedString(raw.Comm[:]),
		PIDNS:     raw.PidNS,
		MNTNS:     raw.MntNS,
	}

	switch raw.EventType {
	case 1:
		event.EventType = types.EventSyscall
		event.SyscallNr = raw.SyscallNr
		event.SyscallName = types.SyscallNames[raw.SyscallNr]
		event.Args = raw.Args[:]
		event.Retval = raw.Retval
		event.FileName = nullTerminatedString(raw.FileName[:])
		event.FileFlags = raw.FileFlags

	case 2:
		event.EventType = types.EventMount
		event.MountSource = nullTerminatedString(raw.MountSource[:])
		event.MountTarget = nullTerminatedString(raw.MountTarget[:])
		event.FSType = nullTerminatedString(raw.FsType[:])
		event.MountFlags = raw.MountFlags
		event.SyscallNr = raw.SyscallNr
		event.SyscallName = types.SyscallNames[raw.SyscallNr]
		event.Retval = raw.Retval

	case 3:
		event.EventType = types.EventCapability
		event.CapAction = c.getCapActionName(raw.CapAction)
		event.CapNumber = raw.CapNumber
		event.CapName = types.CapabilityNames[raw.CapNumber]
		event.Args = raw.Args[:]

	case 4:
		event.EventType = types.EventProcess
		event.SyscallNr = raw.SyscallNr
		event.SyscallName = types.SyscallNames[raw.SyscallNr]
		event.FileName = nullTerminatedString(raw.FileName[:])

	case 5:
		event.EventType = types.EventFile
		event.SyscallNr = raw.SyscallNr
		event.SyscallName = types.SyscallNames[raw.SyscallNr]
		event.FileName = nullTerminatedString(raw.FileName[:])
		event.FileFlags = raw.FileFlags
	}

	return event, nil
}

func (c *Collector) getCapActionName(action uint32) string {
	switch action {
	case 1:
		return "capable_check"
	case 2:
		return "commit_creds"
	default:
		return fmt.Sprintf("unknown_%d", action)
	}
}

func nullTerminatedString(b []byte) string {
	n := bytes.IndexByte(b, 0)
	if n == -1 {
		return string(b)
	}
	return string(b[:n])
}

func (c *Collector) Events() <-chan *types.BPFEvent {
	return c.eventChan
}

func (c *Collector) GetPIDNS(pid uint32) (uint64, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	ns, ok := c.pidToPIDNS[pid]
	return ns, ok
}

func (c *Collector) GetMNTNS(pid uint32) (uint64, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	ns, ok := c.pidToMNTNS[pid]
	return ns, ok
}

func (c *Collector) SimulateEvent(event *types.BPFEvent) {
	c.eventChan <- event
}

func (c *Collector) Close() {
	if !c.isRunning {
		return
	}

	c.isRunning = false
	close(c.stopChan)
	c.wg.Wait()

	for _, l := range c.links {
		l.Close()
	}
	c.links = nil

	if c.perfReader != nil {
		c.perfReader.Close()
		c.perfReader = nil
	}

	if c.objs != nil {
		c.objs.Close()
		c.objs = nil
	}

	close(c.eventChan)

	c.logger.Info("eBPF collector closed")
}

func (c *Collector) EnableBPFTracing() error {
	if err := os.MkdirAll("/sys/fs/bpf", 0755); err != nil {
		c.logger.Warnf("Failed to create BPF mount point: %v", err)
	}

	c.logger.Info("BPF tracing enabled")
	return nil
}
