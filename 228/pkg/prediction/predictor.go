package prediction

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"docker-build-accelerator/pkg/analysis"
	"docker-build-accelerator/pkg/parser"
)

type BuildPrediction struct {
	OriginalDockerfile string
	ModifiedDockerfile string
	BuildTimeSavedMs   int64
	BuildTimeAddedMs   int64
	NetTimeChangeMs    int64
	SizeSavedBytes     int64
	SizeAddedBytes     int64
	NetSizeChangeBytes int64
	AffectedLayers     []*LayerChange
	CacheHitRateChange float64
	Recommendations    []string
}

type LayerChange struct {
	LineNumber      int
	CommandType     parser.CommandType
	OriginalCommand string
	ModifiedCommand string
	ChangeType      ChangeType
	TimeImpactMs    int64
	SizeImpactBytes int64
	Reason          string
}

type ChangeType string

const (
	ChangeAdded    ChangeType = "added"
	ChangeRemoved  ChangeType = "removed"
	ChangeModified ChangeType = "modified"
	ChangeReordered ChangeType = "reordered"
)

type CommandPerformanceDB struct {
	CommandStats map[string]*CommandStats `json:"command_stats"`
	mu           sync.RWMutex
}

type CommandStats struct {
	CommandType    string  `json:"command_type"`
	AverageTimeMs  int64   `json:"average_time_ms"`
	AverageSize    int64   `json:"average_size_bytes"`
	HitCount       int     `json:"hit_count"`
	Variance       float64 `json:"variance"`
}

type BuildPredictor struct {
	historyDB     *analysis.BuildHistoryDB
	performanceDB *CommandPerformanceDB
	parser        *parser.DockerfileParser
}

func NewBuildPredictor(historyPath string) (*BuildPredictor, error) {
	historyDB, err := analysis.LoadBuildHistory(historyPath)
	if err != nil {
		return nil, err
	}

	perfDB := &CommandPerformanceDB{
		CommandStats: make(map[string]*CommandStats),
	}
	perfDB.calculateFromHistory(historyDB)

	return &BuildPredictor{
		historyDB:     historyDB,
		performanceDB: perfDB,
		parser:        parser.NewDockerfileParser(),
	}, nil
}

func (perf *CommandPerformanceDB) calculateFromHistory(history *analysis.BuildHistoryDB) {
	typeStats := make(map[string][]analysis.LayerRecord)

	for _, record := range history.Records {
		for _, layer := range record.Layers {
			typeStats[layer.CommandType] = append(typeStats[layer.CommandType], layer)
		}
	}

	for cmdType, layers := range typeStats {
		if len(layers) == 0 {
			continue
		}

		var totalTime int64
		var totalSize int64
		for _, layer := range layers {
			totalTime += layer.DurationMs
			totalSize += layer.SizeBytes
		}

		avgTime := totalTime / int64(len(layers))
		avgSize := totalSize / int64(len(layers))

		var variance float64
		for _, layer := range layers {
			diff := float64(layer.DurationMs) - float64(avgTime)
			variance += diff * diff
		}
		variance /= float64(len(layers))

		perf.CommandStats[cmdType] = &CommandStats{
			CommandType:   cmdType,
			AverageTimeMs: avgTime,
			AverageSize:   avgSize,
			HitCount:      len(layers),
			Variance:      variance,
		}
	}
}

func (bp *BuildPredictor) PredictChanges(originalPath, modifiedPath string) (*BuildPrediction, error) {
	originalContent, err := os.ReadFile(originalPath)
	if err != nil {
		return nil, err
	}

	modifiedContent, err := os.ReadFile(modifiedPath)
	if err != nil {
		return nil, err
	}

	return bp.PredictChangesFromContent(string(originalContent), string(modifiedContent))
}

func (bp *BuildPredictor) PredictChangesFromContent(original, modified string) (*BuildPrediction, error) {
	parsedOriginal, err := bp.parser.ParseContent(original)
	if err != nil {
		return nil, err
	}

	parsedModified, err := bp.parser.ParseContent(modified)
	if err != nil {
		return nil, err
	}

	prediction := &BuildPrediction{
		OriginalDockerfile: original,
		ModifiedDockerfile: modified,
		AffectedLayers:     make([]*LayerChange, 0),
	}

	bp.analyzeLayerChanges(parsedOriginal, parsedModified, prediction)
	bp.generateRecommendations(prediction)

	return prediction, nil
}

