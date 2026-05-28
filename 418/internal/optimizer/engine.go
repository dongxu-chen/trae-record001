package optimizer

import (
	"context"
	"fmt"
	"sort"
	"time"

	"github.com/coldstart-optimizer/coldstart/internal/cost"
	"github.com/coldstart-optimizer/coldstart/internal/geo"
	"github.com/coldstart-optimizer/coldstart/internal/model"
	"github.com/coldstart-optimizer/coldstart/internal/pool"
	"github.com/coldstart-optimizer/coldstart/internal/predictive"
	"github.com/coldstart-optimizer/coldstart/internal/scheduler"
	"github.com/coldstart-optimizer/coldstart/internal/snapshot"
)

type Engine struct {
	policies []Policy
}

type Policy interface {
	Name() string
	Evaluate(profile model.ColdStartProfile) *model.Suggestion
}

func NewEngine() *Engine {
	return &Engine{
		policies: []Policy{
			&ImagePreloadPolicy{},
			&NodeAffinityPolicy{},
			&PredictivePreheatPolicy{},
			&DependencySnapshotPolicy{},
			&GeoReplicationPolicy{},
			&EnvReusePolicy{},
			&WarmPoolPolicy{},
			&PoolLeakGuardPolicy{},
			&SnapshotFusePolicy{},
			&KernelOptPolicy{},
			&CostControlPolicy{},
		},
	}
}

func (e *Engine) Analyze(profile model.ColdStartProfile) []model.Suggestion {
	var out []model.Suggestion
	for _, p := range e.policies {
		if s := p.Evaluate(profile); s != nil {
			out = append(out, *s)
		}
	}
	sort.SliceStable(out, func(i, k int) bool { return out[i].Priority < out[k].Priority })
	return out
}

func (e *Engine) BuildAffinityPlan(function, runtime, imageRef string, preferZones []string, pinNode string, nodes []*scheduler.Node, replicas int) (*scheduler.PreloadPlan, error) {
	engine := scheduler.NewAffinityEngine(nodes)
	topo := scheduler.AffinityForFunction(function, runtime, preferZones, pinNode)
	return scheduler.BuildPreloadPlan(function, imageRef, topo, engine, replicas)
}

func (e *Engine) BuildSnapshotPlan(lang snapshot.Language, runtimeVer, sourceDir, cacheDir string) (*snapshot.BuildResult, error) {
	return snapshot.BuildForLanguage(lang, runtimeVer, sourceDir, cacheDir)
}

func (e *Engine) BuildPoolAdvice(profile model.ColdStartProfile, stats pool.PoolStats) model.PoolAdvice {
	pa := model.PoolAdvice{
		MaxConnsPerEnv: 10,
		IdleTimeout:    10 * time.Minute,
		MaxAge:         time.Hour,
		ReclaimTimeout: 30 * time.Second,
		MaxPoolSize:    100,
	}
	if profile.Total > 2*time.Second {
		pa.MaxConnsPerEnv = 20
		pa.MaxPoolSize = 200
		pa.IdleTimeout = 15 * time.Minute
	}
	if stats.Exhausted > 0 {
		pa.MaxPoolSize = int(float64(stats.MaxSize) * 1.5)
	}
	if stats.Leaks > 0 {
		pa.ReclaimTimeout = 15 * time.Second
	}
	return pa
}

type ImagePreloadPolicy struct{}

func (p *ImagePreloadPolicy) Name() string { return "image_preload" }

func (p *ImagePreloadPolicy) Evaluate(profile model.ColdStartProfile) *model.Suggestion {
	pull := profile.PhaseDuration(model.PhaseImagePull)
	if pull < 500*time.Millisecond {
		return nil
	}
	return &model.Suggestion{
		Kind:         model.OptImagePreload,
		Priority:     1,
		TargetPhase:  model.PhaseImagePull,
		Description:  fmt.Sprintf("镜像拉取耗时 %v 较长，建议启用节点镜像预热（daemonset 预拉取）或镜像瘦身（多阶段构建、distroless）。", pull),
		ExpectedGain: time.Duration(float64(pull) * 0.8),
		Confidence:   0.9,
	}
}

