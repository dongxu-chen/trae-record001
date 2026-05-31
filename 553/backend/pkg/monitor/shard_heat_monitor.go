package monitor

import (
	"context"
	"sync"
	"time"

	"go.uber.org/zap"
	"es-shard-balancer/pkg/config"
	"es-shard-balancer/pkg/elasticsearch"
)

type ShardHeatMonitor struct {
	client        *elasticsearch.Client
	cfg           *config.ShardHeatConfig
	logger        *zap.Logger
	indexHistory  map[string][]elasticsearch.IndexStats
	previousStats map[string]*elasticsearch.IndexStats
	indexHeat     map[string]*elasticsearch.IndexHeatInfo
	mu            sync.RWMutex
}

func NewShardHeatMonitor(client *elasticsearch.Client, cfg *config.ShardHeatConfig, logger *zap.Logger) *ShardHeatMonitor {
	return &ShardHeatMonitor{
		client:        client,
		cfg:           cfg,
		logger:        logger,
		indexHistory:  make(map[string][]elasticsearch.IndexStats),
		previousStats: make(map[string]*elasticsearch.IndexStats),
		indexHeat:     make(map[string]*elasticsearch.IndexHeatInfo),
	}
}

func (shm *ShardHeatMonitor) Start(ctx context.Context) {
	if !shm.cfg.Enabled {
		shm.logger.Info("Shard heat monitor disabled")
		return
	}

	interval := time.Duration(shm.cfg.CollectIntervalSec) * time.Second
	if interval <= 0 {
		interval = 60 * time.Second
	}

	shm.logger.Info("Starting shard heat monitor", zap.Duration("interval", interval))

	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		if err := shm.CollectStats(ctx); err != nil {
			shm.logger.Error("Failed to collect initial shard heat stats", zap.Error(err))
		}

		for {
			select {
			case <-ctx.Done():
				shm.logger.Info("Shard heat monitor stopped")
				return
			case <-ticker.C:
				if err := shm.CollectStats(ctx); err != nil {
					shm.logger.Error("Failed to collect shard heat stats", zap.Error(err))
				}
			}
		}
	}()
}

func (shm *ShardHeatMonitor) CollectStats(ctx context.Context) error {
	stats, err := shm.client.GetIndicesStats(ctx)
	if err != nil {
		return err
	}

	shm.mu.Lock()
	defer shm.mu.Unlock()

	historySize := shm.cfg.HistorySize
	if historySize <= 0 {
		historySize = 10
	}

	for indexName, currentStat := range stats {
		history := shm.indexHistory[indexName]
		history = append(history, *currentStat)
		if len(history) > historySize {
			history = history[len(history)-historySize:]
		}
		shm.indexHistory[indexName] = history

		prevStat := shm.previousStats[indexName]
		if prevStat != nil && currentStat.Timestamp > prevStat.Timestamp {
			intervalSec := float64(currentStat.Timestamp - prevStat.Timestamp)
			if intervalSec > 0 {
				queryDelta := float64(currentStat.QueryCount - prevStat.QueryCount)
				indexDelta := float64(currentStat.IndexCount - prevStat.IndexCount)
				if queryDelta < 0 {
					queryDelta = 0
				}
				if indexDelta < 0 {
					indexDelta = 0
				}

				avgQueriesPerSec := queryDelta / intervalSec
				avgIndexesPerSec := indexDelta / intervalSec

				queryWeight := shm.cfg.QueryWeight
				indexWeight := shm.cfg.IndexWeight
				if queryWeight <= 0 {
					queryWeight = 0.6
				}
				if indexWeight <= 0 {
					indexWeight = 0.4
				}

				normalizedQuery := normalize(avgQueriesPerSec, 1000)
				normalizedIndex := normalize(avgIndexesPerSec, 100)

				heatScore := normalizedQuery*queryWeight + normalizedIndex*indexWeight

				heatThreshold := shm.cfg.HeatThreshold
				if heatThreshold <= 0 {
					heatThreshold = 0.7
				}

				shm.indexHeat[indexName] = &elasticsearch.IndexHeatInfo{
					IndexName:        indexName,
					HeatScore:        heatScore,
					AvgQueriesPerSec: avgQueriesPerSec,
					AvgIndexesPerSec: avgIndexesPerSec,
					IsHot:            heatScore >= heatThreshold,
					History:          history,
				}
			}
		}

		shm.previousStats[indexName] = currentStat
	}

	return nil
}

func normalize(value, max float64) float64 {
	if max <= 0 {
		return 0
	}
	result := value / max
	if result > 1 {
		return 1
	}
	if result < 0 {
		return 0
	}
	return result
}

func (shm *ShardHeatMonitor) GetIndexHeat(indexName string) *elasticsearch.IndexHeatInfo {
	shm.mu.RLock()
	defer shm.mu.RUnlock()
	return shm.indexHeat[indexName]
}

func (shm *ShardHeatMonitor) GetAllIndexHeat() map[string]*elasticsearch.IndexHeatInfo {
	shm.mu.RLock()
	defer shm.mu.RUnlock()

	result := make(map[string]*elasticsearch.IndexHeatInfo)
	for k, v := range shm.indexHeat {
		result[k] = v
	}
	return result
}

func (shm *ShardHeatMonitor) GetShardHeat(shard elasticsearch.ShardInfo, nodeName string) *elasticsearch.ShardHeatInfo {
	indexHeat := shm.GetIndexHeat(shard.Index)
	if indexHeat == nil {
		return &elasticsearch.ShardHeatInfo{
			IndexName: shard.Index,
			ShardNum:  shard.Shard,
			HeatScore: 0,
			IsHot:     false,
			NodeName:  nodeName,
		}
	}

	return &elasticsearch.ShardHeatInfo{
		IndexName: shard.Index,
		ShardNum:  shard.Shard,
		HeatScore: indexHeat.HeatScore,
		IsHot:     indexHeat.IsHot,
		NodeName:  nodeName,
	}
}

func (shm *ShardHeatMonitor) GetHotIndices() []string {
	shm.mu.RLock()
	defer shm.mu.RUnlock()

	var hotIndices []string
	for indexName, heat := range shm.indexHeat {
		if heat.IsHot {
			hotIndices = append(hotIndices, indexName)
		}
	}
	return hotIndices
}

func (shm *ShardHeatMonitor) GetShardPriorityBoost(shard elasticsearch.ShardInfo) float64 {
	if !shm.cfg.Enabled {
		return 1.0
	}

	heat := shm.GetIndexHeat(shard.Index)
	if heat == nil {
		return 1.0
	}

	boost := shm.cfg.PriorityBoost
	if boost <= 0 {
		boost = 1.5
	}

	if heat.IsHot {
		return boost
	}
	return 1.0
}
