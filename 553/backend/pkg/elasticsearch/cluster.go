package elasticsearch

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
)

type ClusterHealth struct {
	ClusterName                 string  `json:"cluster_name"`
	Status                      string  `json:"status"`
	TimedOut                    bool    `json:"timed_out"`
	NumberOfNodes               int     `json:"number_of_nodes"`
	NumberOfDataNodes           int     `json:"number_of_data_nodes"`
	ActivePrimaryShards         int     `json:"active_primary_shards"`
	ActiveShards                int     `json:"active_shards"`
	RelocatingShards            int     `json:"relocating_shards"`
	InitializingShards          int     `json:"initializing_shards"`
	UnassignedShards            int     `json:"unassigned_shards"`
	DelayedUnassignedShards     int     `json:"delayed_unassigned_shards"`
	NumberOfPendingTasks        int     `json:"number_of_pending_tasks"`
	NumberOfInFlightFetch       int     `json:"number_of_in_flight_fetch"`
	TaskMaxWaitingInQueueMillis int     `json:"task_max_waiting_in_queue_millis"`
	ActiveShardsPercentAsNumber float64 `json:"active_shards_percent_as_number"`
}

type NodeInfo struct {
	Name        string            `json:"name"`
	Host        string            `json:"host"`
	Ip          string            `json:"ip"`
	Roles       []string          `json:"roles"`
	Attributes  map[string]string `json:"attributes"`
}

type NodeStats struct {
	Name  string `json:"name"`
	Host  string `json:"host"`
	Ip    string `json:"ip"`
	FS    FS     `json:"fs"`
}

type FS struct {
	Total     Total     `json:"total"`
	DataNodes []DataNode `json:"data"`
}

type Total struct {
	TotalInBytes     int64 `json:"total_in_bytes"`
	FreeInBytes      int64 `json:"free_in_bytes"`
	AvailableInBytes int64 `json:"available_in_bytes"`
}

type DataNode struct {
	Path             string `json:"path"`
	Mount            string `json:"mount"`
	TotalInBytes     int64  `json:"total_in_bytes"`
	FreeInBytes      int64  `json:"free_in_bytes"`
	AvailableInBytes int64  `json:"available_in_bytes"`
}

type ShardInfo struct {
	Index    string `json:"index"`
	Shard    string `json:"shard"`
	Prirep   string `json:"prirep"`
	State    string `json:"state"`
	Node     string `json:"node"`
	UnassignedReason string `json:"unassigned.reason,omitempty"`
}

type ShardDistribution struct {
	Nodes         map[string]*NodeShardInfo `json:"nodes"`
	TotalShards   int                       `json:"total_shards"`
	AvgShards     float64                   `json:"avg_shards"`
	MaxShards     int                       `json:"max_shards"`
	MinShards     int                       `json:"min_shards"`
	Imbalance     float64                   `json:"imbalance"`
}

type NodeShardInfo struct {
	NodeName       string            `json:"node_name"`
	ShardCount     int               `json:"shard_count"`
	Indices        []string          `json:"indices"`
	Shards         []ShardInfo       `json:"shards"`
	DiskUsage      DiskUsage         `json:"disk_usage"`
	NodeType       string            `json:"node_type"`
}

type DiskUsage struct {
	TotalBytes     int64   `json:"total_bytes"`
	UsedBytes      int64   `json:"used_bytes"`
	AvailableBytes int64   `json:"available_bytes"`
	UsedPercent    float64 `json:"used_percent"`
	DynamicLow     float64 `json:"dynamic_low,omitempty"`
	DynamicHigh    float64 `json:"dynamic_high,omitempty"`
	DynamicFlood   float64 `json:"dynamic_flood,omitempty"`
}

type NodeOSStats struct {
	Timestamp int64   `json:"timestamp"`
	CPU       CPUStats `json:"cpu"`
	IO        IOStats  `json:"io"`
	LoadAvg   []float64 `json:"load_average"`
}