type NodeAffinityPolicy struct{}

func (p *NodeAffinityPolicy) Name() string { return "node_affinity" }

func (p *NodeAffinityPolicy) Evaluate(profile model.ColdStartProfile) *model.Suggestion {
	pull := profile.PhaseDuration(model.PhaseImagePull)
	init := profile.PhaseDuration(model.PhaseContainerInit)
	if pull+init < 400*time.Millisecond {
		return nil
	}
	return &model.Suggestion{
		Kind:        model.OptNodeAffinity,
		Priority:    1,
		TargetPhase: model.PhaseImagePull,
		Description: fmt.Sprintf("启用节点亲和调度，结合函数历史调度位置在对应节点预先拉取镜像并保持 Warm 沙箱，可将跨节点冷启动成本降低 60%%~80%%。当前 pull+init=%v。", pull+init),
		ExpectedGain: time.Duration(float64(pull+init) * 0.7),
		Confidence:   0.85,
	}
}

type DependencySnapshotPolicy struct{}

func (p *DependencySnapshotPolicy) Name() string { return "dependency_snapshot" }

func (p *DependencySnapshotPolicy) Evaluate(profile model.ColdStartProfile) *model.Suggestion {
	dep := profile.PhaseDuration(model.PhaseDependencyLoad)
	if dep < 200*time.Millisecond {
		return nil
	}
	meta := snapshot.Format{
		Kind:     snapshotKindForRuntime(profile.Runtime),
		Language: snapshot.Language(profile.Runtime),
		RuntimeVer: "auto",
		Tool:     toolForRuntime(profile.Runtime),
	}
	return &model.Suggestion{
		Kind:         model.OptDependencySnap,
		Priority:     2,
		TargetPhase:  model.PhaseDependencyLoad,
		Description:  fmt.Sprintf("依赖加载耗时 %v，使用统一快照层：%s (%s)。Node.js→V8 Snapshot，Python→.pyc 预制，Java→AppCDS，Go→plugin。", dep, meta.Kind, meta.Tool),
		ExpectedGain: time.Duration(float64(dep) * 0.6),
		Confidence:   0.8,
	}
}

type EnvReusePolicy struct{}

func (p *EnvReusePolicy) Name() string { return "env_reuse" }

func (p *EnvReusePolicy) Evaluate(profile model.ColdStartProfile) *model.Suggestion {
	boot := profile.PhaseDuration(model.PhaseRuntimeBoot)
	if boot < 100*time.Millisecond {
		return nil
	}
	return &model.Suggestion{
		Kind:         model.OptReuseEnv,
		Priority:     3,
		TargetPhase:  model.PhaseRuntimeBoot,
		Description:  fmt.Sprintf("运行时启动耗时 %v，建议启用执行环境复用（同一容器处理多个请求，保持 Warm 状态），并通过连接数上限防止过载。", boot),
		ExpectedGain: time.Duration(float64(profile.Total) * 0.4),
		Confidence:   0.75,
	}
}

type WarmPoolPolicy struct{}

func (p *WarmPoolPolicy) Name() string { return "warm_pool" }

func (p *WarmPoolPolicy) Evaluate(profile model.ColdStartProfile) *model.Suggestion {
	if profile.Total < 1*time.Second {
		return nil
	}
	return &model.Suggestion{
		Kind:         model.OptWarmPool,
		Priority:     4,
		TargetPhase:  model.PhaseContainerInit,
		Description:  fmt.Sprintf("总体冷启动 %v，建议配置 Warm Pool 预热 N 个空闲沙箱，直接从沙箱池获取；支持按节点亲和批量调度预热任务。", profile.Total),
		ExpectedGain: time.Duration(float64(profile.Total) * 0.5),
		Confidence:   0.7,
	}
}

type PoolLeakGuardPolicy struct{}

func (p *PoolLeakGuardPolicy) Name() string { return "pool_leak_guard" }

