package main

import (
	"context"
	"log"
	"math"
	"math/rand"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"anomaly-detector/alert"
	"anomaly-detector/api"
	"anomaly-detector/clustering"
	"anomaly-detector/correlation"
	"anomaly-detector/detector"
	"anomaly-detector/injection"
	"anomaly-detector/model"
	"anomaly-detector/prediction"
	"anomaly-detector/prometheus"
	"anomaly-detector/rootcause"
)

type DemoDataSource struct {
	mu     sync.RWMutex
	series map[string][]model.TimeSeriesPoint
}

func NewDemoDataSource() *DemoDataSource {
	return &DemoDataSource{
		series: make(map[string][]model.TimeSeriesPoint),
	}
}

func (d *DemoDataSource) Generate() {
	now := time.Now()
	start := now.Add(-2 * time.Hour)

	metrics := []struct {
		name     string
		base     float64
		amp      float64
		period   int
		noisy    float64
		spikeAt  int
		spikeVal float64
		dropAt   int
		dropVal  float64
		correlatedWith string
	}{
		{"http_requests_total", 100, 30, 60, 5, 45, 200, 80, 10, "response_time_ms"},
		{"cpu_usage_percent", 50, 15, 60, 3, 50, 95, 70, 5, "memory_usage_percent"},
		{"memory_usage_percent", 60, 10, 60, 2, 48, 90, 0, 0, "cpu_usage_percent"},
		{"response_time_ms", 200, 50, 60, 10, 45, 800, 0, 0, "http_requests_total"},
		{"error_rate_percent", 1, 2, 60, 0.5, 50, 15, 0, 0, "response_time_ms"},
		{"disk_io_mbps", 50, 20, 60, 5, 0, 0, 0, 0, ""},
		{"network_throughput_mbps", 200, 50, 60, 10, 45, 500, 0, 0, "http_requests_total"},
		{"active_connections", 500, 100, 60, 20, 50, 1200, 80, 50, "http_requests_total"},
	}

	for _, m := range metrics {
		var points []model.TimeSeriesPoint
		for i := 0; i < 120; i++ {
			t := start.Add(time.Duration(i) * time.Minute)
			val := m.base +
				m.amp*math.Sin(2*math.Pi*float64(i)/float64(m.period)) +
				m.noisy*(rand.Float64()-0.5)*2

			if m.spikeAt > 0 && i == m.spikeAt {
				val = m.spikeVal
			}
			if m.dropAt > 0 && i == m.dropAt {
				val = m.dropVal
			}

			points = append(points, model.TimeSeriesPoint{
				Timestamp: t,
				Value:     val,
			})
		}
		d.series[m.name] = points
	}
}

func (d *DemoDataSource) GetSeries(name string) []model.TimeSeriesPoint {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return d.series[name]
}

func (d *DemoDataSource) GetAllSeries() map[string][]model.TimeSeriesPoint {
	d.mu.RLock()
	defer d.mu.RUnlock()
	result := make(map[string][]model.TimeSeriesPoint)
	for k, v := range d.series {
		result[k] = v
	}
	return result
}

