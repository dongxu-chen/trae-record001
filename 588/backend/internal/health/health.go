package health

import (
	"fmt"
	"math"
	"time"
	"zk-inspector/internal/storage"
	"zk-inspector/internal/types"
)

type HealthEvaluator struct{}

func NewHealthEvaluator() *HealthEvaluator {
	return &HealthEvaluator{}
}

func (he *HealthEvaluator) Evaluate(
	snapshot *storage.Snapshot,
	heatStats map[string]interface{},
) *types.HealthScore {
	score := &types.HealthScore{
		Timestamp:   time.Now(),
		Dimensions:  []types.HealthDimension{},
		Suggestions: []string{},
	}
	if snapshot == nil {
		score.TotalScore = 0
		score.Grade = "N/A"
		return score
	}

	dimensions := []types.HealthDimension{}
	dimensions = append(dimensions, he.evaluateNodeCount(snapshot))
	dimensions = append(dimensions, he.evaluateDataSize(snapshot))
	dimensions = append(dimensions, he.evaluatePathDepth(snapshot))
	dimensions = append(dimensions, he.evaluateAlerts(snapshot))
	dimensions = append(dimensions, he.evaluateEphemeralNodes(snapshot))
	dimensions = append(dimensions, he.evaluateHeatDistribution(heatStats))
	dimensions = append(dimensions, he.evaluateDataDistribution(snapshot))

	totalWeight := 0.0
	weightedSum := 0.0
	for _, dim := range dimensions {
		totalWeight += dim.Weight
		weightedSum += dim.Score * dim.Weight
	}
	if totalWeight > 0 {
		score.TotalScore = weightedSum / totalWeight
	}
	score.Grade = he.scoreToGrade(score.TotalScore)
	score.Dimensions = dimensions
	score.Suggestions = he.generateSuggestions(dimensions)
	return score
}

func (he *HealthEvaluator) evaluateNodeCount(s *storage.Snapshot) types.HealthDimension {
	c := s.TotalNodes
	var sc float64
	var status, desc string
	switch {
	case c < 1000:
		sc, status, desc = 100, "excellent", fmt.Sprintf("节点数量 %d，处于健康范围", c)
	case c < 5000:
		sc, status, desc = 80, "good", fmt.Sprintf("节点数量 %d，可以接受", c)
	case c < 10000:
		sc, status, desc = 60, "warning", fmt.Sprintf("节点数量 %d，接近上限", c)
	case c < 50000:
		sc, status, desc = 40, "poor", fmt.Sprintf("节点数量 %d，可能影响性能", c)
	default:
		sc, status, desc = 20, "critical", fmt.Sprintf("节点数量 %d，严重影响性能", c)
	}
	return types.HealthDimension{Name: "node_count", Score: sc, Weight: 0.2, Description: desc, Status: status}
}

func (he *HealthEvaluator) evaluateDataSize(s *storage.Snapshot) types.HealthDimension {
	sz := s.TotalSize
	var sc float64
	var status, desc string
	switch {
	case sz < 10*1024*1024:
		sc, status, desc = 100, "excellent", fmt.Sprintf("总数据量 %s，处于健康范围", formatBytes(sz))
	case sz < 50*1024*1024:
		sc, status, desc = 80, "good", fmt.Sprintf("总数据量 %s，可以接受", formatBytes(sz))
	case sz < 100*1024*1024:
		sc, status, desc = 60, "warning", fmt.Sprintf("总数据量 %s，建议关注", formatBytes(sz))
	case sz < 500*1024*1024:
		sc, status, desc = 40, "poor", fmt.Sprintf("总数据量 %s，建议优化", formatBytes(sz))
	default:
		sc, status, desc = 20, "critical", fmt.Sprintf("总数据量 %s，需要立即处理", formatBytes(sz))
	}
	return types.HealthDimension{Name: "data_size", Score: sc, Weight: 0.2, Description: desc, Status: status}
}

func (he *HealthEvaluator) evaluatePathDepth(s *storage.Snapshot) types.HealthDimension {
	d := s.MaxDepth
	var sc float64
	var status, desc string
	switch {
	case d <= 5:
		sc, status, desc = 100, "excellent", fmt.Sprintf("最大深度 %d，结构良好", d)
	case d <= 8:
		sc, status, desc = 80, "good", fmt.Sprintf("最大深度 %d，可以接受", d)
	case d <= 10:
		sc, status, desc = 60, "warning", fmt.Sprintf("最大深度 %d，偏深", d)
	case d <= 15:
		sc, status, desc = 40, "poor", fmt.Sprintf("最大深度 %d，建议扁平化", d)
	default:
		sc, status, desc = 20, "critical", fmt.Sprintf("最大深度 %d，严重影响查询性能", d)
	}
	return types.HealthDimension{Name: "path_depth", Score: sc, Weight: 0.1, Description: desc, Status: status}
}

func (he *HealthEvaluator) evaluateAlerts(s *storage.Snapshot) types.HealthDimension {
	a := len(s.Alerts)
	var sc float64
	var status, desc string
	switch {
	case a == 0:
		sc, status, desc = 100, "excellent", "无预警信息"
	case a < 5:
		sc, status, desc = 80, "good", fmt.Sprintf("%d 条预警，可关注", a)
	case a < 20:
		sc, status, desc = 60, "warning", fmt.Sprintf("%d 条预警，建议处理", a)
	case a < 50:
		sc, status, desc = 40, "poor", fmt.Sprintf("%d 条预警，需要重视", a)
	default:
		sc, status, desc = 20, "critical", fmt.Sprintf("%d 条预警，急需处理", a)
	}
	return types.HealthDimension{Name: "alert_count", Score: sc, Weight: 0.15, Description: desc, Status: status}
}

