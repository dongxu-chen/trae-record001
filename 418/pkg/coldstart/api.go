package coldstart

import (
	"context"

	"github.com/coldstart-optimizer/coldstart/internal/analyzer"
	"github.com/coldstart-optimizer/coldstart/internal/cost"
	"github.com/coldstart-optimizer/coldstart/internal/geo"
	"github.com/coldstart-optimizer/coldstart/internal/model"
	"github.com/coldstart-optimizer/coldstart/internal/optimizer"
	"github.com/coldstart-optimizer/coldstart/internal/pool"
	"github.com/coldstart-optimizer/coldstart/internal/predictive"
	"github.com/coldstart-optimizer/coldstart/internal/scheduler"
	"github.com/coldstart-optimizer/coldstart/internal/snapshot"
)

type Options = analyzer.Options

type Analyzer struct {
	impl *analyzer.Analyzer
}

func New(opts Options) (*Analyzer, error) {
	a, err := analyzer.New(opts)
	if err != nil {
		return nil, err
	}
	return &Analyzer{impl: a}, nil
}

func (a *Analyzer) Run(ctx context.Context, w interface{ Write([]byte) (int, error) }) (*model.ColdStartReport, error) {
	return a.impl.Run(ctx, w)
}

func (a *Analyzer) Close(ctx context.Context) {
	a.impl.Close(ctx)
}

func NewOptimizerEngine() *optimizer.Engine { return optimizer.NewEngine() }

func NewPool(cfg pool.PoolConfig) *pool.EnvPool { return pool.NewEnvPool(cfg) }

func DefaultPoolConfig() pool.PoolConfig { return pool.DefaultPoolConfig() }

func BuildAffinityPlan(function, runtime, imageRef string, preferZones []string, pinNode string, nodes []*scheduler.Node, replicas int) (*scheduler.PreloadPlan, error) {
	eng := optimizer.NewEngine()
	return eng.BuildAffinityPlan(function, runtime, imageRef, preferZones, pinNode, nodes, replicas)
}

func BuildSnapshot(lang snapshot.Language, runtimeVer, sourceDir, cacheDir string) (*snapshot.BuildResult, error) {
	return snapshot.BuildForLanguage(lang, runtimeVer, sourceDir, cacheDir)
}

func NewNode(name, zone, region string, labels map[string]string) *scheduler.Node {
	return &scheduler.Node{Name: name, Zone: zone, Region: region, Labels: labels}
}

func NewRuntimeEnv(id, function, runtime, containerID, node string) *pool.RuntimeEnv {
	return pool.NewEnv(id, function, runtime, containerID, node)
}

func NewPredictor(cfg predictive.PredictorConfig) *predictive.Predictor {
	return predictive.NewPredictor(cfg)
}

func DefaultPredictorConfig() predictive.PredictorConfig {
	return predictive.DefaultConfig()
}

func PredictResidentFunctions(history []predictive.HistoryEntry, cfg predictive.PredictorConfig) *model.PredictedPreheat {
	eng := optimizer.NewEngine()
	return eng.BuildPredictionPlan(history, cfg)
}

func NewReplicator(cfg geo.ReplicationConfig) *geo.Replicator {
	eng := optimizer.NewEngine()
	return eng.NewReplicator(cfg)
}

func DefaultReplicationConfig() geo.ReplicationConfig {
	return geo.DefaultReplicationConfig()
}

func DefaultRegionSet() []*model.GeoRegion {
	return geo.DefaultRegionSet()
}

func NewCostAnalyzer(pricing cost.PricingModel) *cost.Analyzer {
	return cost.NewAnalyzer(pricing)
}

func DefaultPricing() cost.PricingModel {
	return cost.DefaultPricing()
}

func AnalyzeCost(profile model.ColdStartProfile, pricing cost.PricingModel) *model.CostAnalysis {
	ca := cost.NewAnalyzer(pricing)
	return ca.Analyze(profile)
}

type OptimizerFacade struct {
	impl *optimizer.Optimizer
}

func NewOptimizer() *OptimizerFacade {
	return &OptimizerFacade{impl: optimizer.NewOptimizer()}
}

func NewOptimizerWithPricing(pricing cost.PricingModel) *OptimizerFacade {
	return &OptimizerFacade{impl: optimizer.NewOptimizerWithPricing(pricing)}
}

func (f *OptimizerFacade) BuildReport(ctx context.Context, profile model.ColdStartProfile) *model.ColdStartReport {
	return f.impl.BuildReport(ctx, profile)
}

func (f *OptimizerFacade) SetPricing(pricing cost.PricingModel) {
	f.impl.SetPricing(pricing)
}
