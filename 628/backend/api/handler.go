package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"anomaly-detector/alert"
	"anomaly-detector/clustering"
	"anomaly-detector/correlation"
	"anomaly-detector/detector"
	"anomaly-detector/injection"
	"anomaly-detector/model"
	"anomaly-detector/prediction"
	"anomaly-detector/prometheus"
	"anomaly-detector/rootcause"
)

type Handler struct {
	promClient      *prometheus.Client
	detector        *detector.Detector
	correlator      *correlation.Correlator
	clusterer       *clustering.DBSCAN
	corrClusterer   *clustering.CorrelationClusterer
	aggregator      *alert.Aggregator
	corrAggregator  *alert.CorrelationBasedAggregator
	rootCauseAnalyzer *rootcause.RootCauseAnalyzer
	predictor       *prediction.Predictor
	injector        *injection.Injector
}

func NewHandler(
	promClient *prometheus.Client,
	det *detector.Detector,
	corr *correlation.Correlator,
	corrClust *clustering.CorrelationClusterer,
	corrAgg *alert.CorrelationBasedAggregator,
	rca *rootcause.RootCauseAnalyzer,
	pred *prediction.Predictor,
	inj *injection.Injector,
) *Handler {
	return &Handler{
		promClient:        promClient,
		detector:          det,
		correlator:        corr,
		corrClusterer:     corrClust,
		corrAggregator:    corrAgg,
		rootCauseAnalyzer: rca,
		predictor:         pred,
		injector:          inj,
	}
}

func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/api/detect", h.handleDetect)
	mux.HandleFunc("/api/detect/batch", h.handleDetectBatch)
	mux.HandleFunc("/api/correlate", h.handleCorrelate)
	mux.HandleFunc("/api/alerts", h.handleAlerts)
	mux.HandleFunc("/api/alerts/acknowledge", h.handleAcknowledge)
	mux.HandleFunc("/api/metrics/query", h.handleMetricsQuery)
	mux.HandleFunc("/api/health", h.handleHealth)
	mux.HandleFunc("/api/algorithm/info", h.handleAlgorithmInfo)
	mux.HandleFunc("/api/rootcause/analyze", h.handleRootCauseAnalyze)
	mux.HandleFunc("/api/prediction/forecast", h.handlePredictionForecast)
	mux.HandleFunc("/api/injection/drill", h.handleInjectionDrill)
	mux.HandleFunc("/api/injection/configs", h.handleInjectionConfigs)
}

func (h *Handler) handleAlgorithmInfo(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"seasonal_detection": "STL分解 + S-ESD (Seasonal ESD with Robust Statistics)",
		"alignment":          "DTW动态时间规整 (Dynamic Time Warping)",
		"clustering":         "相关性聚类 (Correlation-Based Clustering)",
		"aggregation":        "相关性告警合并 (Correlation-Based Alert Aggregation)",
		"root_cause":         "根因推荐 (Causal Inference + Lag Correlation)",
		"prediction":         "异常预测 (Trend + Seasonal + Rate-of-Change + Volatility)",
		"injection":          "异常演练 (Spike/Drop/Gradual/Oscillation Injection)",
		"features": []string{
			"STL时序分解: 趋势/季节/残差三部分",
			"S-ESD检测: 鲁棒统计 + 广义极值学生化残差",
			"DTW对齐: 消除时序偏移,准确计算相关性",
			"相关性聚类: 按指标相关性和时间聚类异常",
			"相关性合并: 真正相关的告警智能合并",
			"根因推荐: 基于滞后相关和因果推断推测异常原因",
			"异常预测: 趋势+周期+变化率+波动率多维度预警",
			"异常演练: 注入异常验证检测灵敏度",
		},
	})
}

func (h *Handler) handleRootCauseAnalyze(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Anomalies []model.Anomaly          `json:"anomalies"`
		Series    map[string][]float64     `json:"series_map"`
		Correlations map[string]float64    `json:"correlations"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	corrMatrix := buildCorrelationMatrix(req.Correlations)

	results := h.rootCauseAnalyzer.AnalyzeBatch(req.Anomalies, req.Series, corrMatrix)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"root_causes":    results,
		"total_analyzed": len(results),
	})
}

func (h *Handler) handlePredictionForecast(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Series  []model.TimeSeries `json:"series"`
		Horizon float64            `json:"horizon_minutes"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	horizon := 30 * time.Minute
	if req.Horizon > 0 {
		horizon = time.Duration(req.Horizon) * time.Minute
	}

	pred := prediction.NewPredictor(horizon, 0.7, 60)
	result := pred.PredictBatch(req.Series)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"predictions":  result.Predictions,
		"count":        len(result.Predictions),
		"horizon":      result.Horizon.String(),
		"analysis_time": result.AnalysisTime,
	})
}

