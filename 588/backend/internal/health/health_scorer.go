package health

import (
	"math"
	"time"
	"zk-inspector/internal/storage"
)

type HealthScore struct {
	OverallScore    float64            `json:"overall_score"`
	Grade           string             `json:"grade"`
	LastUpdated     time.Time          `json:"last_updated"`
	CategoryScores  map[string]float64 `json:"category_scores"`
	Recommendations []string           `json:"recommendations"`
	Warnings        []string           `json:"warnings"`
}

type HealthConfig struct {
	MaxRecommendedNodes      int
	MaxRecommendedTotalSize  int64
	MaxRecommendedDepth      int
	MaxRecommendedAlertCount int
}

type HealthScorer struct {
	config  HealthConfig
	storage *storage.MemoryStorage
}

func NewHealthScorer(config HealthConfig, storage *storage.MemoryStorage) *HealthScorer {
	return &HealthScorer{
		config:  config,
		storage: storage,
	}
}

func (hs *HealthScorer) calculateNodeCountScore(count int) (float64, []string) {
	warnings := []string{}

	if count <= hs.config.MaxRecommendedNodes/2 {
		return 100, warnings
	}

	ratio := float64(count) / float64(hs.config.MaxRecommendedNodes)
	score := 100 - math.Min(60, (ratio-0.5)*120)

	if ratio > 1.0 {
		warnings = append(warnings, "节点数量超过推荐上限，考虑扩容或拆分集群")
	} else if ratio > 0.8 {
		warnings = append(warnings, "节点数量接近推荐上限，建议监控增长趋势")
	}

	return math.Max(40, score), warnings
}

func (hs *HealthScorer) calculateDataSizeScore(totalSize int64) (float64, []string) {
	warnings := []string{}

	if totalSize <= hs.config.MaxRecommendedTotalSize/2 {
		return 100, warnings
	}

	ratio := float64(totalSize) / float64(hs.config.MaxRecommendedTotalSize)
	score := 100 - math.Min(60, (ratio-0.5)*120)

	if ratio > 1.0 {
		warnings = append(warnings, "总数据量超过推荐上限，建议清理或使用外部存储")
	} else if ratio > 0.8 {
		warnings = append(warnings, "数据量接近上限，注意监控增长趋势")
	}

	return math.Max(40, score), warnings
}

func (hs *HealthScorer) calculateDepthScore(maxDepth int) (float64, []string) {
	warnings := []string{}

	if maxDepth <= hs.config.MaxRecommendedDepth/2 {
		return 100, warnings
	}

	ratio := float64(maxDepth) / float64(hs.config.MaxRecommendedDepth)
	score := 100 - math.Min(50, (ratio-0.5)*100)

	if ratio > 1.0 {
		warnings = append(warnings, "路径深度超过推荐值，考虑扁平化设计")
	}

	return math.Max(50, score), warnings
}

func (hs *HealthScorer) calculateAlertScore(alertCount int) (float64, []string) {
	warnings := []string{}

	if alertCount == 0 {
		return 100, warnings
	}

	if alertCount <= hs.config.MaxRecommendedAlertCount {
		score := 100 - float64(alertCount)*5
		return math.Max(80, score), warnings
	}

	score := 80 - float64(alertCount-hs.config.MaxRecommendedAlertCount)*2
	warnings = append(warnings, "存在多个预警，请检查预警中心详情")

	return math.Max(50, score), warnings
}

func (hs *HealthScorer) calculateDistributionScore(snapshot *storage.Snapshot) (float64, []string) {
	warnings := []string{}

	if snapshot.TotalNodes == 0 {
		return 100, warnings
	}

	avgChildren := 0
	maxChildren := 0
	for _, node := range snapshot.Nodes {
		if node.ChildCount > maxChildren {
			maxChildren = node.ChildCount
		}
		avgChildren += node.ChildCount
	}
	avgChildren /= snapshot.TotalNodes

	score := 100.0

	if maxChildren > 1000 {
		score -= 30
		warnings = append(warnings, "存在子节点过多的节点，可能导致性能问题")
	} else if maxChildren > 500 {
		score -= 15
	}

	if float64(maxChildren)/float64(avgChildren+1) > 10 {
		score -= 10
		warnings = append(warnings, "子节点分布不均，考虑负载均衡")
	}

	return math.Max(50, score), warnings
}

