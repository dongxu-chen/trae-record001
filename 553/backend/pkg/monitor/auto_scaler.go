package monitor

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"

	"go.uber.org/zap"
	"es-shard-balancer/pkg/config"
	"es-shard-balancer/pkg/elasticsearch"
)

type AutoScaler struct {
	client        *elasticsearch.Client
	cfg           *config.AutoScalingConfig
	logger        *zap.Logger
	lastScaleTime time.Time
	mu            sync.Mutex
	httpClient    *http.Client
}

type ScaleEvent struct {
	Timestamp   time.Time `json:"timestamp"`
	EventType   string    `json:"event_type"`
	Reason      string    `json:"reason"`
	CurrentNodes int      `json:"current_nodes"`
	TargetNodes  int      `json:"target_nodes"`
	Success     bool      `json:"success"`
	Message     string    `json:"message"`
}

type WebhookPayload struct {
	Action      string            `json:"action"`
	Reason      string            `json:"reason"`
	NodeType    string            `json:"node_type"`
	DiskSizeGB  int               `json:"disk_size_gb"`
	ClusterName string            `json:"cluster_name"`
	CurrentNodes int              `json:"current_nodes"`
	Metrics     map[string]float64 `json:"metrics"`
}

func NewAutoScaler(client *elasticsearch.Client, cfg *config.AutoScalingConfig, logger *zap.Logger) *AutoScaler {
	return &AutoScaler{
		client:     client,
		cfg:        cfg,
		logger:     logger,
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
}

func (as *AutoScaler) Start(ctx context.Context) {
	if !as.cfg.Enabled {
		as.logger.Info("Auto scaler disabled")
		return
	}

	cooldown := time.Duration(as.cfg.CooldownMinutes) * time.Minute
	if cooldown <= 0 {
		cooldown = 30 * time.Minute
	}

	minNodes := as.cfg.MinNodes
	if minNodes <= 0 {
		minNodes = 3
	}

	maxNodes := as.cfg.MaxNodes
	if maxNodes <= 0 {
		maxNodes = 10
	}

	as.logger.Info("Starting auto scaler",
		zap.Duration("cooldown", cooldown),
		zap.Int("min_nodes", minNodes),
		zap.Int("max_nodes", maxNodes),
	)

	go func() {
		ticker := time.NewTicker(60 * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				as.logger.Info("Auto scaler stopped")
				return
			case <-ticker.C:
				if err := as.CheckAndScale(ctx); err != nil {
					as.logger.Error("Auto scaling check failed", zap.Error(err))
				}
			}
		}
	}()
}

func (as *AutoScaler) CheckAndScale(ctx context.Context) error {
	as.mu.Lock()
	defer as.mu.Unlock()

	minNodes := as.cfg.MinNodes
	if minNodes <= 0 {
		minNodes = 3
	}
	maxNodes := as.cfg.MaxNodes
	if maxNodes <= 0 {
		maxNodes = 10
	}

	cooldown := time.Duration(as.cfg.CooldownMinutes) * time.Minute
	if cooldown <= 0 {
		cooldown = 30 * time.Minute
	}

	if !as.lastScaleTime.IsZero() && time.Since(as.lastScaleTime) < cooldown {
		as.logger.Debug("In cooldown period, skipping scaling check",
			zap.Duration("remaining", cooldown-time.Since(as.lastScaleTime)))
		return nil
	}

	health, err := as.client.GetClusterHealth(ctx)
	if err != nil {
		return fmt.Errorf("failed to get cluster health: %w", err)
	}

	dist, err := as.client.GetShardDistribution(ctx, false, "", "", "", "")
	if err != nil {
		return fmt.Errorf("failed to get shard distribution: %w", err)
	}

	floodThreshold := as.cfg.FloodThreshold
	if floodThreshold <= 0 {
		floodThreshold = 95
	}

	var nodesOverFlood []string
	maxUsage := 0.0

	for nodeName, node := range dist.Nodes {
		if node.DiskUsage.UsedPercent > maxUsage {
			maxUsage = node.DiskUsage.UsedPercent
		}
		if node.DiskUsage.UsedPercent >= floodThreshold {
			nodesOverFlood = append(nodesOverFlood, nodeName)
		}
	}

	as.logger.Debug("Auto scaling check",
		zap.Int("current_nodes", health.NumberOfDataNodes),
		zap.Float64("max_disk_usage", maxUsage),
		zap.Int("nodes_over_flood", len(nodesOverFlood)),
		zap.Float64("flood_threshold", floodThreshold),
	)

	if len(nodesOverFlood) > 0 {
		if health.NumberOfDataNodes >= maxNodes {
			as.logger.Warn("Cannot scale out, already at max nodes",
				zap.Int("current", health.NumberOfDataNodes),
				zap.Int("max", maxNodes))
			return nil
		}

		targetNodes := health.NumberOfDataNodes + 1
		reason := fmt.Sprintf("Nodes %v over flood threshold (%.1f%%), max usage: %.1f%%",
			nodesOverFlood, floodThreshold, maxUsage)

		as.logger.Info("Scaling out cluster",
			zap.String("reason", reason),
			zap.Int("from", health.NumberOfDataNodes),
			zap.Int("to", targetNodes))

		event := as.triggerScaleOut(ctx, health.NumberOfDataNodes, targetNodes, reason, maxUsage, float64(len(nodesOverFlood)))

		if event.Success {
			as.lastScaleTime = time.Now()
		}

		return nil
	}

	as.logger.Debug("No scaling needed")
	return nil
}