func (he *HealthEvaluator) evaluateEphemeralNodes(s *storage.Snapshot) types.HealthDimension {
	ephemeral := 0
	for _, node := range s.Nodes {
		if node.Ephemeral {
			ephemeral++
		}
	}
	ratio := 0.0
	if s.TotalNodes > 0 {
		ratio = float64(ephemeral) / float64(s.TotalNodes) * 100
	}
	var sc float64
	var status, desc string
	switch {
	case ratio < 10:
		sc, status, desc = 100, "excellent", fmt.Sprintf("临时节点占比 %.1f%%，健康", ratio)
	case ratio < 30:
		sc, status, desc = 70, "good", fmt.Sprintf("临时节点占比 %.1f%%，可接受", ratio)
	case ratio < 50:
		sc, status, desc = 50, "warning", fmt.Sprintf("临时节点占比 %.1f%%，偏高", ratio)
	default:
		sc, status, desc = 30, "poor", fmt.Sprintf("临时节点占比 %.1f%%，过高，建议优化", ratio)
	}
	return types.HealthDimension{Name: "ephemeral_ratio", Score: sc, Weight: 0.1, Description: desc, Status: status}
}

func (he *HealthEvaluator) evaluateHeatDistribution(heatStats map[string]interface{}) types.HealthDimension {
	if heatStats == nil {
		return types.HealthDimension{Name: "heat_distribution", Score: 70, Weight: 0.15, Description: "热度数据未就绪", Status: "unknown"}
	}
	total, _ := heatStats["total"].(int)
	cold, _ := heatStats["cold"].(int)
	if total == 0 {
		return types.HealthDimension{Name: "heat_distribution", Score: 70, Weight: 0.15, Description: "无热度数据", Status: "unknown"}
	}
	coldRatio := float64(cold) / float64(total) * 100
	var sc float64
	var status, desc string
	switch {
	case coldRatio < 10:
		sc, status, desc = 100, "excellent", fmt.Sprintf("冷数据占比 %.1f%%，数据活跃度高", coldRatio)
	case coldRatio < 30:
		sc, status, desc = 80, "good", fmt.Sprintf("冷数据占比 %.1f%%，可接受", coldRatio)
	case coldRatio < 50:
		sc, status, desc = 60, "warning", fmt.Sprintf("冷数据占比 %.1f%%，建议迁移冷数据", coldRatio)
	default:
		sc, status, desc = 40, "poor", fmt.Sprintf("冷数据占比 %.1f%%，大量冷数据占用资源", coldRatio)
	}
	return types.HealthDimension{Name: "heat_distribution", Score: sc, Weight: 0.15, Description: desc, Status: status}
}

func (he *HealthEvaluator) evaluateDataDistribution(s *storage.Snapshot) types.HealthDimension {
	if len(s.Nodes) < 2 {
		return types.HealthDimension{Name: "data_distribution", Score: 80, Weight: 0.1, Description: "节点数量不足", Status: "unknown"}
	}
	sizes := make([]float64, 0, len(s.Nodes))
	for _, node := range s.Nodes {
		sizes = append(sizes, float64(node.DataSize))
	}
	mean := 0.0
	for _, v := range sizes {
		mean += v
	}
	mean /= float64(len(sizes))
	variance := 0.0
	for _, v := range sizes {
		variance += (v - mean) * (v - mean)
	}
	variance /= float64(len(sizes))
	cv := math.Sqrt(variance)
	if mean > 0 {
		cv = cv / mean
	}
	var sc float64
	var status, desc string
	switch {
	case cv < 0.5:
		sc, status, desc = 100, "excellent", "数据分布均匀"
	case cv < 1.0:
		sc, status, desc = 80, "good", "数据分布较均匀"
	case cv < 2.0:
		sc, status, desc = 60, "warning", "数据分布不均匀，存在热点"
	default:
		sc, status, desc = 40, "poor", "数据分布极不均匀，存在严重热点"
	}
	return types.HealthDimension{Name: "data_distribution", Score: sc, Weight: 0.1, Description: desc, Status: status}
}

func (he *HealthEvaluator) scoreToGrade(score float64) string {
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

func (he *HealthEvaluator) generateSuggestions(dims []types.HealthDimension) []string {
	suggestions := []string{}
	suggestionMap := map[string]string{
		"node_count":        "节点数量过多，建议合并小节点或归档历史节点",
		"data_size":         "数据量过大，建议压缩数据或迁移至外部存储",
		"path_depth":        "路径过深，建议重构命名空间，扁平化层级",
		"alert_count":       "预警数量过多，请优先处理严重级别的预警",
		"ephemeral_ratio":   "临时节点占比过高，检查会话管理和清理机制",
		"heat_distribution": "冷数据占比过高，建议将冷数据迁移至外部存储系统",
		"data_distribution": "数据分布不均匀，建议对热点节点进行拆分或负载均衡",
	}
	for _, dim := range dims {
		if dim.Status == "poor" || dim.Status == "critical" {
			if s, ok := suggestionMap[dim.Name]; ok {
				suggestions = append(suggestions, s)
			}
		}
	}
	return suggestions
}

func formatBytes(bytes int64) string {
	if bytes == 0 {
		return "0 B"
	}
	k := float64(1024)
	sizes := []string{"B", "KB", "MB", "GB"}
	i := 0
	fb := float64(bytes)
	for fb >= k && i < len(sizes)-1 {
		fb /= k
		i++
	}
	return fmt.Sprintf("%.1f %s", fb, sizes[i])
}