func (p *PoolLeakGuardPolicy) Evaluate(profile model.ColdStartProfile) *model.Suggestion {
	if profile.Total < 1*time.Second {
		return nil
	}
	return &model.Suggestion{
		Kind:         model.OptPoolLeakGuard,
		Priority:     5,
		TargetPhase:  model.PhaseContainerInit,
		Description:  "为环境复用池增加硬上限：每个 env 最大连接数（避免过载）、空闲超时、最大生存周期、泄漏回收（超时未 Release 自动回收），防止资源泄漏。",
		ExpectedGain: time.Duration(float64(profile.Total) * 0.2),
		Confidence:   0.9,
	}
}

type SnapshotFusePolicy struct{}

func (p *SnapshotFusePolicy) Name() string { return "snapshot_fuse" }

func (p *SnapshotFusePolicy) Evaluate(profile model.ColdStartProfile) *model.Suggestion {
	extract := profile.PhaseDuration(model.PhaseImageExtract)
	if extract < 200*time.Millisecond {
		return nil
	}
	return &model.Suggestion{
		Kind:         model.OptSnapFuse,
		Priority:     6,
		TargetPhase:  model.PhaseImageExtract,
		Description:  fmt.Sprintf("镜像解压耗时 %v，建议使用 eStargz / Nydus / overlaybd 的 seekable snapshot（支持 Lazy Pull）。", extract),
		ExpectedGain: time.Duration(float64(extract) * 0.7),
		Confidence:   0.85,
	}
}

type KernelOptPolicy struct{}

func (p *KernelOptPolicy) Name() string { return "kernel_opt" }

func (p *KernelOptPolicy) Evaluate(profile model.ColdStartProfile) *model.Suggestion {
	init := profile.PhaseDuration(model.PhaseContainerInit)
	if init < 50*time.Millisecond {
		return nil
	}
	return &model.Suggestion{
		Kind:         model.OptKernelOpt,
		Priority:     7,
		TargetPhase:  model.PhaseContainerInit,
		Description:  fmt.Sprintf("容器初始化耗时 %v，可尝试切换到轻量运行时（Kata + Dragonball、Firecracker、gVisor）以及降低 cgroup 开销。", init),
		ExpectedGain: time.Duration(float64(init) * 0.4),
		Confidence:   0.65,
	}
}

type Optimizer struct {
	engine  *Engine
	pricing cost.PricingModel
}

func NewOptimizer() *Optimizer {
	return &Optimizer{engine: NewEngine(), pricing: cost.DefaultPricing()}
}

func NewOptimizerWithPricing(pricing cost.PricingModel) *Optimizer {
	return &Optimizer{engine: NewEngine(), pricing: pricing}
}

func (o *Optimizer) BuildReport(ctx context.Context, profile model.ColdStartProfile) *model.ColdStartReport {
	_ = ctx
	ca := o.engine.AnalyzeCost(profile, o.pricing)
	return &model.ColdStartReport{
		Profile:      profile,
		Suggestions:  o.engine.Analyze(profile),
		CostAnalysis: ca,
		GeneratedAt:  time.Now(),
	}
}

func (o *Optimizer) BuildReportWithoutCost(ctx context.Context, profile model.ColdStartProfile) *model.ColdStartReport {
	_ = ctx
	return &model.ColdStartReport{
		Profile:      profile,
		Suggestions:  o.engine.Analyze(profile),
		GeneratedAt:  time.Now(),
	}
}

func (o *Optimizer) SetPricing(p cost.PricingModel) {
	o.pricing = p
}

func (o *Optimizer) Pricing() cost.PricingModel { return o.pricing }

func (o *Optimizer) Engine() *Engine { return o.engine }

type PredictivePreheatPolicy struct{}

func (p *PredictivePreheatPolicy) Name() string { return "predictive_preheat" }

func (p *PredictivePreheatPolicy) Evaluate(profile model.ColdStartProfile) *model.Suggestion {
	pull := profile.PhaseDuration(model.PhaseImagePull)
	init := profile.PhaseDuration(model.PhaseContainerInit)
	if pull+init < 300 {
		return nil
	}
	return &model.Suggestion{
		Kind:        model.OptPredictivePreheat,
		Priority:    2,
		TargetPhase: model.PhaseImagePull,
		Description: fmt.Sprintf(
			"启用预测性预热：基于 14 天调度历史分析函数常驻性，对高频（≥3次/天）、稳定（最近7天活跃）、跨地域函数提前在目标节点预拉取镜像并保持 Warm 沙箱。当前 pull+init=%v。",
			pull+init),
		ExpectedGain: time.Duration(float64(pull+init) * 0.7),
		Confidence:   0.82,
	}
}