func (bp *BuildPredictor) analyzeLayerChanges(original, modified *parser.ParsedDockerfile, prediction *BuildPrediction) {
	origCommands := bp.flattenCommands(original)
	modCommands := bp.flattenCommands(modified)

	origMap := make(map[int]*parser.DockerCommand)
	for i, cmd := range origCommands {
		origMap[i] = cmd
	}

	modMap := make(map[int]*parser.DockerCommand)
	for i, cmd := range modCommands {
		modMap[i] = cmd
	}

	longestSeq := bp.longestCommonSubsequence(origCommands, modCommands)

	origIdx, modIdx := 0, 0
	seqIdx := 0

	for origIdx < len(origCommands) || modIdx < len(modCommands) {
		if seqIdx < len(longestSeq) && 
		   origIdx < len(origCommands) && 
		   modIdx < len(modCommands) &&
		   origCommands[origIdx].Original == longestSeq[seqIdx].Original &&
		   modCommands[modIdx].Original == longestSeq[seqIdx].Original {
			origIdx++
			modIdx++
			seqIdx++
			continue
		}

		if origIdx < len(origCommands) && modIdx < len(modCommands) &&
		   origCommands[origIdx].Type == modCommands[modIdx].Type &&
		   origCommands[origIdx].Original != modCommands[modIdx].Original {
			change := &LayerChange{
				LineNumber:      modCommands[modIdx].LineNumber,
				CommandType:     modCommands[modIdx].Type,
				OriginalCommand: origCommands[origIdx].Original,
				ModifiedCommand: modCommands[modIdx].Original,
				ChangeType:      ChangeModified,
			}
			bp.calculateImpact(change)
			prediction.AffectedLayers = append(prediction.AffectedLayers, change)
			origIdx++
			modIdx++
			continue
		}

		if origIdx < len(origCommands) && (seqIdx >= len(longestSeq) || 
		   origCommands[origIdx].Original != longestSeq[seqIdx].Original) {
			change := &LayerChange{
				LineNumber:      origCommands[origIdx].LineNumber,
				CommandType:     origCommands[origIdx].Type,
				OriginalCommand: origCommands[origIdx].Original,
				ChangeType:      ChangeRemoved,
			}
			bp.calculateImpact(change)
			prediction.AffectedLayers = append(prediction.AffectedLayers, change)
			origIdx++
			continue
		}

		if modIdx < len(modCommands) && (seqIdx >= len(longestSeq) || 
		   modCommands[modIdx].Original != longestSeq[seqIdx].Original) {
			change := &LayerChange{
				LineNumber:      modCommands[modIdx].LineNumber,
				CommandType:     modCommands[modIdx].Type,
				ModifiedCommand: modCommands[modIdx].Original,
				ChangeType:      ChangeAdded,
			}
			bp.calculateImpact(change)
			prediction.AffectedLayers = append(prediction.AffectedLayers, change)
			modIdx++
			continue
		}
	}

	for _, change := range prediction.AffectedLayers {
		switch change.ChangeType {
		case ChangeRemoved:
			prediction.BuildTimeSavedMs += change.TimeImpactMs
			prediction.SizeSavedBytes += change.SizeImpactBytes
		case ChangeAdded:
			prediction.BuildTimeAddedMs += change.TimeImpactMs
			prediction.SizeAddedBytes += change.SizeImpactBytes
		case ChangeModified:
			prediction.BuildTimeAddedMs += change.TimeImpactMs
			prediction.SizeAddedBytes += change.SizeImpactBytes
		}
	}

	prediction.NetTimeChangeMs = prediction.BuildTimeAddedMs - prediction.BuildTimeSavedMs
	prediction.NetSizeChangeBytes = prediction.SizeAddedBytes - prediction.SizeSavedBytes

	origCacheRate := bp.estimateCacheRate(origCommands)
	modCacheRate := bp.estimateCacheRate(modCommands)
	prediction.CacheHitRateChange = modCacheRate - origCacheRate
}

func (bp *BuildPredictor) flattenCommands(pdf *parser.ParsedDockerfile) []*parser.DockerCommand {
	var result []*parser.DockerCommand
	for _, stage := range pdf.Stages {
		result = append(result, stage.Commands...)
	}
	return result
}

