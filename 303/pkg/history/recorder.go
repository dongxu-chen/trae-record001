package history

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"autoscaler/internal/types"
	"go.uber.org/zap"
)

type HistoryConfig struct {
	Enabled     bool
	StoragePath string
	MaxRecords  int
}

type HistoryRecorder struct {
	config   HistoryConfig
	records  []*types.ScalingHistoryRecord
	index    map[string]*types.ScalingHistoryRecord
	mu       sync.RWMutex
	logger   *zap.Logger
	filePath string
}

func NewHistoryRecorder(config HistoryConfig, logger *zap.Logger) *HistoryRecorder {
	if config.MaxRecords == 0 {
		config.MaxRecords = 10000
	}

	recorder := &HistoryRecorder{
		config:  config,
		records: make([]*types.ScalingHistoryRecord, 0, config.MaxRecords),
		index:   make(map[string]*types.ScalingHistoryRecord),
		logger:  logger,
	}

	if config.Enabled && config.StoragePath != "" {
		recorder.filePath = filepath.Join(config.StoragePath, "scaling_history.json")
		if err := recorder.load(); err != nil {
			logger.Warn("failed to load history from storage", zap.Error(err))
		}
	}

	return recorder
}

func (h *HistoryRecorder) Record(record *types.ScalingHistoryRecord) error {
	if !h.config.Enabled {
		return nil
	}

	h.mu.Lock()
	defer h.mu.Unlock()

	if _, exists := h.index[record.ID]; exists {
		return fmt.Errorf("record with ID %s already exists", record.ID)
	}

	h.records = append(h.records, record)
	h.index[record.ID] = record

	if len(h.records) > h.config.MaxRecords {
		removed := h.records[0]
		delete(h.index, removed.ID)
		h.records = h.records[1:]
	}

	h.logger.Info("recorded scaling history",
		zap.String("id", record.ID),
		zap.String("result", record.Result),
		zap.String("action_type", string(record.Action.Type)),
		zap.String("direction", string(record.Action.Direction)),
	)

	if h.filePath != "" {
		go func() {
			if err := h.save(); err != nil {
				h.logger.Warn("failed to save history to storage", zap.Error(err))
			}
		}()
	}

	return nil
}

func (h *HistoryRecorder) Query(startTime, endTime time.Time) ([]*types.ScalingHistoryRecord, error) {
	h.mu.RLock()
	defer h.mu.RUnlock()

	var results []*types.ScalingHistoryRecord
	for _, record := range h.records {
		if record.Timestamp.After(startTime) && record.Timestamp.Before(endTime) {
			results = append(results, record)
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Timestamp.Before(results[j].Timestamp)
	})

	return results, nil
}

func (h *HistoryRecorder) GetByID(id string) (*types.ScalingHistoryRecord, error) {
	h.mu.RLock()
	defer h.mu.RUnlock()

	record, exists := h.index[id]
	if !exists {
		return nil, fmt.Errorf("record not found: %s", id)
	}
	return record, nil
}

