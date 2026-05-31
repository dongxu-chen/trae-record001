package predictor

import (
	"math"
	"time"
	"zk-inspector/internal/storage"

	"github.com/montanaflynn/stats"
	"gonum.org/v1/gonum/stat"
)

type TimeSeriesPredictor struct {
}

type DecomposedSeries struct {
	Trend      []float64
	Seasonal   []float64
	Residual   []float64
	Period     int
	SeasonType string
}

func NewTimeSeriesPredictor() *TimeSeriesPredictor {
	return &TimeSeriesPredictor{}
}

func (p *TimeSeriesPredictor) movingAverage(data []float64, windowSize int) []float64 {
	n := len(data)
	result := make([]float64, n)
	halfWindow := windowSize / 2

	for i := 0; i < n; i++ {
		start := max(0, i-halfWindow)
		end := min(n-1, i+halfWindow)
		sum := 0.0
		count := 0
		for j := start; j <= end; j++ {
			sum += data[j]
			count++
		}
		result[i] = sum / float64(count)
	}
	return result
}

func (p *TimeSeriesPredictor) detectPeriod(data []float64) (int, string) {
	n := len(data)
	if n < 24 {
		return 1, "none"
	}

	bestPeriod := 1
	bestScore := math.Inf(-1)

	periods := []struct {
		period int
		name   string
	}{
		{24, "daily"},
		{168, "weekly"},
		{12, "half_daily"},
		{6, "quarter_daily"},
	}

	for _, p := range periods {
		if n < p.period*2 {
			continue
		}

		seasonal := make([]float64, n)
		for i := 0; i < n; i++ {
			idx := i % p.period
			count := 0
			sum := 0.0
			for j := idx; j < n; j += p.period {
				sum += data[j]
				count++
			}
			seasonal[i] = sum / float64(count)
		}

		trend := p.movingAverage(data, p.period)
		residualVariance := 0.0
		for i := 0; i < n; i++ {
			residual := data[i] - trend[i] - seasonal[i] + data[i]/2
			residualVariance += residual * residual
		}

		score := -residualVariance
		if score > bestScore {
			bestScore = score
			bestPeriod = p.period
		}
	}

	periodName := "none"
	for _, p := range periods {
		if p.period == bestPeriod {
			periodName = p.name
			break
		}
	}

	return bestPeriod, periodName
}

func (p *TimeSeriesPredictor) decomposeSTL(data []float64) *DecomposedSeries {
	n := len(data)
	if n < 2 {
		return &DecomposedSeries{
			Trend:      data,
			Seasonal:   make([]float64, n),
			Residual:   make([]float64, n),
			Period:     1,
			SeasonType: "none",
		}
	}

	period, seasonType := p.detectPeriod(data)

	trendWindow := max(period*2+1, 7)
	trend := p.movingAverage(data, trendWindow)

	seasonal := make([]float64, n)
	if period > 1 && n >= period*2 {
		for phase := 0; phase < period; phase++ {
			phaseValues := []float64{}
			for i := phase; i < n; i += period {
				phaseValues = append(phaseValues, data[i]-trend[i])
			}
			mean, _ := stats.Mean(phaseValues)
			for i := phase; i < n; i += period {
				seasonal[i] = mean
			}
		}
	}

	residual := make([]float64, n)
	for i := 0; i < n; i++ {
		residual[i] = data[i] - trend[i] - seasonal[i]
	}

	return &DecomposedSeries{
		Trend:      trend,
		Seasonal:   seasonal,
		Residual:   residual,
		Period:     period,
		SeasonType: seasonType,
	}
}