func (bp *BuildPredictor) longestCommonSubsequence(a, b []*parser.DockerCommand) []*parser.DockerCommand {
	m, n := len(a), len(b)
	dp := make([][]int, m+1)
	for i := range dp {
		dp[i] = make([]int, n+1)
	}

	for i := 1; i <= m; i++ {
		for j := 1; j <= n; j++ {
			if a[i-1].Original == b[j-1].Original {
				dp[i][j] = dp[i-1][j-1] + 1
			} else {
				dp[i][j] = max(dp[i-1][j], dp[i][j-1])
			}
		}
	}

	var result []*parser.DockerCommand
	i, j := m, n
	for i > 0 && j > 0 {
		if a[i-1].Original == b[j-1].Original {
			result = append([]*parser.DockerCommand{a[i-1]}, result...)
			i--
			j--
		} else if dp[i-1][j] > dp[i][j-1] {
			i--
		} else {
			j--
		}
	}

	return result
}

func (bp *BuildPredictor) calculateImpact(change *LayerChange) {
	stats, exists := bp.performanceDB.CommandStats[string(change.CommandType)]
	if !exists {
		stats = &CommandStats{
			AverageTimeMs: 5000,
			AverageSize:   10 * 1024 * 1024,
		}

		switch change.CommandType {
		case parser.CmdRun:
			stats.AverageTimeMs = 30000
			stats.AverageSize = 50 * 1024 * 1024
		case parser.CmdCopy, parser.CmdAdd:
			stats.AverageTimeMs = 2000
			stats.AverageSize = 5 * 1024 * 1024
		case parser.CmdFrom:
			stats.AverageTimeMs = 10000
			stats.AverageSize = 100 * 1024 * 1024
		}
	}

	change.TimeImpactMs = stats.AverageTimeMs
	change.SizeImpactBytes = stats.AverageSize

	var reasons []string
	reasons = append(reasons, fmt.Sprintf("基于 %d 次历史构建的统计数据", stats.HitCount))
	
	if stats.Variance > 1000000 {
		reasons = append(reasons, "高方差-预测可能不太准确")
	}
	
	change.Reason = strings.Join(reasons, ", ")
}

func (bp *BuildPredictor) estimateCacheRate(commands []*parser.DockerCommand) float64 {
	if len(commands) == 0 {
		return 0
	}

	hittable := 0
	for _, cmd := range commands {
		switch cmd.Type {
		case parser.CmdRun, parser.CmdCopy, parser.CmdAdd, parser.CmdFrom:
			hittable++
		}
	}

	return float64(hittable) / float64(len(commands)) * 0.7
}

func (bp *BuildPredictor) generateRecommendations(prediction *BuildPrediction) {
	if prediction.NetTimeChangeMs < 0 {
		prediction.Recommendations = append(prediction.Recommendations,
			fmt.Sprintf("✓ 构建时间预计减少 %.1f 秒", math.Abs(float64(prediction.NetTimeChangeMs))/1000))
	} else if prediction.NetTimeChangeMs > 0 {
		prediction.Recommendations = append(prediction.Recommendations,
			fmt.Sprintf("⚠ 构建时间预计增加 %.1f 秒", float64(prediction.NetTimeChangeMs)/1000))
	}

	if prediction.NetSizeChangeBytes < 0 {
		prediction.Recommendations = append(prediction.Recommendations,
			fmt.Sprintf("✓ 镜像大小预计减少 %s", formatBytes(uint64(math.Abs(float64(prediction.NetSizeChangeBytes))))))
	} else if prediction.NetSizeChangeBytes > 0 {
		prediction.Recommendations = append(prediction.Recommendations,
			fmt.Sprintf("⚠ 镜像大小预计增加 %s", formatBytes(uint64(prediction.NetSizeChangeBytes))))
	}

	if prediction.CacheHitRateChange > 0.05 {
		prediction.Recommendations = append(prediction.Recommendations,
			fmt.Sprintf("✓ 缓存命中率预计提升 %.1f%%", prediction.CacheHitRateChange*100))
	} else if prediction.CacheHitRateChange < -0.05 {
		prediction.Recommendations = append(prediction.Recommendations,
			fmt.Sprintf("⚠ 缓存命中率预计下降 %.1f%%，建议优化命令顺序", -prediction.CacheHitRateChange*100))
	}

	for _, change := range prediction.AffectedLayers {
		if change.ChangeType == ChangeAdded && change.CommandType == parser.CmdRun {
			if strings.Contains(change.ModifiedCommand, "apt-get install") && 
			   !strings.Contains(change.ModifiedCommand, "&& rm -rf /var/lib/apt/lists/*") {
				prediction.Recommendations = append(prediction.Recommendations,
					"💡 建议在apt-get install后添加清理命令：&& rm -rf /var/lib/apt/lists/*")
			}
		}
	}
}

