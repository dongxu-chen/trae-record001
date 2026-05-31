package cluster

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/go-redis/redis/v8"
	"redis-cluster-scaler/pkg/config"
)

type NodeInfo struct {
	ID        string   `json:"id"`
	Addr      string   `json:"addr"`
	Role      string   `json:"role"`
	Slots     []SlotRange `json:"slots"`
	MasterID  string   `json:"master_id,omitempty"`
	Connected bool     `json:"connected"`
	Memory    MemoryInfo `json:"memory"`
	Keyspace  string   `json:"keyspace"`
}

type SlotRange struct {
	Start uint16 `json:"start"`
	End   uint16 `json:"end"`
}

type MemoryInfo struct {
	UsedBytes     int64   `json:"used_bytes"`
	TotalBytes    int64   `json:"total_bytes"`
	UsedPercent   float64 `json:"used_percent"`
	PeakBytes     int64   `json:"peak_bytes"`
	FragmentRatio float64 `json:"fragment_ratio"`
}

type ClusterStats struct {
	Nodes          []NodeInfo `json:"nodes"`
	TotalSlots     int        `json:"total_slots"`
	AssignedSlots  int        `json:"assigned_slots"`
	TotalKeys      int64      `json:"total_keys"`
	TotalMemory    int64      `json:"total_memory"`
	MasterCount    int        `json:"master_count"`
	ReplicaCount   int        `json:"replica_count"`
}

type Manager struct {
	cfg    config.ClusterConfig
	client *redis.ClusterClient
	mu     sync.RWMutex
}

func NewManager(cfg config.ClusterConfig) *Manager {
	client := redis.NewClusterClient(&redis.ClusterOptions{
		Addrs:     cfg.Addrs,
		Password:  cfg.Password,
		PoolSize:  cfg.PoolSize,
	})
	return &Manager{
		cfg:    cfg,
		client: client,
	}
}

func (m *Manager) Close() error {
	return m.client.Close()
}

func (m *Manager) Ping(ctx context.Context) error {
	return m.client.Ping(ctx).Err()
}

func (m *Manager) GetClusterInfo(ctx context.Context) (map[string]string, error) {
	result, err := m.client.ClusterInfo(ctx).Result()
	if err != nil {
		return nil, fmt.Errorf("cluster info: %w", err)
	}
	info := make(map[string]string)
	for _, line := range strings.Split(result, "\n") {
		parts := strings.SplitN(line, ":", 2)
		if len(parts) == 2 {
			info[strings.TrimSpace(parts[0])] = strings.TrimSpace(parts[1])
		}
	}
	return info, nil
}

func (m *Manager) GetNodes(ctx context.Context) ([]NodeInfo, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result, err := m.client.ClusterNodes(ctx).Result()
	if err != nil {
		return nil, fmt.Errorf("cluster nodes: %w", err)
	}

	var nodes []NodeInfo
	lines := strings.Split(result, "\n")

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		node, err := parseNodeLine(line)
		if err != nil {
			continue
		}
		nodes = append(nodes, *node)
	}

	for i := range nodes {
		mem, err := m.getNodeMemory(ctx, nodes[i].Addr)
		if err == nil {
			nodes[i].Memory = mem
		}
		ks, err := m.getNodeKeyspace(ctx, nodes[i].Addr)
		if err == nil {
			nodes[i].Keyspace = ks
		}
	}

	return nodes, nil
}

func parseNodeLine(line string) (*NodeInfo, error) {
	fields := strings.Fields(line)
	if len(fields) < 8 {
		return nil, fmt.Errorf("invalid node line: %s", line)
	}

	node := &NodeInfo{
		ID:   fields[0],
		Addr: strings.Split(fields[1], "@")[0],
	}

	flags := fields[2]
	if strings.Contains(flags, "master") {
		node.Role = "master"
	} else if strings.Contains(flags, "slave") {
		node.Role = "replica"
	}

	node.Connected = strings.Contains(fields[7], "connected")

	if node.Role == "replica" && len(fields) > 3 {
		node.MasterID = fields[3]
	}

	if node.Role == "master" {
		for i := 8; i < len(fields); i++ {
			slots, err := parseSlotRange(fields[i])
			if err == nil {
				node.Slots = append(node.Slots, slots...)
			}
		}
	}

	return node, nil
}

func parseSlotRange(s string) ([]SlotRange, error) {
	var ranges []SlotRange
	parts := strings.Split(s, ",")
	for _, p := range parts {
		if strings.Contains(p, "-") {
			seg := strings.Split(p, "-")
			if len(seg) != 2 {
				continue
			}
			start, err1 := strconv.ParseUint(seg[0], 10, 16)
			end, err2 := strconv.ParseUint(seg[1], 10, 16)
			if err1 != nil || err2 != nil {
				continue
			}
			ranges = append(ranges, SlotRange{Start: uint16(start), End: uint16(end)})
		} else {
			v, err := strconv.ParseUint(p, 10, 16)
			if err != nil {
				continue
			}
			ranges = append(ranges, SlotRange{Start: uint16(v), End: uint16(v)})
		}
	}
	return ranges, nil
}