type GeoReplicationPolicy struct{}

func (p *GeoReplicationPolicy) Name() string { return "geo_replication" }

func (p *GeoReplicationPolicy) Evaluate(profile model.ColdStartProfile) *model.Suggestion {
	pull := profile.PhaseDuration(model.PhaseImagePull)
	dep := profile.PhaseDuration(model.PhaseDependencyLoad)
	if pull+dep < 200 {
		return nil
	}
	return &model.Suggestion{
		Kind:        model.OptGeoReplication,
		Priority:    3,
		TargetPhase: model.PhaseDependencyLoad,
		Description: fmt.Sprintf(
			"启用快照跨地域复制：将已构建的依赖快照分发到所有活跃地域节点，冷启动时本地加载，跳过网络拉取。跨地域 pull+dep=%v 可降低 70%%~90%%。",
			pull+dep),
		ExpectedGain: time.Duration(float64(pull+dep) * 0.75),
		Confidence:   0.88,
	}
}

type CostControlPolicy struct{}

func (p *CostControlPolicy) Name() string { return "cost_control" }

func (p *CostControlPolicy) Evaluate(profile model.ColdStartProfile) *model.Suggestion {
	if profile.Total < 500 {
		return nil
	}
	return &model.Suggestion{
		Kind:        model.OptCostControl,
		Priority:    8,
		TargetPhase: model.PhaseReady,
		Description: fmt.Sprintf(
			"冷启动成本控制：冷启动总耗时 %v 导致 CPU/Memory/IO/网络额外开销。采用预测预热+快照复现+环境复用可降低每次冷启动成本 40%%~70%%，月度节省可观。",
			profile.Total),
		ExpectedGain: time.Duration(float64(profile.Total) * 0.5),
		Confidence:   0.92,
	}
}

func (e *Engine) NewPredictor(cfg predictive.PredictorConfig) *predictive.Predictor {
	return predictive.NewPredictor(cfg)
}

func (e *Engine) NewReplicator(cfg geo.ReplicationConfig) *geo.Replicator {
	store := geo.NewRegionStore()
	for _, r := range geo.DefaultRegionSet() {
		store.RegisterRegion(r)
	}
	return geo.NewReplicator(store, cfg)
}

func (e *Engine) NewCostAnalyzer(pricing cost.PricingModel) *cost.Analyzer {
	return cost.NewAnalyzer(pricing)
}

func (e *Engine) AnalyzeCost(profile model.ColdStartProfile, pricing cost.PricingModel) *model.CostAnalysis {
	ca := cost.NewAnalyzer(pricing)
	return ca.Analyze(profile)
}

func (e *Engine) BuildPredictionPlan(history []predictive.HistoryEntry, cfg predictive.PredictorConfig) *model.PredictedPreheat {
	p := predictive.NewPredictor(cfg)
	p.AddBatch(history)
	return p.Predict(context.Background())
}

func snapshotKindForRuntime(runtime string) snapshot.SnapshotKind {
	switch snapshot.Language(runtime) {
	case snapshot.LangNodeJS:
		return snapshot.KindNodeJSV8Snapshot
	case snapshot.LangPython:
		return snapshot.KindPythonBytecode
	case snapshot.LangJava:
		return snapshot.KindJavaAppCDS
	case snapshot.LangGo:
		return snapshot.KindGoPlugin
	default:
		return snapshot.KindGenericFile
	}
}

func toolForRuntime(runtime string) string {
	switch runtime {
	case "nodejs":
		return "mksnapshot"
	case "python":
		return "compileall"
	case "java":
		return "java -Xshare:dump"
	case "go":
		return "go build -buildmode=plugin"
	default:
		return "rsync"
	}
}
