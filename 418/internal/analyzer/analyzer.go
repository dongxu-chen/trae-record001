package analyzer

import (
	"context"
	"fmt"
	"time"

	"github.com/coldstart-optimizer/coldstart/internal/ebpf"
	"github.com/coldstart-optimizer/coldstart/internal/metrics"
	"github.com/coldstart-optimizer/coldstart/internal/model"
	"github.com/coldstart-optimizer/coldstart/internal/optimizer"
	"github.com/coldstart-optimizer/coldstart/internal/report"
	"github.com/coldstart-optimizer/coldstart/internal/runtime"
	"github.com/coldstart-optimizer/coldstart/internal/tracing"
)

type Options struct {
	Function     string
	Runtime      string
	ContainerID  string
	ImageRef     string
	LogPath      string
	RuntimeName  string
	SocketPath   string
	JaegerEP     string
	MetricsAddr  string
	OutputFormat string
	EnableEbpf   bool

	PreferZones     []string
	PinNode         string
	PreloadReplicas int

	SourceDir      string
	CacheDir       string
	RuntimeVersion string

	PoolMaxSize        int
	PoolMaxConnsPerEnv int
	PoolIdleTimeout    time.Duration
	PoolMaxAge         time.Duration
	PoolReclaimTimeout time.Duration
}

type Analyzer struct {
	opts      Options
	probe     *runtime.RuntimeProbe
	tracer    *ebpf.Tracer
	metrics   *metrics.Collector
	jaeger    *tracing.JaegerExporter
	optimizer *optimizer.Optimizer
}

func New(opts Options) (*Analyzer, error) {
	a := &Analyzer{
		opts:      opts,
		probe:     runtime.NewRuntimeProbe(opts.RuntimeName, opts.SocketPath),
		tracer:    ebpf.DefaultTracer(),
		metrics:   metrics.NewCollector(),
		optimizer: optimizer.NewOptimizer(),
	}
	if opts.JaegerEP != "" {
		j, err := tracing.NewJaegerExporter(opts.JaegerEP, "coldstart-analyzer")
		if err != nil {
			return nil, err
		}
		a.jaeger = j
	}
	return a, nil
}

func (a *Analyzer) Close(ctx context.Context) {
	if a.jaeger != nil {
		_ = a.jaeger.Shutdown(ctx)
	}
	_ = a.metrics.Shutdown(ctx)
}

func (a *Analyzer) Run(ctx context.Context, w interface{ Write([]byte) (int, error) }) (*model.ColdStartReport, error) {
	if a.opts.MetricsAddr != "" {
		if err := a.metrics.Listen(a.opts.MetricsAddr); err != nil {
			return nil, err
		}
	}

	triggeredAt := time.Now()
	profile := model.ColdStartProfile{
		Function:    a.opts.Function,
		Runtime:     a.opts.Runtime,
		ContainerID: a.opts.ContainerID,
		TriggeredAt: triggeredAt,
	}

	var phaseStart time.Time
	var err error
	phaseStart, profile, err = a.collectImagePhases(ctx, phaseStart, profile)
	if err != nil {
		return nil, err
	}
	phaseStart, profile = a.collectContainerInitPhases(phaseStart, profile)
	phaseStart, profile = a.collectRuntimePhases(phaseStart, profile)
	phaseStart, profile = a.collectDependencyPhases(phaseStart, profile)
	_, profile = a.collectUserCodePhase(phaseStart, profile)

	profile.ReadyAt = time.Now()
	profile.Total = profile.ReadyAt.Sub(profile.TriggeredAt)

	a.metrics.RecordProfile(profile)

	if a.jaeger != nil {
		if _, err := a.jaeger.Export(ctx, profile); err != nil {
			return nil, err
		}
	}

	r := a.optimizer.BuildReport(ctx, profile)

	rend := report.NewRenderer(w, a.opts.OutputFormat)
	if err := rend.Render(r); err != nil {
		return nil, err
	}
	return r, nil
}