func (h *HistoryRecorder) Replay(ctx context.Context, config types.HistoryReplayConfig) (*types.ReplayResult, error) {
	h.mu.RLock()
	defer h.mu.RUnlock()

	var records []*types.ScalingHistoryRecord
	if !config.StartTime.IsZero() && !config.EndTime.IsZero() {
		for _, record := range h.records {
			if record.Timestamp.After(config.StartTime) && record.Timestamp.Before(config.EndTime) {
				records = append(records, record)
			}
		}
	} else {
		records = append(records, h.records...)
	}

	sort.Slice(records, func(i, j int) bool {
		return records[i].Timestamp.Before(records[j].Timestamp)
	})

	if len(records) == 0 {
		return &types.ReplayResult{
			TotalSteps:   0,
			StartTime:    time.Now(),
			EndTime:      time.Now(),
			ActionsTaken: 0,
			Recommendations: []string{
				"No scaling history records found for the specified time range",
			},
		}, nil
	}

	result := &types.ReplayResult{
		TotalSteps:   len(records),
		StartTime:    records[0].Timestamp,
		EndTime:      records[len(records)-1].Timestamp,
		ActionsTaken: 0,
		ScaleUps:     0,
		ScaleDowns:   0,
		CostSaved:    0,
		Steps:        make([]types.ReplayStep, 0, len(records)),
	}

	speed := config.Speed
	if speed <= 0 {
		speed = 1.0
	}

	for i, record := range records {
		step := types.ReplayStep{
			Sequence:      i + 1,
			Timestamp:     record.Timestamp,
			Action:        *record,
			ImpactSummary: h.generateImpactSummary(record),
		}

		if config.Visualize && !config.MetricsOnly {
			step.MetricChart = h.generateMetricChart(record)
			step.DecisionTree = h.generateDecisionTree(record)
		}

		result.Steps = append(result.Steps, step)

		if record.Action.Direction == types.ScaleUp {
			result.ScaleUps++
			result.ActionsTaken++
		} else if record.Action.Direction == types.ScaleDown {
			result.ScaleDowns++
			result.ActionsTaken++
		}

		if record.CostChange < 0 {
			result.CostSaved += -record.CostChange
		}

		result.AvgResponseTime += record.Duration

		if ctx.Err() != nil {
			return nil, ctx.Err()
		}
	}

	if result.ActionsTaken > 0 {
		result.AvgResponseTime = result.AvgResponseTime / time.Duration(result.ActionsTaken)
	}

	result.CostSaved *= 24 * 30

	result.Recommendations = h.generateReplayRecommendations(result)

	h.logger.Info("history replay completed",
		zap.Int("total_steps", result.TotalSteps),
		zap.Int("actions_taken", result.ActionsTaken),
		zap.Int("scale_ups", result.ScaleUps),
		zap.Int("scale_downs", result.ScaleDowns),
		zap.Float64("estimated_monthly_savings", result.CostSaved),
	)

	return result, nil
}