func (h *Handler) handleInjectionDrill(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Series  []model.TimeSeries    `json:"series"`
		Configs []model.InjectionConfig `json:"configs"`
		Auto    bool                  `json:"auto"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	inj := injection.NewInjector(h.detector.GetConfig())

	var configs []model.InjectionConfig
	if req.Auto || len(req.Configs) == 0 {
		configs = inj.GenerateDrillConfigs(req.Series)
	} else {
		configs = req.Configs
	}

	results := inj.RunDrill(req.Series, configs)
	summary := inj.ComputeDrillSummary(results)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"results":    results,
		"summary":    summary,
		"total_tests": len(results),
	})
}

func (h *Handler) handleInjectionConfigs(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Series []model.TimeSeries `json:"series"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	inj := injection.NewInjector(h.detector.GetConfig())
	configs := inj.GenerateDrillConfigs(req.Series)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"configs": configs,
		"count":   len(configs),
	})
}

func (h *Handler) handleDetect(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Query     string  `json:"query"`
		Start     string  `json:"start"`
		End       string  `json:"end"`
		Step      string  `json:"step"`
		Direction string  `json:"direction"`
		Alpha     float64 `json:"alpha"`
		Period    int     `json:"period"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	start, err := parseTime(req.Start, time.Now().Add(-1*time.Hour))
	if err != nil {
		http.Error(w, fmt.Sprintf("invalid start time: %v", err), http.StatusBadRequest)
		return
	}

	end, err := parseTime(req.End, time.Now())
	if err != nil {
		http.Error(w, fmt.Sprintf("invalid end time: %v", err), http.StatusBadRequest)
		return
	}

	step := time.Minute
	if req.Step != "" {
		if s, err := time.ParseDuration(req.Step); err == nil {
			step = s
		}
	}

	series, err := h.promClient.QueryRange(r.Context(), req.Query, start, end, step)
	if err != nil {
		http.Error(w, fmt.Sprintf("prometheus query failed: %v", err), http.StatusInternalServerError)
		return
	}

	direction := model.AnomalyDirection(req.Direction)
	if direction == "" {
		direction = model.DirectionBoth
	}

	config := model.DetectionConfig{
		Alpha:              req.Alpha,
		Direction:          direction,
		Period:             req.Period,
		EnablePeriodDetect: req.Period <= 0,
		MinPeriod:          2,
		MaxPeriod:          len(series) / 3,
		MaxAnomalies:       0.1,
	}

	det := detector.NewDetector(config)
	var allAnomalies []model.Anomaly
	for _, ts := range series {
		anomalies := det.Detect(ts)
		allAnomalies = append(allAnomalies, anomalies...)
	}

	clusters := h.corrClusterer.ClusterAnomaliesByCorrelation(allAnomalies, series)

	corrMatrix := make(map[string]float64)
	correlations := h.correlator.Correlate(series)
	for _, c := range correlations {
		key := c.MetricA + "|||" + c.MetricB
		corrMatrix[key] = c.Coefficient
		h.corrAggregator.UpdateCorrelations(c.MetricA, c.MetricB, c.Coefficient)
	}

	_ = h.corrAggregator.AggregateWithCorrelation(clusters, corrMatrix)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"anomalies": allAnomalies,
		"clusters":  clusters,
		"count":     len(allAnomalies),
		"algorithm": "STL+S-ESD + DTW对齐 + 相关性聚类",
	})
}

func (h *Handler) handleDetectBatch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Queries   []string `json:"queries"`
		Start     string   `json:"start"`
		End       string   `json:"end"`
		Step      string   `json:"step"`
		Direction string   `json:"direction"`
		Alpha     float64  `json:"alpha"`
		Period    int      `json:"period"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	start, _ := parseTime(req.Start, time.Now().Add(-1*time.Hour))
	end, _ := parseTime(req.End, time.Now())
	step := time.Minute
	if req.Step != "" {
		if s, err := time.ParseDuration(req.Step); err == nil {
			step = s
		}
	}

	var allSeries []model.TimeSeries
	for _, query := range req.Queries {
		series, err := h.promClient.QueryRange(r.Context(), query, start, end, step)
		if err != nil {
			continue
		}
		allSeries = append(allSeries, series...)
	}

	direction := model.AnomalyDirection(req.Direction)
	if direction == "" {
		direction = model.DirectionBoth
	}

	config := model.DetectionConfig{
		Alpha:              req.Alpha,
		Direction:          direction,
		Period:             req.Period,
		EnablePeriodDetect: req.Period <= 0,
		MinPeriod:          2,
		MaxPeriod:          len(allSeries) / 3,
		MaxAnomalies:       0.1,
	}

	det := detector.NewDetector(config)
	allAnomalies := det.DetectBatch(allSeries)

	correlations := h.correlator.Correlate(allSeries)
	corrAnomalies := h.correlator.CorrelateAnomalies(allAnomalies, allSeries)
	correlations = append(correlations, corrAnomalies...)

	corrMatrix := make(map[string]float64)
	for _, c := range correlations {
		key := c.MetricA + "|||" + c.MetricB
		corrMatrix[key] = c.Coefficient
		h.corrAggregator.UpdateCorrelations(c.MetricA, c.MetricB, c.Coefficient)
	}

	clusters := h.corrClusterer.ClusterAnomaliesByCorrelation(allAnomalies, allSeries)
	newAlerts := h.corrAggregator.AggregateWithCorrelation(clusters, corrMatrix)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"anomalies":    allAnomalies,
		"clusters":     clusters,
		"correlations": correlations,
		"alerts":       newAlerts,
		"count":        len(allAnomalies),
		"algorithm": map[string]interface{}{
			"seasonal_detection": "STL+S-ESD",
			"alignment":          "DTW动态时间规整",
			"clustering":         "相关性聚类",
			"aggregation":        "相关性告警合并",
		},
	})
}

