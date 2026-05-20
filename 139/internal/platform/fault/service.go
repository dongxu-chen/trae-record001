package fault

import (
	"fmt"
	"sync"
	"time"
)

type Service struct {
	faults map[string]*FaultInstance
	mu     sync.RWMutex
}

type FaultType string

const (
	FaultMetricSpike      FaultType = "metric_spike"
	FaultMetricDegradation FaultType = "metric_degradation"
	FaultOutage            FaultType = "outage"
)

type FaultConfig struct {
	ID          string                 `json:"id"`
	Type        FaultType              `json:"type"`
	Name        string                 `json:"name"`
	Description string                 `json:"description,omitempty"`
	Target      TargetSelector         `json:"target"`
	Duration    string                 `json:"duration"`
	Params      map[string]interface{} `json:"params,omitempty"`
}

type TargetSelector struct {
	Cluster   string            `json:"cluster"`
	Metric    string            `json:"metric"`
	Labels    map[string]string `json:"labels,omitempty"`
	Instances []string          `json:"instances,omitempty"`
}

type FaultInstance struct {
	Config    *FaultConfig `json:"config"`
	Status    string       `json:"status"`
	CreatedAt time.Time    `json:"created_at"`
	StartedAt time.Time    `json:"started_at,omitempty"`
	EndedAt   time.Time    `json:"ended_at,omitempty"`
}

type SpikeConfig struct {
	TargetSelector
	Amplitude float64 `json:"amplitude"`
	Duration  string  `json:"duration"`
	Shape     string  `json:"shape,omitempty"`
}

type DegradationConfig struct {
	TargetSelector
	StartValue float64 `json:"start_value"`
	EndValue   float64 `json:"end_value"`
	Duration   string  `json:"duration"`
	CurveType  string  `json:"curve_type,omitempty"`
}

type OutageConfig struct {
	TargetSelector
	Duration string `json:"duration"`
}

func NewService() *Service {
	return &Service{
		faults: make(map[string]*FaultInstance),
	}
}

func (s *Service) GetActiveFaults() []*FaultInstance {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]*FaultInstance, 0, len(s.faults))
	for _, f := range s.faults {
		if f.Status == "running" {
			result = append(result, f)
		}
	}
	return result
}

func (s *Service) StartFault(cfg *FaultConfig) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if cfg.ID == "" {
		cfg.ID = fmt.Sprintf("fault-%d", time.Now().UnixNano())
	}

	instance := &FaultInstance{
		Config:    cfg,
		Status:    "running",
		CreatedAt: time.Now(),
		StartedAt: time.Now(),
	}

	s.faults[cfg.ID] = instance

	go func() {
		duration, _ := time.ParseDuration(cfg.Duration)
		if duration > 0 {
			time.Sleep(duration)
			s.mu.Lock()
			if f, ok := s.faults[cfg.ID]; ok {
				f.Status = "completed"
				f.EndedAt = time.Now()
			}
			s.mu.Unlock()
		}
	}()

	return cfg.ID, nil
}

func (s *Service) StopFault(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	f, ok := s.faults[id]
	if !ok {
		return fmt.Errorf("fault not found: %s", id)
	}

	f.Status = "stopped"
	f.EndedAt = time.Now()

	return nil
}

func (s *Service) CreateSpike(cfg *SpikeConfig) (string, error) {
	faultCfg := &FaultConfig{
		Type:        FaultMetricSpike,
		Name:        fmt.Sprintf("Spike on %s", cfg.Metric),
		Description: fmt.Sprintf("Metric spike with amplitude %.2f", cfg.Amplitude),
		Target: TargetSelector{
			Cluster:   cfg.Cluster,
			Metric:    cfg.Metric,
			Labels:    cfg.Labels,
			Instances: cfg.Instances,
		},
		Duration: cfg.Duration,
		Params: map[string]interface{}{
			"amplitude": cfg.Amplitude,
			"shape":     cfg.Shape,
		},
	}

	return s.StartFault(faultCfg)
}

func (s *Service) CreateOutage(cfg *OutageConfig) (string, error) {
	faultCfg := &FaultConfig{
		Type:        FaultOutage,
		Name:        fmt.Sprintf("Outage on %s", cfg.Cluster),
		Description: "Service outage simulation",
		Target: TargetSelector{
			Cluster:   cfg.Cluster,
			Metric:    cfg.Metric,
			Labels:    cfg.Labels,
			Instances: cfg.Instances,
		},
		Duration: cfg.Duration,
	}

	return s.StartFault(faultCfg)
}

func (s *Service) CreateDegradation(cfg *DegradationConfig) (string, error) {
	faultCfg := &FaultConfig{
		Type:        FaultMetricDegradation,
		Name:        fmt.Sprintf("Degradation on %s", cfg.Metric),
		Description: fmt.Sprintf("Performance degradation from %.2f to %.2f", cfg.StartValue, cfg.EndValue),
		Target: TargetSelector{
			Cluster:   cfg.Cluster,
			Metric:    cfg.Metric,
			Labels:    cfg.Labels,
			Instances: cfg.Instances,
		},
		Duration: cfg.Duration,
		Params: map[string]interface{}{
			"start_value": cfg.StartValue,
			"end_value":   cfg.EndValue,
			"curve_type":  cfg.CurveType,
		},
	}

	return s.StartFault(faultCfg)
}

func (s *Service) GetFault(id string) (*FaultInstance, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	f, ok := s.faults[id]
	return f, ok
}

func (s *Service) GetAllFaults() []*FaultInstance {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]*FaultInstance, 0, len(s.faults))
	for _, f := range s.faults {
		result = append(result, f)
	}
	return result
}

func (s *Service) CleanCompleted() {
	s.mu.Lock()
	defer s.mu.Unlock()

	for id, f := range s.faults {
		if f.Status == "completed" || f.Status == "stopped" {
			if time.Since(f.EndedAt) > 24*time.Hour {
				delete(s.faults, id)
			}
		}
	}
}