type CPUStats struct {
	Percent     int     `json:"percent"`
	LoadAverage float64 `json:"load_average"`
}

type IOStats struct {
	TotalReadBytes  int64   `json:"total_read_bytes"`
	TotalWriteBytes int64   `json:"total_write_bytes"`
	ReadBytesPerSec int64   `json:"read_bytes_per_sec"`
	WriteBytesPerSec int64  `json:"write_bytes_per_sec"`
	IOWaitPercent   float64 `json:"io_wait_percent"`
}

type NodeLoadHistory struct {
	NodeName    string          `json:"node_name"`
	History     []NodeOSStats   `json:"history"`
	AvgLoad     float64         `json:"avg_load"`
	AvgIOWait   float64         `json:"avg_io_wait"`
	AvgCPU      float64         `json:"avg_cpu"`
	IsHighLoad  bool            `json:"is_high_load"`
	LoadScore   float64         `json:"load_score"`
}

func (c *Client) GetClusterHealth(ctx context.Context) (*ClusterHealth, error) {
	res, err := c.Cluster.Health(
		c.Cluster.Health.WithContext(ctx),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get cluster health: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		return nil, fmt.Errorf("cluster health API error: %s", res.Status())
	}

	var health ClusterHealth
	if err := json.NewDecoder(res.Body).Decode(&health); err != nil {
		return nil, fmt.Errorf("failed to decode cluster health: %w", err)
	}

	return &health, nil
}

func (c *Client) GetNodes(ctx context.Context) (map[string]*NodeInfo, error) {
	res, err := c.Nodes.Info(
		c.Nodes.Info.WithContext(ctx),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get nodes info: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		return nil, fmt.Errorf("nodes info API error: %s", res.Status())
	}

	var result struct {
		Nodes map[string]*NodeInfo `json:"nodes"`
	}
	if err := json.NewDecoder(res.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode nodes info: %w", err)
	}

	return result.Nodes, nil
}

func (c *Client) GetNodesStats(ctx context.Context) (map[string]*NodeStats, error) {
	res, err := c.Nodes.Stats(
		c.Nodes.Stats.WithContext(ctx),
		c.Nodes.Stats.WithMetric("fs"),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get nodes stats: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		return nil, fmt.Errorf("nodes stats API error: %s", res.Status())
	}

	var result struct {
		Nodes map[string]*NodeStats `json:"nodes"`
	}
	if err := json.NewDecoder(res.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode nodes stats: %w", err)
	}

	return result.Nodes, nil
}

func (c *Client) GetNodesOSStats(ctx context.Context) (map[string]*NodeOSStats, error) {
	res, err := c.Nodes.Stats(
		c.Nodes.Stats.WithContext(ctx),
		c.Nodes.Stats.WithMetric("os", "process"),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get nodes OS stats: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		return nil, fmt.Errorf("nodes OS stats API error: %s", res.Status())
	}

	var rawResult struct {
		Nodes map[string]struct {
			Name string `json:"name"`
			OS   struct {
				CPU struct {
					Percent int `json:"percent"`
					LoadAvg struct {
						OneMinute     float64 `json:"1m"`
						FiveMinutes   float64 `json:"5m"`
						FifteenMinutes float64 `json:"15m"`
					} `json:"load_average"`
				} `json:"cpu"`
				Mem struct {
					TotalInBytes int64 `json:"total_in_bytes"`
					FreeInBytes  int64 `json:"free_in_bytes"`
					UsedInBytes  int64 `json:"used_in_bytes"`
				} `json:"mem"`
				Swap struct {
					TotalInBytes int64 `json:"total_in_bytes"`
					FreeInBytes  int64 `json:"free_in_bytes"`
					UsedInBytes  int64 `json:"used_in_bytes"`
				} `json:"swap"`
			} `json:"os"`
			Process struct {
				CPU struct {
					Percent int `json:"percent"`
					Total   struct {
						InMillis int64 `json:"in_millis"`
					} `json:"total"`
				} `json:"cpu"`
			} `json:"process"`
		} `json:"nodes"`
	}

	if err := json.NewDecoder(res.Body).Decode(&rawResult); err != nil {
		return nil, fmt.Errorf("failed to decode nodes OS stats: %w", err)
	}

	result := make(map[string]*NodeOSStats)
	for nodeID, raw := range rawResult.Nodes {
		loadAvg := []float64{raw.OS.CPU.LoadAvg.OneMinute, raw.OS.CPU.LoadAvg.FiveMinutes, raw.OS.CPU.LoadAvg.FifteenMinutes}
		result[nodeID] = &NodeOSStats{
			Timestamp: time.Now().Unix(),
			CPU: CPUStats{
				Percent:     raw.OS.CPU.Percent,
				LoadAverage: raw.OS.CPU.LoadAvg.OneMinute,
			},
			IO: IOStats{
				IOWaitPercent: 0,
			},
			LoadAvg: loadAvg,
		}
	}

	return result, nil
}