func main() {
	promURL := os.Getenv("PROMETHEUS_URL")
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	promClient := prometheus.NewClient(promURL)

	detectionConfig := model.DetectionConfig{
		PrometheusURL:      promURL,
		QueryInterval:      time.Minute,
		Lookback:           2 * time.Hour,
		MaxAnomalies:       0.1,
		Alpha:              0.05,
		Direction:          model.DirectionBoth,
		Period:             0,
		EnablePeriodDetect: true,
		MinPeriod:          2,
		MaxPeriod:          60,
	}

	alertConfig := model.AlertConfig{
		GroupWait:         30 * time.Second,
		GroupInterval:     5 * time.Minute,
		RepeatInterval:    4 * time.Hour,
		SuppressionWindow: 10 * time.Minute,
		MaxAlertsPerGroup: 10,
	}

	det := detector.NewDetector(detectionConfig)
	corr := correlation.NewCorrelator(0.05)
	corrClusterer := clustering.NewCorrelationClusterer(5*time.Minute, 0.5, 1)
	agg := alert.NewCorrelationAggregator(alertConfig, 0.5)
	rca := rootcause.NewRootCauseAnalyzer(0.5, 10*time.Minute)
	pred := prediction.NewPredictor(30*time.Minute, 0.7, 60)
	inj := injection.NewInjector(detectionConfig)

	handler := api.NewHandler(promClient, det, corr, corrClusterer, agg, rca, pred, inj)

	demo := NewDemoDataSource()

	mux := http.NewServeMux()
	handler.RegisterRoutes(mux)

	mux.HandleFunc("/api/demo/generate", func(w http.ResponseWriter, r *http.Request) {
		demo.Generate()
		api.WriteJSONHelper(w, http.StatusOK, map[string]interface{}{
			"status": "generated",
		})
	})

	mux.HandleFunc("/api/demo/detect", func(w http.ResponseWriter, r *http.Request) {
		allSeries := demo.GetAllSeries()
		if len(allSeries) == 0 {
			demo.Generate()
			allSeries = demo.GetAllSeries()
		}

		var seriesList []model.TimeSeries
		seriesMap := make(map[string][]float64)
		for name, points := range allSeries {
			seriesList = append(seriesList, model.TimeSeries{
				Name:   name,
				Labels: map[string]string{"job": "demo"},
				Points: points,
			})
			vals := make([]float64, len(points))
			for i, p := range points {
				vals[i] = p.Value
			}
			seriesMap[name] = vals
		}

		allAnomalies := det.DetectBatch(seriesList)

		correlations := corr.Correlate(seriesList)
		corrAnomalies := corr.CorrelateAnomalies(allAnomalies, seriesList)
		correlations = append(correlations, corrAnomalies...)

		corrMatrix := make(map[string]float64)
		for _, c := range correlations {
			key := c.MetricA + "|||" + c.MetricB
			corrMatrix[key] = c.Coefficient
			agg.UpdateCorrelations(c.MetricA, c.MetricB, c.Coefficient)
		}

		clusters := corrClusterer.ClusterAnomaliesByCorrelation(allAnomalies, seriesList)
		newAlerts := agg.AggregateWithCorrelation(clusters, corrMatrix)

		corrMatrixNested := buildCorrelationMatrixFromFlat(corrMatrix)
		rootCauseResults := rca.AnalyzeBatch(allAnomalies, seriesMap, corrMatrixNested)

		predictionResults := pred.PredictBatch(seriesList)

		api.WriteJSONHelper(w, http.StatusOK, map[string]interface{}{
			"anomalies":       allAnomalies,
			"clusters":        clusters,
			"correlations":    correlations,
			"alerts":          newAlerts,
			"root_causes":     rootCauseResults,
			"predictions":     predictionResults.Predictions,
			"total_anomalies": len(allAnomalies),
			"total_clusters":  len(clusters),
			"total_root_causes": len(rootCauseResults),
			"total_predictions": len(predictionResults.Predictions),
			"algorithm": map[string]interface{}{
				"seasonal_detection": "STL+S-ESD (改进版)",
				"alignment":          "DTW动态时间规整",
				"clustering":         "相关性聚类",
				"aggregation":        "相关性告警合并",
				"root_cause":         "根因推荐(因果推断)",
				"prediction":         "异常预测(多维预警)",
			},
		})
	})

	mux.HandleFunc("/api/demo/series", func(w http.ResponseWriter, r *http.Request) {
		allSeries := demo.GetAllSeries()
		if len(allSeries) == 0 {
			demo.Generate()
			allSeries = demo.GetAllSeries()
		}

		var seriesList []model.TimeSeries
		for name, points := range allSeries {
			seriesList = append(seriesList, model.TimeSeries{
				Name:   name,
				Labels: map[string]string{"job": "demo"},
				Points: points,
			})
		}

		api.WriteJSONHelper(w, http.StatusOK, map[string]interface{}{
			"series": seriesList,
		})
	})

	mux.HandleFunc("/api/demo/drill", func(w http.ResponseWriter, r *http.Request) {
		allSeries := demo.GetAllSeries()
		if len(allSeries) == 0 {
			demo.Generate()
			allSeries = demo.GetAllSeries()
		}

		var seriesList []model.TimeSeries
		for name, points := range allSeries {
			seriesList = append(seriesList, model.TimeSeries{
				Name:   name,
				Labels: map[string]string{"job": "demo"},
				Points: points,
			})
		}

		drillConfigs := inj.GenerateDrillConfigs(seriesList)
		results := inj.RunDrill(seriesList, drillConfigs)
		summary := inj.ComputeDrillSummary(results)

		api.WriteJSONHelper(w, http.StatusOK, map[string]interface{}{
			"results":     results,
			"summary":     summary,
			"total_tests": len(results),
		})
	})

	mux.HandleFunc("/api/demo/predict", func(w http.ResponseWriter, r *http.Request) {
		allSeries := demo.GetAllSeries()
		if len(allSeries) == 0 {
			demo.Generate()
			allSeries = demo.GetAllSeries()
		}

		var seriesList []model.TimeSeries
		for name, points := range allSeries {
			seriesList = append(seriesList, model.TimeSeries{
				Name:   name,
				Labels: map[string]string{"job": "demo"},
				Points: points,
			})
		}

		result := pred.PredictBatch(seriesList)

		api.WriteJSONHelper(w, http.StatusOK, map[string]interface{}{
			"predictions":   result.Predictions,
			"count":         len(result.Predictions),
			"horizon":       result.Horizon.String(),
			"analysis_time": result.AnalysisTime,
		})
	})

	fs := http.FileServer(http.Dir("./frontend/dist"))
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if len(r.URL.Path) >= 5 && r.URL.Path[:5] == "/api/" {
			mux.ServeHTTP(w, r)
			return
		}
		fs.ServeHTTP(w, r)
	})

	srv := &http.Server{
		Addr:    ":" + port,
		Handler: corsMiddleware(mux),
	}

	go func() {
		demo.Generate()
		log.Printf("Demo data generated with improved algorithms")
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Printf("Starting Prometheus Anomaly Detector on port %s", port)
		log.Printf("Algorithm Stack:")
		log.Printf("  - 季节性检测: STL分解 + S-ESD (鲁棒统计)")
		log.Printf("  - 时序对齐: DTW动态时间规整")
		log.Printf("  - 异常聚类: 相关性聚类")
		log.Printf("  - 告警聚合: 相关性告警合并")
		log.Printf("  - 根因推荐: 滞后相关 + 因果推断")
		log.Printf("  - 异常预测: 趋势+周期+变化率+波动率")
		log.Printf("  - 异常演练: 注入异常验证灵敏度")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	<-quit
	log.Println("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Server stopped")
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func buildCorrelationMatrixFromFlat(flat map[string]float64) map[string]map[string]float64 {
	matrix := make(map[string]map[string]float64)
	for pair, corr := range flat {
		var a, b string
		for i := 0; i < len(pair); i++ {
			if i+3 <= len(pair) && pair[i:i+3] == "|||" {
				a = pair[:i]
				b = pair[i+3:]
				break
			}
		}
		if a == "" || b == "" {
			continue
		}
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
