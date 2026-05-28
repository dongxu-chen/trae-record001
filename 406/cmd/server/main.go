package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
	"health-check/internal/alert"
	"health-check/internal/chaos"
	"health-check/internal/config"
	"health-check/internal/metrics"
	"health-check/internal/model"
	"health-check/internal/pool"
	"health-check/internal/prediction"
	"health-check/internal/probe"
	"health-check/internal/scheduler"
	"health-check/internal/tracing"
	"health-check/internal/window"
)

type HealthCheckService struct {
	cfg           *config.Config
	probePool     *pool.ProbePool
	alertEngine   *alert.Engine
	chaosInjector *chaos.Injector
	metricsExp    *metrics.Exporter
	scheduler     *scheduler.WeightedScheduler
	predictor     *prediction.Predictor
	tracer        *tracing.Tracer
	windows       map[string]*window.SlidingWindow
	results       map[string][]*model.ProbeResult
	lastRun       map[string]time.Time
	stopChan      chan struct{}
}

func NewHealthCheckService(cfgPath string) (*HealthCheckService, error) {
	cfg, err := config.Load(cfgPath)
	if err != nil {
		return nil, fmt.Errorf("load config failed: %w", err)
	}

	svc := &HealthCheckService{
		cfg:       cfg,
		windows:   make(map[string]*window.SlidingWindow),
		results:   make(map[string][]*model.ProbeResult),
		lastRun:   make(map[string]time.Time),
		stopChan:  make(chan struct{}),
	}

	svc.tracer = tracing.NewTracer(&cfg.Tracing)
	svc.scheduler = scheduler.NewWeightedScheduler(&cfg.Scheduling)
	svc.predictor = prediction.NewPredictor(&cfg.Prediction)

	probe.Init(svc.tracer)

	svc.probePool = pool.New(
		cfg.ProbePool.MinWorkers,
		cfg.ProbePool.MaxWorkers,
		cfg.ProbePool.QueueSize,
		func(ctx context.Context, ep *model.Endpoint) *model.ProbeResult {
			return probe.Do(ctx, ep)
		},
	)

	svc.alertEngine = alert.New(&cfg.Alert, cfg.AlertRules)
	svc.chaosInjector = chaos.New(&cfg.Chaos, &cfg.Shadow)
	svc.metricsExp = metrics.New()

	for _, ep := range cfg.Endpoints {
		epCopy := ep
		svc.windows[ep.ID] = window.New(cfg.Window.Duration, cfg.Window.Slots)
		svc.alertEngine.RegisterEndpoint(ep.ID, svc.windows[ep.ID])
		svc.scheduler.RegisterEndpoint(&epCopy)
		svc.lastRun[ep.ID] = time.Time{}
	}

	return svc, nil
}

func (s *HealthCheckService) Start() {
	s.probePool.Start()
	s.chaosInjector.Start()
	s.scheduler.StartAutoAdjust()

	go s.startMetricsServer()
	go s.startAdminServer()
	go s.scheduleProbes()
	go s.reportStats()
	go s.runPredictions()
	go s.cleanupTraces()

	log.Println("Health Check Service started successfully")
}

func (s *HealthCheckService) startMetricsServer() {
	if err := s.metricsExp.StartServer(s.cfg.Server.MetricsPort); err != nil {
		log.Printf("Metrics server error: %v", err)
	}
}

func (s *HealthCheckService) startAdminServer() {
	mux := http.NewServeMux()

	mux.HandleFunc("/api/endpoints", s.handleEndpoints)
	mux.HandleFunc("/api/results", s.handleResults)
	mux.HandleFunc("/api/alerts", s.handleAlerts)
	mux.HandleFunc("/api/chaos", s.handleChaos)
	mux.HandleFunc("/api/stats", s.handleStats)
	mux.HandleFunc("/api/shadow", s.handleShadow)
	mux.HandleFunc("/api/scheduler", s.handleScheduler)
	mux.HandleFunc("/api/prediction", s.handlePrediction)
	mux.HandleFunc("/api/tracing", s.handleTracing)

	addr := fmt.Sprintf(":%d", s.cfg.Server.AdminPort)
	log.Printf("Admin API server starting on port %d", s.cfg.Server.AdminPort)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Printf("Admin server error: %v", err)
	}
}