func (c *Client) GetShards(ctx context.Context) ([]ShardInfo, error) {
	res, err := c.Cat.Shards(
		c.Cat.Shards.WithContext(ctx),
		c.Cat.Shards.WithFormat("json"),
		c.Cat.Shards.WithV(true),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get shards: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		return nil, fmt.Errorf("cat shards API error: %s", res.Status())
	}

	var shards []ShardInfo
	if err := json.NewDecoder(res.Body).Decode(&shards); err != nil {
		return nil, fmt.Errorf("failed to decode shards: %w", err)
	}

	return shards, nil
}

func (c *Client) GetShardDistribution(ctx context.Context, hotColdEnabled bool, hotAttr, hotValue, coldAttr, coldValue string) (*ShardDistribution, error) {
	nodes, err := c.GetNodes(ctx)
	if err != nil {
		return nil, err
	}

	nodeStats, err := c.GetNodesStats(ctx)
	if err != nil {
		return nil, err
	}

	shards, err := c.GetShards(ctx)
	if err != nil {
		return nil, err
	}

	distribution := &ShardDistribution{
		Nodes: make(map[string]*NodeShardInfo),
	}

	for nodeID, node := range nodes {
		isDataNode := false
		for _, role := range node.Roles {
			if role == "data" || role == "data_hot" || role == "data_cold" {
				isDataNode = true
				break
			}
		}
		if !isDataNode {
			continue
		}

		nodeType := "data"
		if hotColdEnabled {
			if val, ok := node.Attributes[hotAttr]; ok && val == hotValue {
				nodeType = "hot"
			} else if val, ok := node.Attributes[coldAttr]; ok && val == coldValue {
				nodeType = "cold"
			}
		}

		ns := &NodeShardInfo{
			NodeName:   node.Name,
			ShardCount: 0,
			Indices:    []string{},
			Shards:     []ShardInfo{},
			NodeType:   nodeType,
		}

		if stat, ok := nodeStats[nodeID]; ok {
			total := stat.FS.Total.TotalInBytes
			used := total - stat.FS.Total.AvailableInBytes
			var usedPercent float64
			if total > 0 {
				usedPercent = float64(used) / float64(total) * 100
			}
			ns.DiskUsage = DiskUsage{
				TotalBytes:     total,
				UsedBytes:      used,
				AvailableBytes: stat.FS.Total.AvailableInBytes,
				UsedPercent:    usedPercent,
			}
		}

		distribution.Nodes[node.Name] = ns
	}

	indexSet := make(map[string]map[string]bool)
	for _, shard := range shards {
		if shard.State != "STARTED" {
			continue
		}
		if ns, ok := distribution.Nodes[shard.Node]; ok {
			ns.ShardCount++
			ns.Shards = append(ns.Shards, shard)
			if _, ok := indexSet[shard.Index]; !ok {
				indexSet[shard.Index] = make(map[string]bool)
			}
			if !indexSet[shard.Index][shard.Node] {
				indexSet[shard.Index][shard.Node] = true
				ns.Indices = append(ns.Indices, shard.Index)
			}
			distribution.TotalShards++
		}
	}

	dataNodeCount := len(distribution.Nodes)
	if dataNodeCount > 0 {
		distribution.AvgShards = float64(distribution.TotalShards) / float64(dataNodeCount)
	}

	first := true
	for _, ns := range distribution.Nodes {
		if first {
			distribution.MaxShards = ns.ShardCount
			distribution.MinShards = ns.ShardCount
			first = false
		} else {
			if ns.ShardCount > distribution.MaxShards {
				distribution.MaxShards = ns.ShardCount
			}
			if ns.ShardCount < distribution.MinShards {
				distribution.MinShards = ns.ShardCount
			}
		}
	}

	if distribution.AvgShards > 0 {
		distribution.Imbalance = float64(distribution.MaxShards-distribution.MinShards) / distribution.AvgShards
	}

	return distribution, nil
}