func (hs *HealthScorer) calculateGrowthScore(snapshot *storage.Snapshot) (float64, []string) {
	warnings := []string{}

	predictions := hs.storage.GetAllPredictions()
	score := 100.0

	if nodePred, ok := predictions["total_nodes"]; ok {
		if nodePred.Trend == "increasing" && math.Abs(nodePred.GrowthRate) > 5 {
			score -= 20
			warnings = append(warnings, "节点数量增长过快，注意容量规划")
		}
	}

	if sizePred, ok := predictions["total_size"]; ok {
		if sizePred.Trend == "increasing" && math.Abs(sizePred.GrowthRate) > 10 {
			score -= 25
			warnings = append(warnings, "数据量增长过快，建议设置数据过期策略")
		}
	}

	return math.Max(50, score), warnings
}

func (hs *HealthScorer) getGrade(score float64) string {
	switch {
	case score >= 90:
		return "A"
	case score >= 80:
		return "B"
	case score >= 70:
		return "C"
	case score >= 60:
		return "D"
	default:
		return "F"
	}
}

func (hs *HealthScorer) CalculateHealthScore() *HealthScore {
	snapshot := hs.storage.GetLatestSnapshot()
	if snapshot == nil {
		return &HealthScore{
			OverallScore:   0,
			Grade:          "N/A",
			LastUpdated:    time.Now(),
			CategoryScores: make(map[string]float64),
			Warnings:       []string{"暂无数据，等待首次采集完成"},
		}
	}

	categoryScores := make(map[string]float64)
	allWarnings := []string{}
	allRecommendations := []string{}

	score1, w1 := hs.calculateNodeCountScore(snapshot.TotalNodes)
	categoryScores["node_count"] = score1
	allWarnings = append(allWarnings, w1...)

	score2, w2 := hs.calculateDataSizeScore(snapshot.TotalSize)
	categoryScores["data_size"] = score2
	allWarnings = append(allWarnings, w2...)

	score3, w3 := hs.calculateDepthScore(snapshot.MaxDepth)
	categoryScores["path_depth"] = score3
	allWarnings = append(allWarnings, w3...)

	score4, w4 := hs.calculateAlertScore(len(snapshot.Alerts))
	categoryScores["alerts"] = score4
	allWarnings = append(allWarnings, w4...)

	score5, w5 := hs.calculateDistributionScore(snapshot)
	categoryScores["distribution"] = score5
	allWarnings = append(allWarnings, w5...)

	score6, w6 := hs.calculateGrowthScore(snapshot)
	categoryScores["growth"] = score6
	allWarnings = append(allWarnings, w6...)

	weights := map[string]float64{
		"node_count":   0.20,
		"data_size":    0.25,
		"path_depth":   0.10,
		"alerts":       0.20,
		"distribution": 0.15,
		"growth":       0.10,
	}

	overallScore := 0.0
	for category, score := range categoryScores {
		overallScore += score * weights[category]
	}

	if overallScore >= 90 {
		allRecommendations = append(allRecommendations, "集群运行状态优秀，继续保持现有运维策略")
	} else if overallScore >= 70 {
		allRecommendations = append(allRecommendations, "集群运行状态良好，建议关注相关预警项")
	} else if overallScore >= 60 {
		allRecommendations = append(allRecommendations, "集群存在一定风险，请查看预警并及时处理")
	} else {
		allRecommendations = append(allRecommendations, "集群存在严重风险，建议立即处理相关问题")
	}

	return &HealthScore{
		OverallScore:    math.Round(overallScore*100) / 100,
		Grade:           hs.getGrade(overallScore),
		LastUpdated:     time.Now(),
		CategoryScores:  categoryScores,
		Recommendations: allRecommendations,
		Warnings:        allWarnings,
	}
}
