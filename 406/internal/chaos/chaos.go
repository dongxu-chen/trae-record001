package chaos

import (
	"context"
	"fmt"
	"math/rand"
	"net/http"
	"sync"
	"time"
	"health-check/internal/config"
	"health-check/internal/model"
)

type FaultType string

const (
	FaultDelay        FaultType = "delay"
	FaultError        FaultType = "error"
	FaultTimeout      FaultType = "timeout"
	FaultAbort        FaultType = "abort"
	FaultShadow       FaultType = "shadow"
)

type Injector struct {
	mu         sync.RWMutex
	cfg        *config.ChaosConfig
	shadowCfg  *config.ShadowConfig
	enabled    bool
	faults     map[string]*activeFault
	shadowURLs map[string]string
	httpClient *http.Client
}

type activeFault struct {
	endpointID string
	faultType  FaultType
	duration   time.Duration
	rate       float64
	startTime  time.Time
	shadow     bool
}

type ShadowResult struct {
	IsShadow    bool
	ShadowURL   string
	CompareData interface{}
}

func New(cfg *config.ChaosConfig, shadowCfg *config.ShadowConfig) *Injector {
	return &Injector{
		cfg:        cfg,
		shadowCfg:  shadowCfg,
		enabled:    cfg.Enabled,
		faults:     make(map[string]*activeFault),
		shadowURLs: make(map[string]string),
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

func (i *Injector) Start() {
	if !i.enabled {
		return
	}

	go i.scheduler()
}

func (i *Injector) scheduler() {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		i.checkAndInject()
	}
}

func (i *Injector) checkAndInject() {
	now := time.Now()
	currentHour := now.Hour()

	i.mu.Lock()
	defer i.mu.Unlock()

	for id, fault := range i.faults {
		if now.After(fault.startTime.Add(fault.duration)) {
			delete(i.faults, id)
		}
	}

	for _, ep := range i.cfg.Endpoints {
		if ep.StartHour != 0 && currentHour < ep.StartHour {
			continue
		}
		if ep.EndHour != 0 && currentHour >= ep.EndHour {
			continue
		}

		if _, exists := i.faults[ep.EndpointID]; !exists {
			if rand.Float64() < 0.1 {
				faultType := FaultType(ep.FaultType)
				if ep.Shadow || i.shadowCfg.Enabled {
					faultType = FaultShadow
				}

				i.faults[ep.EndpointID] = &activeFault{
					endpointID: ep.EndpointID,
					faultType:  faultType,
					duration:   time.Duration(ep.Duration) * time.Second,
					rate:       ep.Rate,
					startTime:  now,
					shadow:     ep.Shadow || i.shadowCfg.Enabled,
				}
			}
		}
	}
}

func (i *Injector) Inject(endpointID string, endpoint *model.Endpoint, result *model.ProbeResult, ctx context.Context) (*model.ProbeResult, context.Context) {
	if !i.enabled {
		return result, ctx
	}

	i.mu.RLock()
	fault, exists := i.faults[endpointID]
	i.mu.RUnlock()

	if !exists {
		return result, ctx
	}

	if rand.Float64() > fault.rate {
		return result, ctx
	}

	if fault.shadow || fault.faultType == FaultShadow {
		result.IsShadow = true
		shadowResult := i.executeShadowCall(endpoint, result)
		_ = shadowResult
		return result, ctx
	}

	switch fault.faultType {
	case FaultDelay:
		delay := time.Duration(rand.Intn(2000)) * time.Millisecond
		time.Sleep(delay)
		result.Latency += delay
	case FaultError:
		result.Status = model.StatusDown
		result.Error = "chaos injection: simulated error"
	case FaultTimeout:
		result.Status = model.StatusDown
		result.Error = "chaos injection: simulated timeout"
	case FaultAbort:
		result.Status = model.StatusDown
		result.Error = "chaos injection: connection aborted"
	}

	return result, ctx
}

func (i *Injector) executeShadowCall(endpoint *model.Endpoint, originalResult *model.ProbeResult) *model.ProbeResult {
	if endpoint.HTTPConfig == nil || i.shadowCfg == nil {
		return originalResult
	}

	shadowURL := i.getShadowURL(endpoint)
	if shadowURL == "" {
		return originalResult
	}

	shadowResult := &model.ProbeResult{
		EndpointID: endpoint.ID,
		Name:       endpoint.Name + " (Shadow)",
		Protocol:   endpoint.Protocol,
		Timestamp:  time.Now(),
		IsShadow:   true,
	}

	url := shadowURL + endpoint.HTTPConfig.Path

	method := endpoint.HTTPConfig.Method
	if method == "" {
		method = http.MethodGet
	}

	var req *http.Request
	var err error

	if endpoint.HTTPConfig.Body != "" {
		req, err = http.NewRequestWithContext(context.Background(), method, url, nil)
	} else {
		req, err = http.NewRequestWithContext(context.Background(), method, url, nil)
	}

	if err != nil {
		shadowResult.Status = model.StatusDown
		shadowResult.Error = "shadow request creation failed: " + err.Error()
		return shadowResult
	}

	req.Header.Set(i.shadowCfg.ShadowHeader, i.shadowCfg.ShadowValue)
	for k, v := range endpoint.HTTPConfig.Headers {
		req.Header.Set(k, v)
	}

	start := time.Now()
	resp, err := i.httpClient.Do(req)
	shadowResult.Latency = time.Since(start)

	if err != nil {
		shadowResult.Status = model.StatusDown
		shadowResult.Error = "shadow call failed: " + err.Error()
		return shadowResult
	}
	defer resp.Body.Close()

	shadowResult.HTTPStatus = resp.StatusCode

	if resp.StatusCode < 400 {
		shadowResult.Status = model.StatusUp
	} else {
		shadowResult.Status = model.StatusDown
		shadowResult.Error = fmt.Sprintf("shadow call returned %d", resp.StatusCode)
	}

	return shadowResult
}

func (i *Injector) getShadowURL(endpoint *model.Endpoint) string {
	i.mu.RLock()
	defer i.mu.RUnlock()

	if url, ok := i.shadowURLs[endpoint.ID]; ok {
		return url
	}

	if i.shadowCfg != nil && i.shadowCfg.ShadowAddress != "" {
		return i.shadowCfg.ShadowAddress
	}

	return endpoint.Address
}

func (i *Injector) InjectFault(endpointID string, faultType FaultType, duration time.Duration, rate float64, shadow bool) {
	i.mu.Lock()
	defer i.mu.Unlock()

	i.faults[endpointID] = &activeFault{
		endpointID: endpointID,
		faultType:  faultType,
		duration:   duration,
		rate:       rate,
		startTime:  time.Now(),
		shadow:     shadow,
	}
}

func (i *Injector) ClearFault(endpointID string) {
	i.mu.Lock()
	defer i.mu.Unlock()

	delete(i.faults, endpointID)
}

func (i *Injector) GetActiveFaults() []map[string]interface{} {
	i.mu.RLock()
	defer i.mu.RUnlock()

	faults := make([]map[string]interface{}, 0, len(i.faults))
	for id, f := range i.faults {
		faultInfo := map[string]interface{}{
			"endpoint_id": id,
			"fault_type":  f.faultType,
			"duration":    f.duration.String(),
			"rate":        f.rate,
			"remaining":   f.startTime.Add(f.duration).Sub(time.Now()).String(),
			"shadow":      f.shadow,
		}
		faults = append(faults, faultInfo)
	}
	return faults
}

func (i *Injector) SetShadowURL(endpointID, url string) {
	i.mu.Lock()
	defer i.mu.Unlock()
	i.shadowURLs[endpointID] = url
}

func (i *Injector) Enable() {
	i.enabled = true
}

func (i *Injector) Disable() {
	i.enabled = false
	i.mu.Lock()
	defer i.mu.Unlock()
	i.faults = make(map[string]*activeFault)
}