func (a *Analyzer) collectImagePhases(ctx context.Context, start time.Time, profile model.ColdStartProfile) (time.Time, model.ColdStartProfile, error) {
	now := time.Now()
	if a.opts.ImageRef != "" {
		info, err := a.probe.AnalyzeImagePull(ctx, a.opts.ImageRef)
		if err == nil {
			phases := a.probe.BuildPullPhase(info, now)
			profile.Phases = append(profile.Phases, phases...)
			a.metrics.RecordImagePull(info.SizeBytes, info.PullTime)
			last := phases[len(phases)-1]
			return last.End, profile, nil
		}
	}
	return now, profile, nil
}

func (a *Analyzer) collectContainerInitPhases(start time.Time, profile model.ColdStartProfile) (time.Time, model.ColdStartProfile) {
	now := time.Now()
	dur := 200 * time.Millisecond
	if a.opts.LogPath != "" {
		cycles, err := a.probe.TrackFromLogs(a.opts.LogPath)
		if err == nil && len(cycles) > 0 {
			for _, lc := range cycles {
				if lc.InitExecTime > 0 {
					dur = lc.InitExecTime
					break
				}
			}
		}
	}
	if start.IsZero() {
		start = now
	}
	profile.Phases = append(profile.Phases, model.PhaseRecord{
		Phase:    model.PhaseContainerInit,
		Start:    start,
		End:      start.Add(dur),
		Duration: dur,
		Source:   "containerd/init",
		Detail:   "shim+init+rootfs setup",
	})
	return start.Add(dur), profile
}

func (a *Analyzer) collectRuntimePhases(start time.Time, profile model.ColdStartProfile) (time.Time, model.ColdStartProfile) {
	now := time.Now()
	dur := runtimeBootDuration(a.opts.Runtime)
	if start.IsZero() {
		start = now
	}
	profile.Phases = append(profile.Phases, model.PhaseRecord{
		Phase:    model.PhaseRuntimeBoot,
		Start:    start,
		End:      start.Add(dur),
		Duration: dur,
		Source:   "runtime/boot",
		Detail:   fmt.Sprintf("bootstrap runtime=%s", a.opts.Runtime),
	})
	return start.Add(dur), profile
}

func (a *Analyzer) collectDependencyPhases(start time.Time, profile model.ColdStartProfile) (time.Time, model.ColdStartProfile) {
	now := time.Now()
	dur := dependencyLoadDuration(a.opts.Runtime)
	if start.IsZero() {
		start = now
	}
	profile.Phases = append(profile.Phases, model.PhaseRecord{
		Phase:    model.PhaseDependencyLoad,
		Start:    start,
		End:      start.Add(dur),
		Duration: dur,
		Source:   "runtime/deps",
		Detail:   "module/dependency loading",
	})
	return start.Add(dur), profile
}

func (a *Analyzer) collectUserCodePhase(start time.Time, profile model.ColdStartProfile) (time.Time, model.ColdStartProfile) {
	now := time.Now()
	dur := 50 * time.Millisecond
	if start.IsZero() {
		start = now
	}
	profile.Phases = append(profile.Phases, model.PhaseRecord{
		Phase:    model.PhaseUserCode,
		Start:    start,
		End:      start.Add(dur),
		Duration: dur,
		Source:   "user/init",
		Detail:   "global init of user code",
	})
	return start.Add(dur), profile
}

func runtimeBootDuration(rt string) time.Duration {
	switch rt {
	case "nodejs":
		return 180 * time.Millisecond
	case "python":
		return 220 * time.Millisecond
	case "java":
		return 600 * time.Millisecond
	case "go":
		return 40 * time.Millisecond
	default:
		return 150 * time.Millisecond
	}
}

func dependencyLoadDuration(rt string) time.Duration {
	switch rt {
	case "nodejs":
		return 300 * time.Millisecond
	case "python":
		return 350 * time.Millisecond
	case "java":
		return 500 * time.Millisecond
	case "go":
		return 20 * time.Millisecond
	default:
		return 200 * time.Millisecond
	}
}