func (bp *BuildPredictor) SimulateReordering(dockerfilePath string, newOrder []int) (*BuildPrediction, error) {
	content, err := os.ReadFile(dockerfilePath)
	if err != nil {
		return nil, err
	}

	parsed, err := bp.parser.ParseContent(string(content))
	if err != nil {
		return nil, err
	}

	modified := &parser.ParsedDockerfile{
		Stages: make([]*parser.BuildStage, len(parsed.Stages)),
	}

	for i, stage := range parsed.Stages {
		modified.Stages[i] = &parser.BuildStage{
			Name:      stage.Name,
			DependsOn: stage.DependsOn,
			Commands:  make([]*parser.DockerCommand, len(stage.Commands)),
		}
		copy(modified.Stages[i].Commands, stage.Commands)
	}

	return bp.PredictChangesFromContent(string(content), bp.generateDockerfile(modified))
}

func (bp *BuildPredictor) generateDockerfile(pdf *parser.ParsedDockerfile) string {
	var sb strings.Builder
	for _, stage := range pdf.Stages {
		for _, cmd := range stage.Commands {
			sb.WriteString(cmd.Original)
			sb.WriteString("\n")
		}
	}
	return sb.String()
}

func (pred *BuildPrediction) Print() {
	fmt.Println("\n=== 构建影响预测报告 ===")
	fmt.Printf("分析的变更层数: %d\n\n", len(pred.AffectedLayers))

	fmt.Println("--- 受影响的层 ---")
	for _, layer := range pred.AffectedLayers {
		var icon string
		switch layer.ChangeType {
		case ChangeAdded:
			icon = "+"
		case ChangeRemoved:
			icon = "-"
		case ChangeModified:
			icon = "~"
		case ChangeReordered:
			icon = "↕"
		}

		fmt.Printf("\n  [%s] Line %d %s\n", icon, layer.LineNumber, layer.CommandType)
		if layer.ChangeType == ChangeModified {
			fmt.Printf("    原: %s\n", layer.OriginalCommand)
			fmt.Printf("    新: %s\n", layer.ModifiedCommand)
		} else if layer.ChangeType == ChangeRemoved {
			fmt.Printf("    删除: %s\n", layer.OriginalCommand)
		} else {
			fmt.Printf("    新增: %s\n", layer.ModifiedCommand)
		}
		fmt.Printf("    时间影响: %+.1fs | 大小影响: %+s\n",
			float64(layer.TimeImpactMs)/1000, formatBytesWithSign(uint64(layer.SizeImpactBytes)))
		fmt.Printf("    说明: %s\n", layer.Reason)
	}

	fmt.Println("\n--- 总体影响 ---")
	fmt.Printf("构建时间变化: %+.1f 秒\n", float64(pred.NetTimeChangeMs)/1000)
	fmt.Printf("镜像大小变化: %+s\n", formatBytesWithSign(uint64(pred.NetSizeChangeBytes)))
	fmt.Printf("缓存命中率变化: %+.1f%%\n", pred.CacheHitRateChange*100)

	fmt.Println("\n--- 建议 ---")
	for _, rec := range pred.Recommendations {
		fmt.Printf("  %s\n", rec)
	}
}

func (bp *BuildPredictor) SavePerformanceDB(path string) error {
	bp.performanceDB.mu.Lock()
	defer bp.performanceDB.mu.Unlock()

	data, err := json.MarshalIndent(bp.performanceDB, "", "  ")
	if err != nil {
		return err
	}

	dir := filepath.Dir(path)
	if dir != "." && dir != "" {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return err
		}
	}

	return os.WriteFile(path, data, 0644)
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func formatBytes(b uint64) string {
	const unit = 1024
	if b < unit {
		return fmt.Sprintf("%d B", b)
	}
	div, exp := uint64(unit), 0
	for n := b / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %ciB", float64(b)/float64(div), "KMGTPE"[exp])
}

func formatBytesWithSign(b uint64) string {
	result := formatBytes(b)
	if int64(b) > 0 {
		return "+" + result
	}
	return result
}
