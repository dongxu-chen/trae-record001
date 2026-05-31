package tuner

import (
	"math"
	"math/rand"
	"sync"
	"time"
)

type TunableParams struct {
	ScaleUpThreshold    float64           `json:"scaleUpThreshold"`
	ScaleDownThreshold  float64           `json:"scaleDownThreshold"`
	CompositeTarget     float64           `json:"compositeTarget"`
	ScaleUpCooldownSec  int               `json:"scaleUpCooldownSec"`
	ScaleDownCooldownSec int              `json:"scaleDownCooldownSec"`
	MaxScaleUpRatio     float64           `json:"maxScaleUpRatio"`
	FusionWeights       map[string]float64 `json:"fusionWeights"`
}

type TuningSample struct {
	Timestamp         time.Time     `json:"timestamp"`
	ParamsBefore      TunableParams `json:"paramsBefore"`
	CurrentReplicas   int32         `json:"currentReplicas"`
	DesiredReplicas   int32         `json:"desiredReplicas"`
	AvgCPU            float64       `json:"avgCPU"`
	AvgQPS            float64       `json:"avgQPS"`
	AvgLatency        float64       `json:"avgLatency"`
	SLAViolations     int           `json:"slaViolations"`
	CostChangePercent float64       `json:"costChangePercent"`
	Reward            float64       `json:"reward"`
}

type TuningResult struct {
	Params           TunableParams `json:"params"`
	BestReward       float64       `json:"bestReward"`
	SampleCount      int           `json:"sampleCount"`
	LastUpdate       time.Time     `json:"lastUpdate"`
	ExplorationRate  float64       `json:"explorationRate"`
	RollingWindowSize int          `json:"rollingWindowSize"`
}

type AutoTuner struct {
	currentParams     TunableParams
	rollingWindow     []TuningSample
	maxWindowSize     int
	explorationRate   float64
	explorationDecay  float64
	minExplorationRate float64
	bestParams        TunableParams
	bestReward        float64
	updateCounter     int
	updateInterval    int
	mu                sync.RWMutex
}

func NewAutoTuner(initial TunableParams, windowSize int) *AutoTuner {
	return &AutoTuner{
		currentParams:      initial,
		rollingWindow:      make([]TuningSample, 0, windowSize),
		maxWindowSize:      windowSize,
		explorationRate:    0.3,
		explorationDecay:   0.995,
		minExplorationRate: 0.05,
		bestParams:         initial,
		bestReward:         -1.0,
		updateInterval:     10,
	}
}

func (t *AutoTuner) GetParams() TunableParams {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return t.currentParams
}

func (t *AutoTuner) calculateReward(s TuningSample) float64 {
	slaComponent := 0.4 * (1.0 - float64(s.SLAViolations)/math.Max(1.0, float64(s.SLAViolations+1)))
	latencyTarget := 0.2
	latencyComponent := 0.3 * (1.0 - math.Abs(s.AvgLatency-latencyTarget)/latencyTarget)
	if latencyComponent < 0 {
		latencyComponent = 0
	}
	costComponent := 0.3 * (1.0 - math.Abs(s.CostChangePercent)/100.0)
	if costComponent < 0 {
		costComponent = 0
	}
	reward := slaComponent + latencyComponent + costComponent
	if reward < 0 {
		reward = 0
	}
	if reward > 1 {
		reward = 1
	}
	return reward
}

func (t *AutoTuner) perturbParams(params TunableParams) TunableParams {
	perturb := func(v float64) float64 {
		change := (rand.Float64() - 0.5) * 0.4
		newVal := v * (1.0 + change)
		if newVal < 0.1 {
			newVal = 0.1
		}
		if newVal > 5.0 {
			newVal = 5.0
		}
		return newVal
	}

	p := params
	p.ScaleUpThreshold = perturb(p.ScaleUpThreshold)
	p.ScaleDownThreshold = perturb(p.ScaleDownThreshold)
	p.CompositeTarget = perturb(p.CompositeTarget)
	p.MaxScaleUpRatio = perturb(p.MaxScaleUpRatio)

	if p.FusionWeights != nil {
		newWeights := make(map[string]float64)
		for k, v := range p.FusionWeights {
			newWeights[k] = perturb(v)
		}
		total := 0.0
		for _, v := range newWeights {
			total += v
		}
		for k, v := range newWeights {
			newWeights[k] = v / total
		}
		p.FusionWeights = newWeights
	}

	return p
}

func (t *AutoTuner) updateParamsIfNeeded() {
	t.updateCounter++
	if t.updateCounter < t.updateInterval {
		return
	}
	t.updateCounter = 0

	if len(t.rollingWindow) < t.updateInterval {
		return
	}

	windowBestReward := -1.0
	windowBestIdx := 0
	for i, s := range t.rollingWindow {
		if s.Reward > windowBestReward {
			windowBestReward = s.Reward
			windowBestIdx = i
		}
	}

	if windowBestReward > t.bestReward {
		t.bestReward = windowBestReward
		t.bestParams = t.rollingWindow[windowBestIdx].ParamsBefore
	}

	if rand.Float64() < t.explorationRate {
		t.currentParams = t.perturbParams(t.bestParams)
	} else {
		t.currentParams = t.bestParams
	}

	t.explorationRate = math.Max(t.minExplorationRate, t.explorationRate*t.explorationDecay)
}

func (t *AutoTuner) RecordSample(sample TuningSample) {
	t.mu.Lock()
	defer t.mu.Unlock()

	sample.Reward = t.calculateReward(sample)

	t.rollingWindow = append(t.rollingWindow, sample)
	for len(t.rollingWindow) > t.maxWindowSize {
		t.rollingWindow = t.rollingWindow[1:]
	}

	t.updateParamsIfNeeded()
}

func (t *AutoTuner) GetTuningResult() TuningResult {
	t.mu.RLock()
	defer t.mu.RUnlock()

	return TuningResult{
		Params:           t.currentParams,
		BestReward:       t.bestReward,
		SampleCount:      len(t.rollingWindow),
		LastUpdate:       time.Now(),
		ExplorationRate:  t.explorationRate,
		RollingWindowSize: t.maxWindowSize,
	}
}

func (t *AutoTuner) GetRollingWindow() []TuningSample {
	t.mu.RLock()
	defer t.mu.RUnlock()
	window := make([]TuningSample, len(t.rollingWindow))
	copy(window, t.rollingWindow)
	return window
}