func (h *HistoryRecorder) GenerateVisualReport(ctx context.Context, config types.HistoryReplayConfig) (string, error) {
	replayResult, err := h.Replay(ctx, config)
	if err != nil {
		return "", err
	}

	var report strings.Builder

	report.WriteString("# 弹性伸缩历史分析报告\n\n")
	report.WriteString(fmt.Sprintf("**时间范围**: %s ~ %s\n\n",
		replayResult.StartTime.Format("2006-01-02 15:04:05"),
		replayResult.EndTime.Format("2006-01-02 15:04:05"),
	))
	report.WriteString("---\n\n")
	report.WriteString("## 执行概览\n\n")
	report.WriteString(fmt.Sprintf("| 指标 | 数值 |\n"))
	report.WriteString("|------|------|\n")
	report.WriteString(fmt.Sprintf("| 总步骤数 | %d |\n", replayResult.TotalSteps))
	report.WriteString(fmt.Sprintf("| 执行的伸缩动作 | %d |\n", replayResult.ActionsTaken))
	report.WriteString(fmt.Sprintf("| 扩容次数 | %d |\n", replayResult.ScaleUps))
	report.WriteString(fmt.Sprintf("| 缩容次数 | %d |\n", replayResult.ScaleDowns))
	report.WriteString(fmt.Sprintf("| 预估月节省成本 | $%.2f |\n", replayResult.CostSaved))
	report.WriteString(fmt.Sprintf("| 平均响应时间 | %v |\n\n", replayResult.AvgResponseTime))

	report.WriteString("## 伸缩决策时序图\n\n")
	report.WriteString("```\n")
	report.WriteString("时间轴: ")

	step := len(replayResult.Steps) / 50
	if step < 1 {
		step = 1
	}

	for i := 0; i < len(replayResult.Steps); i += step {
		rec := replayResult.Steps[i]
		switch rec.Action.Action.Direction {
		case types.ScaleUp:
			report.WriteString("↑")
		case types.ScaleDown:
			report.WriteString("↓")
		default:
			report.WriteString("-")
		}
	}
	report.WriteString("\n\n")
	report.WriteString("图例: ↑=扩容  ↓=缩容  -=无操作\n")
	report.WriteString("```\n\n")

	if len(replayResult.Recommendations) > 0 {
		report.WriteString("## 优化建议\n\n")
		for i, rec := range replayResult.Recommendations {
			report.WriteString(fmt.Sprintf("%d. %s\n", i+1, rec))
		}
		report.WriteString("\n")
	}

	report.WriteString("## 详细事件回放\n\n")

	displayCount := 10
	if len(replayResult.Steps) < displayCount {
		displayCount = len(replayResult.Steps)
	}

	for i := 0; i < displayCount; i++ {
		step := replayResult.Steps[i]
		report.WriteString(fmt.Sprintf("### 步骤 %d - %s\n\n",
			step.Sequence,
			step.Timestamp.Format("2006-01-02 15:04:05"),
		))
		report.WriteString(fmt.Sprintf("- **动作**: %s %s\n",
			step.Action.Action.Type, step.Action.Action.Direction))
		report.WriteString(fmt.Sprintf("- **原因**: %s\n", step.Action.Action.Reason))
		report.WriteString(fmt.Sprintf("- **结果**: %s\n", step.Action.Result))
		report.WriteString(fmt.Sprintf("- **实例数变化**: %d\n", step.Action.InstanceCount))
		report.WriteString(fmt.Sprintf("- **成本变化**: $%.4f/小时\n\n", step.Action.CostChange))
	}

	if len(replayResult.Steps) > displayCount {
		report.WriteString(fmt.Sprintf("\n... 还有 %d 条记录，使用完整模式查看\n",
			len(replayResult.Steps)-displayCount))
	}

	return report.String(), nil
}

func (h *HistoryRecorder) Close() error {
	if !h.config.Enabled || h.filePath == "" {
		return nil
	}

	h.mu.Lock()
	defer h.mu.Unlock()

	return h.save()
}

