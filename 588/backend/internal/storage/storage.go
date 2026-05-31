package storage

import (
	"sort"
	"sync"
	"time"
	"zk-inspector/internal/types"
)

type Snapshot struct {
	Timestamp  time.Time
	Nodes      map[string]*types.NodeInfo
	PathStats  map[string]*PathStat
	Alerts     []Alert
	TotalNodes int
	TotalSize  int64
	MaxDepth   int
}

type PathStat struct {
	Path           string
	NodeCount      int
	TotalDataSize  int64
	MaxDepth       int
	AvgDataSize    int64
	EphemeralCount int
}

type Alert struct {
	Type      string
	Severity  string
	Path      string
	Message   string
	Value     int64
	Threshold int64
	Timestamp time.Time
}

type DataPoint struct {
	Timestamp time.Time
	Value     float64
}

type Prediction struct {
	Path             string
	Metric           string
	HistoricalData   []DataPoint
	PredictedData    []DataPoint
	GrowthRate       float64
	PredictedValue7D float64
	Trend            string
	SeasonType       string
}

type MemoryStorage struct {
	sync.RWMutex
	snapshots    []*Snapshot
	predictions  map[string]*Prediction
	maxSnapshots int
}

func NewMemoryStorage() *MemoryStorage {
	return &MemoryStorage{
		snapshots:    make([]*Snapshot, 0),
		predictions:  make(map[string]*Prediction),
		maxSnapshots: 10080,
	}
}

func (s *MemoryStorage) AddSnapshot(snapshot *Snapshot) {
	s.Lock()
	defer s.Unlock()

	s.snapshots = append(s.snapshots, snapshot)
	if len(s.snapshots) > s.maxSnapshots {
		s.snapshots = s.snapshots[1:]
	}
}

func (s *MemoryStorage) GetLatestSnapshot() *Snapshot {
	s.RLock()
	defer s.RUnlock()

	if len(s.snapshots) == 0 {
		return nil
	}
	return s.snapshots[len(s.snapshots)-1]
}

func (s *MemoryStorage) GetSnapshots(duration time.Duration) []*Snapshot {
	s.RLock()
	defer s.RUnlock()

	cutoff := time.Now().Add(-duration)
	result := make([]*Snapshot, 0)

	for i := len(s.snapshots) - 1; i >= 0; i-- {
		if s.snapshots[i].Timestamp.After(cutoff) {
			result = append([]*Snapshot{s.snapshots[i]}, result...)
		} else {
			break
		}
	}

	return result
}

func (s *MemoryStorage) GetTimeSeries(metric string, duration time.Duration) []DataPoint {
	snapshots := s.GetSnapshots(duration)
	result := make([]DataPoint, 0, len(snapshots))

	for _, snap := range snapshots {
		var value float64
		switch metric {
		case "total_nodes":
			value = float64(snap.TotalNodes)
		case "total_size":
			value = float64(snap.TotalSize)
		case "max_depth":
			value = float64(snap.MaxDepth)
		case "alert_count":
			value = float64(len(snap.Alerts))
		}
		result = append(result, DataPoint{
			Timestamp: snap.Timestamp,
			Value:     value,
		})
	}

	return result
}

func (s *MemoryStorage) GetTopPaths(by string, limit int) []PathStat {
	latest := s.GetLatestSnapshot()
	if latest == nil {
		return nil
	}

	stats := make([]PathStat, 0, len(latest.PathStats))
	for _, stat := range latest.PathStats {
		stats = append(stats, *stat)
	}

	sort.Slice(stats, func(i, j int) bool {
		switch by {
		case "node_count":
			return stats[i].NodeCount > stats[j].NodeCount
		case "total_size":
			return stats[i].TotalDataSize > stats[j].TotalDataSize
		case "max_depth":
			return stats[i].MaxDepth > stats[j].MaxDepth
		default:
			return stats[i].TotalDataSize > stats[j].TotalDataSize
		}
	})

	if len(stats) > limit {
		stats = stats[:limit]
	}

	return stats
}

func (s *MemoryStorage) SetPrediction(key string, pred *Prediction) {
	s.Lock()
	defer s.Unlock()
	s.predictions[key] = pred
}

func (s *MemoryStorage) GetPrediction(key string) *Prediction {
	s.RLock()
	defer s.RUnlock()
	return s.predictions[key]
}

func (s *MemoryStorage) GetAllPredictions() map[string]*Prediction {
	s.RLock()
	defer s.RUnlock()

	result := make(map[string]*Prediction, len(s.predictions))
	for k, v := range s.predictions {
		result[k] = v
	}
	return result
}
