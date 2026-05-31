package elasticsearch

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"time"
)

type MigrationPlan struct {
	Index           string    `json:"index"`
	Shard           string    `json:"shard"`
	FromNode        string    `json:"from_node"`
	ToNode          string    `json:"to_node"`
	Reason          string    `json:"reason"`
	EstimatedSize   int64     `json:"estimated_size"`
	CreatedAt       time.Time `json:"created_at"`
	HeatScore       float64   `json:"heat_score,omitempty"`
	IsHotShard      bool      `json:"is_hot_shard,omitempty"`
}

type MigrationSimulationResult struct {
	Plans                  []MigrationPlan       `json:"plans"`
	BeforeDistribution     *ShardDistribution    `json:"before_distribution"`
	AfterDistribution      *ShardDistribution    `json:"after_distribution"`
	ImprovementMetrics     *SimulationMetrics    `json:"improvement_metrics"`
	EstimatedTimeSeconds   float64               `json:"estimated_time_seconds"`
	EstimatedTotalBytes    int64                 `json:"estimated_total_bytes"`
	Warnings               []string              `json:"warnings"`
}

type SimulationMetrics struct {
	BeforeImbalance     float64 `json:"before_imbalance"`
	AfterImbalance      float64 `json:"after_imbalance"`
	ImbalanceImprovement float64 `json:"imbalance_improvement_percent"`

	BeforeMaxDiskUsage  float64 `json:"before_max_disk_usage"`
	AfterMaxDiskUsage   float64 `json:"after_max_disk_usage"`
	DiskUsageImprovement float64 `json:"disk_usage_improvement_percent"`

	BeforeHotShardsOnHighLoad int `json:"before_hot_shards_on_high_load"`
	AfterHotShardsOnHighLoad  int `json:"after_hot_shards_on_high_load"`
	HotShardImprovement       float64 `json:"hot_shard_improvement_percent"`

	NodesOverHighWatermarkBefore int `json:"nodes_over_high_watermark_before"`
	NodesOverHighWatermarkAfter  int `json:"nodes_over_high_watermark_after"`

	OverallScore float64 `json:"overall_score"`
}

type MigrationStatus struct {
	TaskID          string    `json:"task_id"`
	Index           string    `json:"index"`
	Shard           string    `json:"shard"`
	FromNode        string    `json:"from_node"`
	ToNode          string    `json:"to_node"`
	Status          string    `json:"status"`
	Progress        float64   `json:"progress"`
	BytesTransferred int64    `json:"bytes_transferred"`
	TotalBytes      int64     `json:"total_bytes"`
	StartedAt       time.Time `json:"started_at"`
}

type RerouteRequest struct {
	Commands []RerouteCommand `json:"commands"`
}

type RerouteCommand struct {
	Move *MoveCommand `json:"move,omitempty"`
}

type MoveCommand struct {
	Index     string `json:"index"`
	Shard     int    `json:"shard"`
	FromNode  string `json:"from_node"`
	ToNode    string `json:"to_node"`
}