func (p *TimeSeriesPredictor) predictWithDecomposition(
	data []storage.DataPoint,
	steps int,
) (*storage.Prediction, error) {
	if len(data) < 2 {
		return &storage.Prediction{
			HistoricalData: data,
			PredictedData:  []storage.DataPoint{},
			GrowthRate:     0,
			Trend:          "insufficient_data",
		}, nil
	}

	values := make([]float64, len(data))
	for i, dp := range data {
		values[i] = dp.Value
	}

	decomposed := p.decomposeSTL(values)

	xs := make([]float64, len(data))
	for i := range data {
		xs[i] = float64(i)
	}

	trendAlpha, trendBeta := stat.LinearRegression(xs, decomposed.Trend, nil, false)

	lastTime := data[len(data)-1].Timestamp
	interval := time.Minute
	if len(data) > 1 {
		interval = data[1].Timestamp.Sub(data[0].Timestamp)
	}

	predicted := make([]storage.DataPoint, steps)
	for i := 0; i < steps; i++ {
		x := float64(len(data) + i)
		trendPred := trendAlpha + trendBeta*x

		seasonalPred := 0.0
		if decomposed.Period > 1 {
			phase := (len(data) + i) % decomposed.Period
			if phase < len(decomposed.Seasonal) {
				seasonalPred = decomposed.Seasonal[phase]
			}
		}

		predicted[i] = storage.DataPoint{
			Timestamp: lastTime.Add(time.Duration(i+1) * interval),
			Value:     trendPred + seasonalPred,
		}
	}

	steps7D := int(7 * 24 * time.Hour / interval)
	x7d := float64(len(data) + steps7D)
	trend7d := trendAlpha + trendBeta*x7d
	seasonal7d := 0.0
	if decomposed.Period > 1 {
		phase7d := (len(data) + steps7D) % decomposed.Period
		if phase7d < len(decomposed.Seasonal) {
			seasonal7d = decomposed.Seasonal[phase7d]
		}
	}
	predictedValue7D := trend7d + seasonal7d

	growthRate := trendBeta
	mean, _ := stats.Mean(values)
	if mean != 0 {
		growthRate = (trendBeta / mean) * 100
	}

	var trendStr string
	switch {
	case math.Abs(growthRate) < 0.01:
		trendStr = "stable"
	case growthRate > 0:
		trendStr = "increasing"
	default:
		trendStr = "decreasing"
	}

	return &storage.Prediction{
		HistoricalData:   data,
		PredictedData:    predicted,
		GrowthRate:       growthRate,
		PredictedValue7D: predictedValue7D,
		Trend:            trendStr,
		SeasonType:       decomposed.SeasonType,
	}, nil
}

func (p *TimeSeriesPredictor) Predict(data []storage.DataPoint, steps int) (*storage.Prediction, error) {
	return p.predictWithDecomposition(data, steps)
}