func (as *AutoScaler) triggerScaleOut(ctx context.Context, currentNodes, targetNodes int, reason string, maxDiskUsage float64, nodesOverThreshold float64) *ScaleEvent {
	event := &ScaleEvent{
		Timestamp:    time.Now(),
		EventType:    "scale_out",
		Reason:       reason,
		CurrentNodes: currentNodes,
		TargetNodes:  targetNodes,
	}

	switch as.cfg.Provider {
	case "webhook":
		event.Success, event.Message = as.callWebhook(ctx, reason, maxDiskUsage, nodesOverThreshold)
	default:
		event.Success = false
		event.Message = fmt.Sprintf("Unsupported provider: %s", as.cfg.Provider)
		as.logger.Warn(event.Message)
	}

	as.logger.Info("Scale event completed",
		zap.Bool("success", event.Success),
		zap.String("message", event.Message))

	return event
}

func (as *AutoScaler) callWebhook(ctx context.Context, reason string, maxDiskUsage float64, nodesOverThreshold float64) (bool, string) {
	if as.cfg.WebhookURL == "" {
		return false, "webhook URL not configured"
	}

	health, err := as.client.GetClusterHealth(ctx)
	if err != nil {
		return false, fmt.Sprintf("failed to get cluster name: %v", err)
	}

	payload := WebhookPayload{
		Action:      "scale_out",
		Reason:      reason,
		NodeType:    as.cfg.NodeType,
		DiskSizeGB:  as.cfg.DiskSizeGB,
		ClusterName: health.ClusterName,
		CurrentNodes: health.NumberOfDataNodes,
		Metrics: map[string]float64{
			"max_disk_usage":       maxDiskUsage,
			"nodes_over_threshold": nodesOverThreshold,
			"active_shards":        float64(health.ActiveShards),
			"unassigned_shards":    float64(health.UnassignedShards),
		},
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return false, fmt.Sprintf("failed to marshal payload: %v", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", as.cfg.WebhookURL, bytes.NewBuffer(body))
	if err != nil {
		return false, fmt.Sprintf("failed to create request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := as.httpClient.Do(req)
	if err != nil {
		return false, fmt.Sprintf("webhook request failed: %v", err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		return true, fmt.Sprintf("webhook success: %s", string(respBody))
	}

	return false, fmt.Sprintf("webhook returned status %d: %s", resp.StatusCode, string(respBody))
}

func (as *AutoScaler) GetScaleStatus(ctx context.Context) (map[string]interface{}, error) {
	as.mu.Lock()
	defer as.mu.Unlock()

	cooldown := time.Duration(as.cfg.CooldownMinutes) * time.Minute
	if cooldown <= 0 {
		cooldown = 30 * time.Minute
	}

	inCooldown := false
	remaining := 0 * time.Second
	if !as.lastScaleTime.IsZero() {
		elapsed := time.Since(as.lastScaleTime)
		if elapsed < cooldown {
			inCooldown = true
			remaining = cooldown - elapsed
		}
	}

	health, err := as.client.GetClusterHealth(ctx)
	if err != nil {
		return nil, err
	}

	dist, err := as.client.GetShardDistribution(ctx, false, "", "", "", "")
	if err != nil {
		return nil, err
	}

	maxUsage := 0.0
	for _, node := range dist.Nodes {
		if node.DiskUsage.UsedPercent > maxUsage {
			maxUsage = node.DiskUsage.UsedPercent
		}
	}

	return map[string]interface{}{
		"enabled":            as.cfg.Enabled,
		"min_nodes":          as.cfg.MinNodes,
		"max_nodes":          as.cfg.MaxNodes,
		"current_nodes":      health.NumberOfDataNodes,
		"flood_threshold":    as.cfg.FloodThreshold,
		"max_disk_usage":     maxUsage,
		"in_cooldown":        inCooldown,
		"cooldown_remaining": remaining.Seconds(),
		"last_scale_time":    as.lastScaleTime,
		"provider":           as.cfg.Provider,
		"node_type":          as.cfg.NodeType,
	}, nil
}
