package analysis

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	"docker-build-accelerator/pkg/parser"
)

type LayerRecord struct {
	LayerHash   string    `json:"layer_hash"`
	Command     string    `json:"command"`
	CommandType string    `json:"command_type"`
	SizeBytes   int64     `json:"size_bytes"`
	DurationMs  int64     `json:"duration_ms"`
	CacheHit    bool      `json:"cache_hit"`
	StageName   string    `json:"stage_name"`
	LineNumber  int       `json:"line_number"`
	CreatedAt   time.Time `json:"created_at"`
}

type BuildHistory struct {
	BuildID       string         `json:"build_id"`
	Dockerfile    string         `json:"dockerfile"`
	ImageName     string         `json:"image_name"`
	StartTime     time.Time      `json:"start_time"`
	EndTime       time.Time      `json:"end_time"`
	TotalDuration int64          `json:"total_duration_ms"`
	TotalSize     int64          `json:"total_size_bytes"`
	Layers        []*LayerRecord `json:"layers"`
	Success       bool           `json:"success"`
}

type AnalysisReport struct {
	AverageBuildTimeMs   int64
	AverageImageSize     int64
	SlowestLayers        []*LayerRecord
	LargestLayers        []*LayerRecord
	CacheHitRate         float64
	TotalBuilds          int
	CommandTypeStats     map[string]*CommandStats
	OptimizationTips     []string
	HistoricalTrends     []*TrendData
}

type CommandStats struct {
	Count          int
	TotalDuration  int64
	TotalSize      int64
	AvgDuration    int64
	AvgSize        int64
	CacheHitCount  int
}

type TrendData struct {
	BuildIndex    int
	DurationMs    int64
	SizeBytes     int64
	CacheHitRate  float64
	Timestamp     time.Time
}

type Analyzer struct {
	HistoryDir string
	Histories  []*BuildHistory
}

func NewAnalyzer(historyDir string) (*Analyzer, error) {
	if err := os.MkdirAll(historyDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create history directory: %w", err)
	}

	return &Analyzer{
		HistoryDir: historyDir,
		Histories:  make([]*BuildHistory, 0),
	}, nil
}

func (a *Analyzer) RecordBuild(history *BuildHistory) error {
	data, err := json.MarshalIndent(history, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal build history: %w", err)
	}

	filename := filepath.Join(a.HistoryDir, fmt.Sprintf("build_%s.json", history.BuildID))
	if err := os.WriteFile(filename, data, 0644); err != nil {
		return fmt.Errorf("failed to write build history: %w", err)
	}

	a.Histories = append(a.Histories, history)
	return nil
}

func (a *Analyzer) LoadHistories() error {
	files, err := filepath.Glob(filepath.Join(a.HistoryDir, "build_*.json"))
	if err != nil {
		return fmt.Errorf("failed to list history files: %w", err)
	}

	for _, file := range files {
		data, err := os.ReadFile(file)
		if err != nil {
			continue
		}

		var history BuildHistory
		if err := json.Unmarshal(data, &history); err != nil {
			continue
		}

		a.Histories = append(a.Histories, &history)
	}

	sort.Slice(a.Histories, func(i, j int) bool {
		return a.Histories[i].StartTime.Before(a.Histories[j].StartTime)
	})

	return nil
}

func (a *Analyzer) GenerateReport() *AnalysisReport {
	if len(a.Histories) == 0 {
		return &AnalysisReport{
			TotalBuilds:      0,
			CommandTypeStats: make(map[string]*CommandStats),
			OptimizationTips: []string{"No build history available for analysis"},
		}
	}

	report := &AnalysisReport{
		TotalBuilds:      len(a.Histories),
		CommandTypeStats: make(map[string]*CommandStats),
	}

	var totalDuration, totalSize int64
	var cacheHits, totalLayers int
	var allLayers []*LayerRecord

	for _, history := range a.Histories {
		totalDuration += history.TotalDuration
		totalSize += history.TotalSize

		for _, layer := range history.Layers {
			allLayers = append(allLayers, layer)
			totalLayers++
			if layer.CacheHit {
				cacheHits++
			}

			stats := report.CommandTypeStats[layer.CommandType]
			if stats == nil {
				stats = &CommandStats{}
				report.CommandTypeStats[layer.CommandType] = stats
			}
			stats.Count++
			stats.TotalDuration += layer.DurationMs
			stats.TotalSize += layer.SizeBytes
			if layer.CacheHit {
				stats.CacheHitCount++
			}
		}
	}

	report.AverageBuildTimeMs = totalDuration / int64(len(a.Histories))
	report.AverageImageSize = totalSize / int64(len(a.Histories))
	if totalLayers > 0 {
		report.CacheHitRate = float64(cacheHits) / float64(totalLayers)
	}

	for cmdType, stats := range report.CommandTypeStats {
		stats.AvgDuration = stats.TotalDuration / int64(stats.Count)
		if stats.TotalSize > 0 {
			stats.AvgSize = stats.TotalSize / int64(stats.Count)
		}
		_ = cmdType
	}

	sort.Slice(allLayers, func(i, j int) bool {
		return allLayers[i].DurationMs > allLayers[j].DurationMs
	})
	report.SlowestLayers = takeTop(allLayers, 10)

	sort.Slice(allLayers, func(i, j int) bool {
		return allLayers[i].SizeBytes > allLayers[j].SizeBytes
	})
	report.LargestLayers = takeTop(allLayers, 10)

	report.OptimizationTips = a.generateOptimizationTips(report)
	report.HistoricalTrends = a.generateTrends()

	return report
}