func (p *TimeSeriesPredictor) GenerateOptimizationRecommendations(
	snapshot *storage.Snapshot,
) []map[string]interface{} {
	recommendations := []map[string]interface{}{}

	if snapshot == nil {
		return recommendations
	}

	if snapshot.TotalSize > 100*1024*1024 {
		recommendations = append(recommendations, map[string]interface{}{
			"category":  "data_size",
			"severity":  "high",
			"title":     "总数据量过大",
			"message":   "总数据量超过100MB，影响ZooKeeper性能",
			"action":    "实施数据压缩或归档",
			"solutions": []string{"对JSON/XML等文本数据使用gzip压缩存储", "将大体积数据迁移到外部存储系统（如HBase、Cassandra）", "ZooKeeper仅存储数据引用和元数据", "设置数据过期策略，定期清理历史数据"},
			"scripts":   []string{"使用zkCli.sh的get/delete命令手动清理", "编写定时脚本扫描并删除过期节点", "使用Curator Framework的节点清理工具"},
		})
	}

	if snapshot.TotalNodes > 10000 {
		recommendations = append(recommendations, map[string]interface{}{
			"category":  "node_count",
			"severity":  "medium",
			"title":     "节点数量过多",
			"message":   "超过10000个节点可能导致watch压力过大",
			"action":    "节点合并与批量优化",
			"solutions": []string{"将多个相关子节点合并为单节点多字段存储", "使用批量API（multi操作）减少往返次数", "实现节点池机制复用节点", "调整jute.maxbuffer配置"},
			"scripts":   []string{"编写脚本批量合并小节点", "使用分布式锁控制节点创建速率"},
		})
	}

	if snapshot.MaxDepth > 10 {
		recommendations = append(recommendations, map[string]interface{}{
			"category":  "path_depth",
			"severity":  "low",
			"title":     "路径层级过深",
			"message":   "最深路径超过10层，增加查询开销",
			"action":    "路径扁平化设计",
			"solutions": []string{"重构命名空间，减少层级", "使用编码节点名替代深层路径", "将部分层级信息编码到节点名中"},
			"scripts":   []string{"编写路径迁移脚本", "使用事务原子性迁移节点数据"},
		})
	}

	largeEphemeral := 0
	ephemeralPaths := []string{}
	for path, pathStat := range snapshot.PathStats {
		if pathStat.EphemeralCount > 500 {
			largeEphemeral++
			ephemeralPaths = append(ephemeralPaths, path)
		}
	}
	if largeEphemeral > 0 {
		recommendations = append(recommendations, map[string]interface{}{
			"category":      "ephemeral",
			"severity":      "medium",
			"title":         "临时节点过多",
			"message":       "大量临时节点消耗内存和会话资源",
			"action":        "临时节点清理优化",
			"solutions":     []string{"检查会话超时设置是否合理", "实现客户端优雅关闭确保临时节点删除", "使用节点分组减少数量", "考虑使用Persistent节点+TTL替代"},
			"scripts":       []string{"监控并统计临时节点生命周期", "编写检测孤儿临时节点的脚本"},
			"affectedPaths": ephemeralPaths,
		})
	}

	largeNodes := []string{}
	for nodePath, node := range snapshot.Nodes {
		if node.DataSize > 512*1024 {
			largeNodes = append(largeNodes, nodePath)
		}
	}
	if len(largeNodes) > 0 {
		recommendations = append(recommendations, map[string]interface{}{
			"category":      "large_nodes",
			"severity":      "high",
			"title":         "存在大节点",
			"message":       "部分节点数据超过512KB",
			"action":        "大节点拆分处理",
			"solutions":     []string{"将大数据拆分为多个子节点", "使用外部存储存储大对象数据", "实现数据分片存储策略"},
			"scripts":       []string{"自动检测并告警大节点", "数据拆分迁移脚本"},
			"affectedNodes": largeNodes,
		})
	}

	highChildCount := []string{}
	for nodePath, node := range snapshot.Nodes {
		if node.ChildCount > 200 {
			highChildCount = append(highChildCount, nodePath)
		}
	}
	if len(highChildCount) > 0 {
		recommendations = append(recommendations, map[string]interface{}{
			"category":      "many_children",
			"severity":      "medium",
			"title":         "节点子节点过多",
			"message":       "部分节点子节点数超过200",
			"action":        "子节点分片优化",
			"solutions":     []string{"使用哈希分片将子节点分散到多个父节点", "实现分页加载子节点逻辑", "避免对大子节点列表设置watch"},
			"affectedNodes": highChildCount,
		})
	}

	return recommendations
}

func (p *TimeSeriesPredictor) StartPredictionJob(
	storage *storage.MemoryStorage,
	interval time.Duration,
) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for range ticker.C {
		p.runPredictions(storage)
	}
}

func (p *TimeSeriesPredictor) runPredictions(storage *storage.MemoryStorage) {
	metrics := []string{"total_nodes", "total_size", "max_depth"}

	for _, metric := range metrics {
		data := storage.GetTimeSeries(metric, 7*24*time.Hour)
		prediction, err := p.Predict(data, 24)
		if err != nil {
			continue
		}
		prediction.Metric = metric
		storage.SetPrediction(metric, prediction)
	}
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