func (c *Client) MoveShard(ctx context.Context, index string, shard int, fromNode, toNode string) error {
	body := RerouteRequest{
		Commands: []RerouteCommand{
			{
				Move: &MoveCommand{
					Index:    index,
					Shard:    shard,
					FromNode: fromNode,
					ToNode:   toNode,
				},
			},
		},
	}

	jsonBody, err := json.Marshal(body)
	if err != nil {
		return fmt.Errorf("failed to marshal reroute request: %w", err)
	}

	res, err := c.Cluster.Reroute(
		c.Cluster.Reroute.WithContext(ctx),
		c.Cluster.Reroute.WithBody(bytes.NewReader(jsonBody)),
	)
	if err != nil {
		return fmt.Errorf("failed to execute reroute: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		bodyStr, _ := readBody(res.Body)
		return fmt.Errorf("reroute API error: %s, body: %s", res.Status(), bodyStr)
	}

	return nil
}

func (c *Client) GetMigrationTasks(ctx context.Context) ([]MigrationStatus, error) {
	res, err := c.Tasks.List(
		c.Tasks.List.WithContext(ctx),
		c.Tasks.List.WithActions("*shard*move*"),
		c.Tasks.List.WithDetailed(true),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get migration tasks: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		return nil, fmt.Errorf("tasks list API error: %s", res.Status())
	}

	var result struct {
		Tasks map[string]struct {
			Node     string `json:"node"`
			Action   string `json:"action"`
			Status   struct {
				Phase string `json:"phase"`
			} `json:"status"`
			StartTimeInMillis int64 `json:"start_time_in_millis"`
		} `json:"tasks"`
	}

	if err := json.NewDecoder(res.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode tasks: %w", err)
	}

	var migrations []MigrationStatus
	for taskID, task := range result.Tasks {
		migrations = append(migrations, MigrationStatus{
			TaskID:    taskID,
			Status:    task.Status.Phase,
			StartedAt: time.Unix(0, task.StartTimeInMillis*int64(time.Millisecond)),
		})
	}

	return migrations, nil
}

func (c *Client) GetIndexSettings(ctx context.Context, index string) (map[string]interface{}, error) {
	res, err := c.Indices.GetSettings(
		c.Indices.GetSettings.WithContext(ctx),
		c.Indices.GetSettings.WithIndex(index),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get index settings: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		return nil, fmt.Errorf("get settings API error: %s", res.Status())
	}

	var result map[string]interface{}
	if err := json.NewDecoder(res.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode settings: %w", err)
	}

	return result, nil
}

func (c *Client) SetAllocationAwareness(ctx context.Context, attrName string) error {
	body := map[string]interface{}{
		"persistent": map[string]interface{}{
			"cluster.routing.allocation.awareness.attributes": attrName,
		},
	}

	jsonBody, _ := json.Marshal(body)
	res, err := c.Cluster.PutSettings(
		c.Cluster.PutSettings.WithContext(ctx),
		c.Cluster.PutSettings.WithBody(bytes.NewReader(jsonBody)),
	)
	if err != nil {
		return fmt.Errorf("failed to set allocation awareness: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		return fmt.Errorf("put settings API error: %s", res.Status())
	}

	return nil
}

func (c *Client) SetSpeedLimit(ctx context.Context, maxBytesPerSec string) error {
	body := map[string]interface{}{
		"persistent": map[string]interface{}{
			"indices.recovery.max_bytes_per_sec": maxBytesPerSec,
		},
	}

	jsonBody, _ := json.Marshal(body)
	res, err := c.Cluster.PutSettings(
		c.Cluster.PutSettings.WithContext(ctx),
		c.Cluster.PutSettings.WithBody(bytes.NewReader(jsonBody)),
	)
	if err != nil {
		return fmt.Errorf("failed to set speed limit: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		return fmt.Errorf("put settings API error: %s", res.Status())
	}

	return nil
}

func (c *Client) SetDiskWatermark(ctx context.Context, low, high, flood string) error {
	body := map[string]interface{}{
		"persistent": map[string]interface{}{
			"cluster.routing.allocation.disk.watermark.low":         low,
			"cluster.routing.allocation.disk.watermark.high":        high,
			"cluster.routing.allocation.disk.watermark.flood_stage": flood,
		},
	}

	jsonBody, _ := json.Marshal(body)
	res, err := c.Cluster.PutSettings(
		c.Cluster.PutSettings.WithContext(ctx),
		c.Cluster.PutSettings.WithBody(bytes.NewReader(jsonBody)),
	)
	if err != nil {
		return fmt.Errorf("failed to set disk watermark: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		return fmt.Errorf("put settings API error: %s", res.Status())
	}

	return nil
}

func readBody(body io.Reader) string {
	buf := new(bytes.Buffer)
	buf.ReadFrom(body)
	return buf.String()
}
