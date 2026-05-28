package ebpf

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/coldstart-optimizer/coldstart/internal/model"
)

type TraceEvent struct {
	Kind      string
	Timestamp time.Time
	PID       uint32
	TGID      uint32
	Comm      string
	Detail    string
}

type Tracer struct {
	mu      sync.RWMutex
	enabled bool
	events  []TraceEvent
	cb      func(TraceEvent)
}

var (
	globalTracer = &Tracer{}
)

func DefaultTracer() *Tracer {
	return globalTracer
}

func (t *Tracer) SetCallback(cb func(TraceEvent)) {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.cb = cb
}

func (t *Tracer) Start(ctx context.Context) error {
	t.mu.Lock()
	t.enabled = true
	t.events = make([]TraceEvent, 0, 64)
	t.mu.Unlock()

	go func() {
		<-ctx.Done()
		t.mu.Lock()
		t.enabled = false
		t.mu.Unlock()
	}()
	return nil
}

func (t *Tracer) Stop() {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.enabled = false
}

func (t *Tracer) Record(ev TraceEvent) {
	t.mu.Lock()
	defer t.mu.Unlock()
	if !t.enabled {
		return
	}
	t.events = append(t.events, ev)
	if t.cb != nil {
		t.cb(ev)
	}
}

func (t *Tracer) Snapshot() []TraceEvent {
	t.mu.RLock()
	defer t.mu.RUnlock()
	out := make([]TraceEvent, len(t.events))
	copy(out, t.events)
	return out
}

func (t *Tracer) BuildPhaseRecord(kind string, prev time.Time, phase model.Phase, detail string) (model.PhaseRecord, time.Time) {
	now := time.Now()
	if prev.IsZero() {
		prev = now
	}
	return model.PhaseRecord{
		Phase:    phase,
		Start:    prev,
		End:      now,
		Duration: now.Sub(prev),
		Source:   fmt.Sprintf("ebpf:%s", kind),
		Detail:   detail,
	}, now
}

func ClassifyExec(comm string) model.Phase {
	switch comm {
	case "runc", "containerd", "containerd-shim":
		return model.PhaseContainerInit
	case "node", "python3", "python", "java", "go":
		return model.PhaseRuntimeBoot
	default:
		return model.PhaseUserCode
	}
}