type IndexStats struct {
	IndexName       string              `json:"index_name"`
	QueryCount      int64               `json:"query_count"`
	IndexCount      int64               `json:"index_count"`
	QueryTimeMs     int64               `json:"query_time_ms"`
	IndexTimeMs     int64               `json:"index_time_ms"`
	StoreSizeBytes  int64               `json:"store_size_bytes"`
	DocsCount       int64               `json:"docs_count"`
	Timestamp       int64               `json:"timestamp"`
}

type IndexHeatInfo struct {
	IndexName       string  `json:"index_name"`
	HeatScore       float64 `json:"heat_score"`
	AvgQueriesPerSec float64 `json:"avg_queries_per_sec"`
	AvgIndexesPerSec float64 `json:"avg_indexes_per_sec"`
	IsHot           bool    `json:"is_hot"`
	History         []IndexStats `json:"history,omitempty"`
}

type ShardHeatInfo struct {
	IndexName       string  `json:"index_name"`
	ShardNum        string  `json:"shard_num"`
	HeatScore       float64 `json:"heat_score"`
	IsHot           bool    `json:"is_hot"`
	NodeName        string  `json:"node_name"`
}

func (c *Client) GetIndicesStats(ctx context.Context) (map[string]*IndexStats, error) {
	res, err := c.Indices.Stats(
		c.Indices.Stats.WithContext(ctx),
		c.Indices.Stats.WithMetric("search", "indexing", "store", "docs"),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get indices stats: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		return nil, fmt.Errorf("indices stats API error: %s", res.Status())
	}

	var rawResult struct {
		Indices map[string]struct {
			Primaries struct {
				Search struct {
					QueryTotal        int64 `json:"query_total"`
					QueryTimeInMillis int64 `json:"query_time_in_millis"`
				} `json:"search"`
				Indexing struct {
					IndexTotal        int64 `json:"index_total"`
					IndexTimeInMillis int64 `json:"index_time_in_millis"`
				} `json:"indexing"`
				Store struct {
					SizeInBytes int64 `json:"size_in_bytes"`
				} `json:"store"`
				Docs struct {
					Count int64 `json:"count"`
				} `json:"docs"`
			} `json:"primaries"`
		} `json:"indices"`
	}

	if err := json.NewDecoder(res.Body).Decode(&rawResult); err != nil {
		return nil, fmt.Errorf("failed to decode indices stats: %w", err)
	}

	result := make(map[string]*IndexStats)
	now := time.Now().Unix()

	for indexName, raw := range rawResult.Indices {
		result[indexName] = &IndexStats{
			IndexName:      indexName,
			QueryCount:     raw.Primaries.Search.QueryTotal,
			IndexCount:     raw.Primaries.Indexing.IndexTotal,
			QueryTimeMs:    raw.Primaries.Search.QueryTimeInMillis,
			IndexTimeMs:    raw.Primaries.Indexing.IndexTimeInMillis,
			StoreSizeBytes: raw.Primaries.Store.SizeInBytes,
			DocsCount:      raw.Primaries.Docs.Count,
			Timestamp:      now,
		}
	}

	return result, nil
}
