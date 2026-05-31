package monitor

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"es-shard-balancer/pkg/config"
	"es-shard-balancer/pkg/elasticsearch"
	"go.uber.org/zap"
)

type SpeedController struct {
	client         *elasticsearch.Client
	cfg            *config.SpeedLimit
	logger         *zap.Logger
	currentSpeed   string
	lastAdjustTime time.Time
	minBytes       int64
	maxBytes       int64
}

func NewSpeedController(client *elasticsearch.Client, cfg *config.SpeedLimit, logger *zap.Logger) *SpeedController {
	sc := &SpeedController{
		client:       client,
		cfg:          cfg,
		logger:       logger,
		currentSpeed: cfg.MaxBytesPerSec,
	}

	sc.minBytes, _ = parseBytesToInt(cfg.MinBytesPerSec)
	sc.maxBytes, _ = parseBytesToInt(cfg.MaxBytesPerSec)

	if sc.minBytes == 0 {
		sc.minBytes = 10 * 1024 * 1024
	}
	if sc.maxBytes == 0 {
		sc.maxBytes = 100 * 1024 * 1024
	}

	return sc
}

func (sc *SpeedController) Start(ctx context.Context) {
	if !sc.cfg.AdaptiveEnabled {
		sc.logger.Info("Adaptive speed control disabled")
		if err := sc.SetSpeed(ctx, sc.cfg.MaxBytesPerSec); err != nil {
			sc.logger.Error("Failed to set initial speed", zap.Error(err))
		}
		return
	}

	interval := time.Duration(sc.cfg.AdjustIntervalSec) * time.Second
	if interval <= 0 {
		interval = 60 * time.Second
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	sc.logger.Info("Adaptive speed controller started",
		zap.String("min_speed", sc.cfg.MinBytesPerSec),
		zap.String("max_speed", sc.cfg.MaxBytesPerSec),
		zap.Duration("interval", interval),
	)

	for {
		select {
		case <-ctx.Done():
			sc.logger.Info("Adaptive speed controller stopped")
			return
		case <-ticker.C:
			sc.adjustSpeed(ctx)
		}
	}
}

func (sc *SpeedController) adjustSpeed(ctx context.Context) {
	if !sc.cfg.AdaptiveEnabled {
		return
	}

	health, err := sc.client.GetClusterHealth(ctx)
	if err != nil {
		sc.logger.Error("Failed to get cluster health for speed adjustment", zap.Error(err))
		return
	}

	targetPending := sc.cfg.TargetPendingTasks
	if targetPending <= 0 {
		targetPending = 5
	}

	currentPending := health.NumberOfPendingTasks
	relocatingShards := health.RelocatingShards

	sc.logger.Debug("Checking speed adjustment",
		zap.Int("pending_tasks", currentPending),
		zap.Int("target_pending", targetPending),
		zap.Int("relocating_shards", relocatingShards),
	)

	ratio := float64(currentPending) / float64(targetPending)
	var newSpeed string

	switch {
	case relocatingShards == 0:
		sc.logger.Debug("No relocating shards, maintaining current speed")
		return

	case ratio < 0.5:
		newSpeed = sc.calculateNewSpeed(1.2)
		sc.logger.Info("Cluster load low, increasing speed",
			zap.String("from", sc.currentSpeed),
			zap.String("to", newSpeed),
		)

	case ratio > 2.0:
		newSpeed = sc.calculateNewSpeed(0.5)
		sc.logger.Info("Cluster load high, decreasing speed",
			zap.String("from", sc.currentSpeed),
			zap.String("to", newSpeed),
		)

	case ratio > 1.5:
		newSpeed = sc.calculateNewSpeed(0.8)
		sc.logger.Info("Cluster load medium-high, slightly decreasing speed",
			zap.String("from", sc.currentSpeed),
			zap.String("to", newSpeed),
		)

	default:
		sc.logger.Debug("Cluster load normal, maintaining current speed",
			zap.Float64("ratio", ratio),
		)
		return
	}

	if newSpeed != sc.currentSpeed {
		if err := sc.SetSpeed(ctx, newSpeed); err != nil {
			sc.logger.Error("Failed to adjust speed", zap.Error(err))
		}
	}
}

func (sc *SpeedController) calculateNewSpeed(factor float64) string {
	currentBytes, _ := parseBytesToInt(sc.currentSpeed)
	if currentBytes == 0 {
		currentBytes = sc.minBytes
	}

	newBytes := int64(float64(currentBytes) * factor)
	newBytes = clamp(newBytes, sc.minBytes, sc.maxBytes)

	return formatBytes(newBytes)
}

func (sc *SpeedController) SetSpeed(ctx context.Context, speed string) error {
	if err := sc.client.SetSpeedLimit(ctx, speed); err != nil {
		return fmt.Errorf("failed to set speed limit: %w", err)
	}

	sc.currentSpeed = speed
	sc.lastAdjustTime = time.Now()

	sc.logger.Info("Migration speed updated", zap.String("speed", speed))
	return nil
}

func (sc *SpeedController) GetCurrentSpeed() string {
	return sc.currentSpeed
}

func (sc *SpeedController) GetSpeedInfo() map[string]interface{} {
	return map[string]interface{}{
		"current_speed":   sc.currentSpeed,
		"min_speed":       sc.cfg.MinBytesPerSec,
		"max_speed":       sc.cfg.MaxBytesPerSec,
		"adaptive_enabled": sc.cfg.AdaptiveEnabled,
		"last_adjust_time": sc.lastAdjustTime,
	}
}

func parseBytesToInt(s string) (int64, error) {
	s = strings.TrimSpace(strings.ToLower(s))

	var multiplier int64 = 1

	switch {
	case strings.HasSuffix(s, "tb"):
		multiplier = 1024 * 1024 * 1024 * 1024
		s = strings.TrimSuffix(s, "tb")
	case strings.HasSuffix(s, "gb"):
		multiplier = 1024 * 1024 * 1024
		s = strings.TrimSuffix(s, "gb")
	case strings.HasSuffix(s, "mb"):
		multiplier = 1024 * 1024
		s = strings.TrimSuffix(s, "mb")
	case strings.HasSuffix(s, "kb"):
		multiplier = 1024
		s = strings.TrimSuffix(s, "kb")
	case strings.HasSuffix(s, "b"):
		s = strings.TrimSuffix(s, "b")
	}

	val, err := strconv.ParseFloat(strings.TrimSpace(s), 64)
	if err != nil {
		return 0, err
	}

	return int64(val * float64(multiplier)), nil
}

func formatBytes(bytes int64) string {
	if bytes < 1024 {
		return fmt.Sprintf("%db", bytes)
	}
	if bytes < 1024*1024 {
		return fmt.Sprintf("%dkb", bytes/1024)
	}
	if bytes < 1024*1024*1024 {
		return fmt.Sprintf("%dmb", bytes/(1024*1024))
	}
	return fmt.Sprintf("%dgb", bytes/(1024*1024*1024))
}

func clamp(val, min, max int64) int64 {
	if val < min {
		return min
	}
	if val > max {
		return max
	}
	return val
}