func (h *HistoryRecorder) load() error {
	if h.filePath == "" {
		return nil
	}

	data, err := os.ReadFile(h.filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	var records []*types.ScalingHistoryRecord
	if err := json.Unmarshal(data, &records); err != nil {
		return fmt.Errorf("failed to parse history file: %w", err)
	}

	h.records = records
	h.index = make(map[string]*types.ScalingHistoryRecord)
	for _, rec := range records {
		h.index[rec.ID] = rec
	}

	h.logger.Info("loaded scaling history from storage",
		zap.Int("record_count", len(records)),
	)

	return nil
}

func (h *HistoryRecorder) save() error {
	if h.filePath == "" {
		return nil
	}

	dir := filepath.Dir(h.filePath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to create storage directory: %w", err)
	}

	data, err := json.MarshalIndent(h.records, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal history records: %w", err)
	}

	if err := os.WriteFile(h.filePath, data, 0644); err != nil {
		return fmt.Errorf("failed to write history file: %w", err)
	}

	return nil
}

func (h *HistoryRecorder) generateImpactSummary(record *types.ScalingHistoryRecord) string {
	direction := "维持"
	if record.Action.Direction == types.ScaleUp {
		direction = "增加"
	} else if record.Action.Direction == types.ScaleDown {
		direction = "减少"
	}

	costStr := ""
	if record.CostChange != 0 {
		if record.CostChange > 0 {
			costStr = fmt.Sprintf("，成本增加 $%.4f/小时", record.CostChange)
		} else {
			costStr = fmt.Sprintf("，成本减少 $%.4f/小时", -record.CostChange)
		}
	}

	return fmt.Sprintf("%s %d 台 %s 实例%s，执行结果: %s",
		direction, record.Action.Step,
		record.Action.ChargeType,
		costStr, record.Result,
	)
}

func (h *HistoryRecorder) generateMetricChart(record *types.ScalingHistoryRecord) string {
	if len(record.MetricSnapshot) == 0 {
		return "无指标数据"
	}

	metricOrder := []types.MetricType{
		types.MetricCPU,
		types.MetricMemory,
		types.MetricNetwork,
	}

	var chart strings.Builder
	chart.WriteString("\n  指标值:\n")

	for _, mt := range metricOrder {
		if m, ok := record.MetricSnapshot[mt]; ok {
			current := m.Current
			target := 0.0
			if mt == types.MetricCPU {
				target = 70.0
			} else if mt == types.MetricMemory {
				target = 75.0
			}

			barLen := int(current / 5)
			if barLen > 20 {
				barLen = 20
			}
			bar := strings.Repeat("█", barLen) + strings.Repeat("░", 20-barLen)

			marker := ""
			if current > target+10 {
				marker = " ↑"
			} else if current < target-10 {
				marker = " ↓"
			}

			chart.WriteString(fmt.Sprintf("    %-7s [%s] %5.1f%%%s (目标: %.0f%%)\n",
				mt, bar, current, marker, target))
		}
	}

	return chart.String()
}

func (h *HistoryRecorder) generateDecisionTree(record *types.ScalingHistoryRecord) string {
	if record.Action.Direction == types.NoScale {
		return "└─ 指标在目标范围内 → 无需伸缩"
	}

	var tree strings.Builder
	tree.WriteString(fmt.Sprintf("├─ 触发指标: %s\n", record.Action.Reason))
	tree.WriteString(fmt.Sprintf("├─ 服务等级: %s\n", record.ServiceLevel))
	tree.WriteString(fmt.Sprintf("├─ 动作类型: %s\n", record.Action.Type))
	tree.WriteString(fmt.Sprintf("├─ 伸缩方向: %s\n", record.Action.Direction))
	tree.WriteString(fmt.Sprintf("├─ 步长: %d\n", record.Action.Step))
	tree.WriteString(fmt.Sprintf("├─ 计费类型: %s\n", record.Action.ChargeType))
	tree.WriteString(fmt.Sprintf("└─ 结果: %s\n", record.Result))

	return tree.String()
}

func (h *HistoryRecorder) generateReplayRecommendations(result *types.ReplayResult) []string {
	var recs []string

	totalHours := result.EndTime.Sub(result.StartTime).Hours()
	if totalHours < 1 {
		totalHours = 1
	}
	actionFreq := float64(result.ActionsTaken) / (totalHours / 24)

	if actionFreq > 10 {
		recs = append(recs,
			fmt.Sprintf("伸缩频率过高 (%.1f次/天)，建议增加冷却时间或调整目标阈值的容差范围", actionFreq))
	}

	if result.ScaleUps > 0 && result.ScaleDowns > 0 {
		ratio := float64(result.ScaleUps) / float64(result.ScaleDowns)
		if ratio > 3.0 || ratio < 0.33 {
			recs = append(recs,
				"扩容和缩容次数严重不平衡，建议检查阈值设置是否合理")
		}
	}

	if result.CostSaved > 0 {
		recs = append(recs,
			fmt.Sprintf("历史缩容操作已节省约 $%.2f/月，建议继续优化实例规格和计费类型", result.CostSaved))
	}

	if len(result.Steps) > 0 {
		noActionCount := 0
		for _, step := range result.Steps {
			if step.Action.Action.Direction == types.NoScale {
				noActionCount++
			}
		}
		if float64(noActionCount)/float64(len(result.Steps)) > 0.8 {
			recs = append(recs,
				"大部分时间无需伸缩，当前策略配置较保守，可考虑降低目标阈值以提高资源利用率")
		}
	}

	if len(recs) == 0 {
		recs = append(recs, "伸缩策略运行良好，各项指标正常")
	}

	return recs
}