func (h *Handler) handleCorrelate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Queries []string `json:"queries"`
		Start   string   `json:"start"`
		End     string   `json:"end"`
		Step    string   `json:"step"`
		UseDTW  bool     `json:"use_dtw"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	start, _ := parseTime(req.Start, time.Now().Add(-1*time.Hour))
	end, _ := parseTime(req.End, time.Now())
	step := time.Minute
	if req.Step != "" {
		if s, err := time.ParseDuration(req.Step); err == nil {
			step = s
		}
	}

	var allSeries []model.TimeSeries
	for _, query := range req.Queries {
		series, err := h.promClient.QueryRange(r.Context(), query, start, end, step)
		if err != nil {
			continue
		}
		allSeries = append(allSeries, series...)
	}

	var results []model.CorrelationResult
	if req.UseDTW {
		results = h.correlator.CorrelateWithDTW(allSeries)
	} else {
		results = h.correlator.Correlate(allSeries)
	}

	corrGroups := h.correlator.FindCorrelatedGroups(allSeries, 0.5)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"correlations": results,
		"groups":       corrGroups,
		"alignment":    req.UseDTW,
	})
}

func (h *Handler) handleAlerts(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	alerts := h.corrAggregator.GetAlerts()

	showSuppressed := r.URL.Query().Get("suppressed")
	if showSuppressed != "true" {
		var filtered []model.Alert
		for _, a := range alerts {
			if !a.Suppressed {
				filtered = append(filtered, a)
			}
		}
		alerts = filtered
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"alerts":      alerts,
		"count":       len(alerts),
		"aggregation": "correlation-based",
	})
}

func (h *Handler) handleAcknowledge(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		AlertID string `json:"alert_id"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if h.corrAggregator.AcknowledgeAlert(req.AlertID) {
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"status": "acknowledged",
		})
	} else {
		http.Error(w, "alert not found", http.StatusNotFound)
	}
}

func (h *Handler) handleMetricsQuery(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query().Get("query")
	if query == "" {
		http.Error(w, "query parameter required", http.StatusBadRequest)
		return
	}

	start, _ := parseTime(r.URL.Query().Get("start"), time.Now().Add(-1*time.Hour))
	end, _ := parseTime(r.URL.Query().Get("end"), time.Now())
	step := time.Minute
	if s := r.URL.Query().Get("step"); s != "" {
		if parsed, err := time.ParseDuration(s); err == nil {
			step = parsed
		}
	}

	series, err := h.promClient.QueryRange(r.Context(), query, start, end, step)
	if err != nil {
		http.Error(w, fmt.Sprintf("prometheus query failed: %v", err), http.StatusInternalServerError)
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"series": series,
	})
}

func (h *Handler) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status": "healthy",
		"time":   time.Now().Format(time.RFC3339),
	})
}

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func WriteJSONHelper(w http.ResponseWriter, status int, data interface{}) {
	writeJSON(w, status, data)
}

func parseTime(s string, defaultTime time.Time) (time.Time, error) {
	if s == "" {
		return defaultTime, nil
	}

	if ts, err := strconv.ParseFloat(s, 64); err == nil {
		return time.Unix(int64(ts), 0), nil
	}

	if t, err := time.Parse(time.RFC3339, s); err == nil {
		return t, nil
	}

	d, err := time.ParseDuration(s)
	if err != nil {
		return defaultTime, nil
	}

	return time.Now().Add(-d), nil
}

func buildCorrelationMatrix(corrMap map[string]float64) map[string]map[string]float64 {
	matrix := make(map[string]map[string]float64)
	for pair, corr := range corrMap {
		parts := splitCorrelationPair(pair)
		if len(parts) != 2 {
			continue
		}
		a, b := parts[0], parts[1]
		if matrix[a] == nil {
			matrix[a] = make(map[string]float64)
		}
		matrix[a][b] = corr
		if matrix[b] == nil {
			matrix[b] = make(map[string]float64)
		}
		matrix[b][a] = corr
	}
	return matrix
}

func splitCorrelationPair(pair string) []string {
	for _, sep := range []string{"|||", "|", ","} {
		for i := 0; i <= len(pair)-len(sep); i++ {
			if pair[i:i+len(sep)] == sep {
				return []string{pair[:i], pair[i+len(sep):]}
			}
		}
	}
	return nil
}