func (s *HealthCheckService) scheduleProbes() {
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			now := time.Now()
			for _, ep := range s.cfg.Endpoints {
				if s.scheduler.ShouldProbeNow(ep.ID, s.lastRun[ep.ID]) {
					epCopy := ep
					go s.doProbe(&epCopy)
					s.lastRun[ep.ID] = now
				}
			}
		case <-s.stopChan:
			return
		}
	}
}

func (s *HealthCheckService) doProbe(endpoint *model.Endpoint) {
	resultChan := s.probePool.Submit(endpoint)

	select {
	case result := <-resultChan:
		result, _ = s.chaosInjector.Inject(endpoint.ID, endpoint, result, context.Background())

		if win, ok := s.windows[endpoint.ID]; ok {
			win.Record(result)
		}

		s.metricsExp.RecordProbe(result)

		s.results[endpoint.ID] = append(s.results[endpoint.ID], result)
		if len(s.results[endpoint.ID]) > 1000 {
			s.results[endpoint.ID] = s.results[endpoint.ID][1:]
		}

		s.scheduler.RecordResult(result)
		s.predictor.RecordResult(result)

		s.alertEngine.Evaluate(endpoint, result)

	case <-time.After(time.Duration(endpoint.Timeout+2) * time.Second):
		log.Printf("Probe timeout for endpoint: %s", endpoint.Name)
	}
}

func (s *HealthCheckService) reportStats() {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		select {
		case <-s.stopChan:
			return
		default:
			activeWorkers, queueLen, _ := s.probePool.Stats()
			s.metricsExp.SetPoolStats(activeWorkers, queueLen)

			for _, ep := range s.cfg.Endpoints {
				if win, ok := s.windows[ep.ID]; ok {
					stats := win.GetStats()
					s.metricsExp.RecordWindowStats(ep.ID, ep.Name, stats)

					interval := s.scheduler.GetInterval(ep.ID)
					healthScore := s.scheduler.GetHealthScore(ep.ID)
					s.metricsExp.RecordScheduling(ep.ID, ep.Name, interval, ep.Weight, healthScore)
				}

				if pred := s.predictor.GetLastPrediction(ep.ID); pred != nil {
					s.metricsExp.RecordPrediction(pred, ep.Name)
				}
			}
		}
	}
}

func (s *HealthCheckService) runPredictions() {
	if !s.cfg.Prediction.Enabled {
		return
	}

	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		select {
		case <-s.stopChan:
			return
		default:
			predictions := s.predictor.PredictAll()
			for _, pred := range predictions {
				if pred.Critical || pred.Warning {
					log.Printf("Prediction alert for %s: %s", pred.EndpointID, pred.Message)
				}
			}
		}
	}
}

func (s *HealthCheckService) cleanupTraces() {
	if !s.cfg.Tracing.Enabled {
		return
	}

	ticker := time.NewTicker(1 * time.Hour)
	defer ticker.Stop()

	for range ticker.C {
		select {
		case <-s.stopChan:
			return
		default:
			s.tracer.CleanupOldSpans(24 * time.Hour)
		}
	}
}

func (s *HealthCheckService) handleEndpoints(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(s.cfg.Endpoints)
}

func (s *HealthCheckService) handleResults(w http.ResponseWriter, r *http.Request) {
	endpointID := r.URL.Query().Get("endpoint_id")
	w.Header().Set("Content-Type", "application/json")

	if endpointID != "" {
		json.NewEncoder(w).Encode(s.results[endpointID])
		return
	}

	allResults := make(map[string][]*model.ProbeResult)
	for id, results := range s.results {
		allResults[id] = results
	}
	json.NewEncoder(w).Encode(allResults)
}

func (s *HealthCheckService) handleAlerts(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(s.alertEngine.GetActiveAlerts())
}