func (m *Manager) getNodeMemory(ctx context.Context, addr string) (MemoryInfo, error) {
	client := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: m.cfg.Password,
	})
	defer client.Close()

	result, err := client.Info(ctx, "memory").Result()
	if err != nil {
		return MemoryInfo{}, err
	}

	mem := MemoryInfo{}
	for _, line := range strings.Split(result, "\n") {
		line = strings.TrimSpace(line)
		parts := strings.SplitN(line, ":", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		val := strings.TrimSpace(parts[1])

		switch key {
		case "used_memory":
			mem.UsedBytes, _ = strconv.ParseInt(val, 10, 64)
		case "used_memory_peak":
			mem.PeakBytes, _ = strconv.ParseInt(val, 10, 64)
		case "total_system_memory":
			mem.TotalBytes, _ = strconv.ParseInt(val, 10, 64)
		case "mem_fragmentation_ratio":
			mem.FragmentRatio, _ = strconv.ParseFloat(val, 64)
		}
	}

	if mem.TotalBytes > 0 {
		mem.UsedPercent = float64(mem.UsedBytes) / float64(mem.TotalBytes) * 100
	}

	return mem, nil
}

func (m *Manager) getNodeKeyspace(ctx context.Context, addr string) (string, error) {
	client := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: m.cfg.Password,
	})
	defer client.Close()

	result, err := client.Info(ctx, "keyspace").Result()
	if err != nil {
		return "", err
	}
	return result, nil
}

func (m *Manager) GetClusterStats(ctx context.Context) (*ClusterStats, error) {
	nodes, err := m.GetNodes(ctx)
	if err != nil {
		return nil, err
	}

	stats := &ClusterStats{
		Nodes:       nodes,
		TotalSlots:  16384,
	}

	for _, node := range nodes {
		if node.Role == "master" {
			stats.MasterCount++
			for _, sr := range node.Slots {
				stats.AssignedSlots += int(sr.End - sr.Start + 1)
			}
			stats.TotalMemory += node.Memory.UsedBytes
		} else {
			stats.ReplicaCount++
		}
	}

	return stats, nil
}

func (m *Manager) AddNode(ctx context.Context, addr string) error {
	client := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: m.cfg.Password,
	})
	defer client.Close()

	meetResult := client.ClusterMeet(ctx, addr, 6379)
	if meetResult.Err() != nil {
		return fmt.Errorf("cluster meet: %w", meetResult.Err())
	}

	time.Sleep(2 * time.Second)

	nodeID, err := m.getNodeID(ctx, addr)
	if err != nil {
		return fmt.Errorf("get node id: %w", err)
	}

	for _, seedAddr := range m.cfg.Addrs {
		seedClient := redis.NewClient(&redis.Options{
			Addr:     seedAddr,
			Password: m.cfg.Password,
		})
		meetErr := seedClient.ClusterMeet(ctx, addr, 6379).Err()
		seedClient.Close()
		if meetErr == nil {
			break
		}
	}

	_ = nodeID
	return nil
}

func (m *Manager) RemoveNode(ctx context.Context, nodeID string) error {
	for _, addr := range m.cfg.Addrs {
		client := redis.NewClient(&redis.Options{
			Addr:     addr,
			Password: m.cfg.Password,
		})
		err := client.ClusterForget(ctx, nodeID).Err()
		client.Close()
		if err == nil {
			return nil
		}
	}
	return fmt.Errorf("failed to forget node %s from any seed", nodeID)
}

func (m *Manager) getNodeID(ctx context.Context, addr string) (string, error) {
	client := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: m.cfg.Password,
	})
	defer client.Close()

	result, err := client.ClusterMyID(ctx).Result()
	if err != nil {
		return "", err
	}
	return result, nil
}

func (m *Manager) SetSlot(ctx context.Context, slot uint16, nodeID string, state string) error {
	var cmd *redis.StatusCmd
	switch state {
	case "IMPORTING":
		cmd = m.client.ClusterSetSlotImporting(ctx, slot, nodeID)
	case "MIGRATING":
		cmd = m.client.ClusterSetSlotMigrating(ctx, slot, nodeID)
	case "NODE":
		cmd = m.client.ClusterSetSlotNode(ctx, slot, nodeID)
	case "STABLE":
		cmd = m.client.ClusterSetSlotStable(ctx, slot)
	default:
		return fmt.Errorf("unknown slot state: %s", state)
	}
	return cmd.Err()
}

func (m *Manager) GetKeysInSlot(ctx context.Context, slot uint16, count int64) ([]string, error) {
	return m.client.ClusterGetKeysInSlot(ctx, slot, count).Result()
}

func (m *Manager) CountKeysInSlot(ctx context.Context, slot uint16) (int64, error) {
	return m.client.ClusterCountKeysInSlot(ctx, slot).Result()
}

func (m *Manager) MigrateKey(ctx context.Context, key string, targetAddr string, targetDB int, timeout time.Duration) error {
	return m.client.Migrate(ctx, targetAddr, targetDB, key, 0, timeout).Err()
}

func (m *Manager) GetNodeForSlot(ctx context.Context, slot uint16) (string, error) {
	nodes, err := m.GetNodes(ctx)
	if err != nil {
		return "", err
	}
	for _, node := range nodes {
		if node.Role != "master" {
			continue
		}
		for _, sr := range node.Slots {
			if slot >= sr.Start && slot <= sr.End {
				return node.ID, nil
			}
		}
	}
	return "", fmt.Errorf("slot %d not assigned to any node", slot)
}

func (m *Manager) GetSlotDistribution(ctx context.Context) (map[string]int, error) {
	nodes, err := m.GetNodes(ctx)
	if err != nil {
		return nil, err
	}
	dist := make(map[string]int)
	for _, node := range nodes {
		if node.Role != "master" {
			continue
		}
		count := 0
		for _, sr := range node.Slots {
			count += int(sr.End - sr.Start + 1)
		}
		dist[node.ID[:8]] = count
	}
	return dist, nil
}