func (a *Analyzer) generateOptimizationTips(report *AnalysisReport) []string {
	var tips []string

	if report.CacheHitRate < 0.5 {
		tips = append(tips, 
			fmt.Sprintf("Cache hit rate is low (%.1f%%). Consider reorganizing Dockerfile commands to improve cache utilization.", 
				report.CacheHitRate*100))
	}

	if runStats, ok := report.CommandTypeStats[string(parser.CmdRun)]; ok && runStats.Count > 0 {
		if runStats.AvgDuration > 30000 {
			tips = append(tips, 
				fmt.Sprintf("RUN commands average %.1fs. Consider combining multiple RUN commands or using multi-stage builds.", 
					float64(runStats.AvgDuration)/1000))
		}
	}

	if len(report.LargestLayers) > 0 && report.LargestLayers[0].SizeBytes > 500*1024*1024 {
		tips = append(tips, 
			fmt.Sprintf("Largest layer is %s (%.2f MB). Consider using .dockerignore or smaller base images.", 
				report.LargestLayers[0].CommandType,
				float64(report.LargestLayers[0].SizeBytes)/1024/1024))
	}

	for _, layer := range report.SlowestLayers {
		if layer.DurationMs > 60000 && !layer.CacheHit {
			tips = append(tips,
				fmt.Sprintf("Slow command: %s takes %.1fs. Consider caching this step.",
					layer.Command, float64(layer.DurationMs)/1000))
			break
		}
	}

	if len(tips) == 0 {
		tips = append(tips, "No major optimization opportunities detected. Keep up the good work!")
	}

	return tips
}

func (a *Analyzer) generateTrends() []*TrendData {
	var trends []*TrendData

	windowSize := 1
	if len(a.Histories) > 20 {
		windowSize = len(a.Histories) / 10
	}

	for i := 0; i < len(a.Histories); i += windowSize {
		end := i + windowSize
		if end > len(a.Histories) {
			end = len(a.Histories)
		}

		var avgDuration, avgSize int64
		var avgCacheRate float64

		for j := i; j < end; j++ {
			avgDuration += a.Histories[j].TotalDuration
			avgSize += a.Histories[j].TotalSize

			cacheHits := 0
			total := len(a.Histories[j].Layers)
			for _, layer := range a.Histories[j].Layers {
				if layer.CacheHit {
					cacheHits++
				}
			}
			if total > 0 {
				avgCacheRate += float64(cacheHits) / float64(total)
			}
		}

		count := int64(end - i)
		trends = append(trends, &TrendData{
			BuildIndex:   i,
			DurationMs:   avgDuration / count,
			SizeBytes:    avgSize / count,
			CacheHitRate: avgCacheRate / float64(count),
			Timestamp:    a.Histories[i].StartTime,
		})
	}

	return trends
}

func takeTop(layers []*LayerRecord, n int) []*LayerRecord {
	if len(layers) <= n {
		return layers
	}
	return layers[:n]
}

func (ar *AnalysisReport) Print() {
	fmt.Println("\n=== Build Analysis Report ===")
	fmt.Printf("Total Builds Analyzed: %d\n", ar.TotalBuilds)
	fmt.Printf("Average Build Time: %.2fs\n", float64(ar.AverageBuildTimeMs)/1000)
	fmt.Printf("Average Image Size: %.2f MB\n", float64(ar.AverageImageSize)/1024/1024)
	fmt.Printf("Cache Hit Rate: %.1f%%\n\n", ar.CacheHitRate*100)

	fmt.Println("=== Slowest Layers (Top 5) ===")
	for i, layer := range takeTop(ar.SlowestLayers, 5) {
		fmt.Printf("%d. [%s] %.2fs - %.2f MB - %s\n",
			i+1, layer.CommandType,
			float64(layer.DurationMs)/1000,
			float64(layer.SizeBytes)/1024/1024,
			truncate(layer.Command, 50))
	}

	fmt.Println("\n=== Optimization Tips ===")
	for i, tip := range ar.OptimizationTips {
		fmt.Printf("%d. %s\n", i+1, tip)
	}

	fmt.Println("\n=== Command Type Statistics ===")
	for cmdType, stats := range ar.CommandTypeStats {
		fmt.Printf("  %-8s - Count: %d, Avg: %.1fs, Avg Size: %.2f MB\n",
			cmdType, stats.Count,
			float64(stats.AvgDuration)/1000,
			float64(stats.AvgSize)/1024/1024)
	}
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}

func NewBuildHistory(buildID, dockerfile, imageName string) *BuildHistory {
	return &BuildHistory{
		BuildID:    buildID,
		Dockerfile: dockerfile,
		ImageName:  imageName,
		StartTime:  time.Now(),
		Layers:     make([]*LayerRecord, 0),
	}
}

func (bh *BuildHistory) AddLayer(layer *LayerRecord) {
	bh.Layers = append(bh.Layers, layer)
}

func (bh *BuildHistory) Complete(success bool) {
	bh.EndTime = time.Now()
	bh.TotalDuration = bh.EndTime.Sub(bh.StartTime).Milliseconds()
	bh.Success = success

	var totalSize int64
	for _, layer := range bh.Layers {
		totalSize += layer.SizeBytes
	}
	bh.TotalSize = totalSize
}