func (s *HealthCheckService) handleChaos(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	if r.Method == http.MethodPost {
		var req struct {
			EndpointID string  `json:"endpoint_id"`
			FaultType  string  `json:"fault_type"`
			Duration   int     `json:"duration"`
			Rate       float64 `json:"rate"`
			Shadow     bool    `json:"shadow"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		s.chaosInjector.InjectFault(req.EndpointID, chaos.FaultType(req.FaultType),
			time.Duration(req.Duration)*time.Second, req.Rate, req.Shadow)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
		return
	}

	if r.Method == http.MethodDelete {
		endpointID := r.URL.Query().Get("endpoint_id")
		s.chaosInjector.ClearFault(endpointID)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
		return
	}

	json.NewEncoder(w).Encode(s.chaosInjector.GetActiveFaults())
}

func (s *HealthCheckService) handleShadow(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	if r.Method == http.MethodPost {
		var req struct {
			EndpointID string `json:"endpoint_id"`
			ShadowURL  string `json:"shadow_url"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		s.chaosInjector.SetShadowURL(req.EndpointID, req.ShadowURL)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"shadow_config":  s.cfg.Shadow,
		"shadow_enabled": s.cfg.Shadow.Enabled,
	})
}

func (s *HealthCheckService) handleStats(w http.ResponseWriter, r *http.Request) {
	endpointID := r.URL.Query().Get("endpoint_id")
	w.Header().Set("Content-Type", "application/json")

	if endpointID != "" {
		if win, ok := s.windows[endpointID]; ok {
			json.NewEncoder(w).Encode(win.GetStats())
			return
		}
		http.Error(w, "endpoint not found", http.StatusNotFound)
		return
	}

	allStats := make(map[string]*model.WindowStats)
	for id, win := range s.windows {
		allStats[id] = win.GetStats()
	}
	json.NewEncoder(w).Encode(allStats)
}

func (s *HealthCheckService) handleScheduler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	if r.Method == http.MethodPost {
		var req struct {
			EndpointID string `json:"endpoint_id"`
			Weight     int    `json:"weight"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		s.scheduler.AdjustEndpointWeight(req.EndpointID, req.Weight)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"intervals":    s.scheduler.GetAllIntervals(),
		"schedule_plans": s.scheduler.GetSchedulePlan(),
		"config":       s.cfg.Scheduling,
	})
}

func (s *HealthCheckService) handlePrediction(w http.ResponseWriter, r *http.Request) {
	endpointID := r.URL.Query().Get("endpoint_id")
	w.Header().Set("Content-Type", "application/json")

	if endpointID != "" {
		pred := s.predictor.Predict(endpointID)
		if pred == nil {
			pred = s.predictor.GetLastPrediction(endpointID)
		}
		anomalies := s.predictor.DetectAnomalies(endpointID)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"prediction": pred,
			"anomalies":  anomalies,
		})
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"predictions": s.predictor.GetAllPredictions(),
		"config":      s.cfg.Prediction,
	})
}

func (s *HealthCheckService) handleTracing(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	traceID := r.URL.Query().Get("trace_id")
	endpointID := r.URL.Query().Get("endpoint_id")
	limit := 100

	if traceID != "" {
		spans := s.tracer.GetTraceTree(traceID)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"trace_id": traceID,
			"spans":    spans,
		})
		return
	}

	if endpointID != "" {
		spans := s.tracer.GetSpansByEndpoint(endpointID, limit)
		deps := s.tracer.BuildDependencyChain(endpointID, 3)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"endpoint_id":  endpointID,
			"spans":        spans,
			"dependencies": deps,
		})
		return
	}

	spans := s.tracer.GetRecentSpans(limit)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"trace_count": s.tracer.GetTraceCount(),
		"span_count":  s.tracer.GetSpanCount(),
		"recent_spans": spans,
		"config":      s.cfg.Tracing,
	})
}

func (s *HealthCheckService) Stop() {
	close(s.stopChan)
	s.probePool.Stop()
	s.scheduler.Stop()
	log.Println("Health Check Service stopped")
}

func main() {
	configPath := flag.String("config", "configs/config.yaml", "Path to config file")
	flag.Parse()

	svc, err := NewHealthCheckService(*configPath)
	if err != nil {
		log.Fatalf("Failed to create service: %v", err)
	}

	svc.Start()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	svc.Stop()
}
