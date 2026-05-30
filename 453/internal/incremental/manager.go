package incremental

import (
	"context"
	"crypto/md5"
	"encoding/json"
	"fmt"
	"hash/fnv"
	"sort"
	"sync"
	"time"

	"heatcache/internal/cache"
)

type RefreshType string

const (
	RefreshTypeFull    RefreshType = "full"
	RefreshTypeIncremental RefreshType = "incremental"
	RefreshTypeDelta   RefreshType = "delta"
)

type QueryRefreshInfo struct {
	QueryHash       string
	QuerySQL        string
	DbConfigName    string
	Tables          []string
	RefreshType     RefreshType
	IsDirty         bool
	DirtyReason     string
	DirtyAt         time.Time
	LastRefreshedAt time.Time
	RefreshCount    int
	RefreshPriority float64
	LastDataHash    string
	LastRowCount    int
	HotScore        float64
}

type TableChangeEvent struct {
	Table       string
	Operation   string
	AffectedPKs []interface{}
	AffectedCols []string
	RowCount    int
	Timestamp   time.Time
	DbName      string
}

type DataHashResult struct {
	Hash      string
	RowCount  int
	Timestamp time.Time
}

type IncrementalManager struct {
	queries    map[string]*QueryRefreshInfo
	dirtyQueue chan *QueryRefreshInfo
	cacheLayer *cache.RedisCache
	mu         sync.RWMutex
	ctx        context.Context
	cancel     context.CancelFunc
}

func NewIncrementalManager(cacheLayer *cache.RedisCache, queueSize int) *IncrementalManager {
	if queueSize <= 0 {
		queueSize = 1000
	}
	return &IncrementalManager{
		queries:    make(map[string]*QueryRefreshInfo),
		dirtyQueue: make(chan *QueryRefreshInfo, queueSize),
		cacheLayer: cacheLayer,
	}
}

func (im *IncrementalManager) Start(ctx context.Context) {
	im.ctx, im.cancel = context.WithCancel(ctx)
}

func (im *IncrementalManager) Stop() {
	if im.cancel != nil {
		im.cancel()
	}
	close(im.dirtyQueue)
}

func (im *IncrementalManager) RegisterQuery(queryHash, querySQL, dbConfigName string, tables []string, hotScore float64) {
	im.mu.Lock()
	defer im.mu.Unlock()

	if info, exists := im.queries[queryHash]; exists {
		info.HotScore = hotScore
		info.DbConfigName = dbConfigName
		info.QuerySQL = querySQL
		info.Tables = tables
		return
	}

	im.queries[queryHash] = &QueryRefreshInfo{
		QueryHash:    queryHash,
		QuerySQL:     querySQL,
		DbConfigName: dbConfigName,
		Tables:       tables,
		RefreshType:  RefreshTypeFull,
		IsDirty:      false,
		HotScore:     hotScore,
	}
}

func (im *IncrementalManager) MarkDirty(table, reason string) int {
	im.mu.Lock()
	defer im.mu.Unlock()

	marked := 0
	for _, info := range im.queries {
		for _, t := range info.Tables {
			if t == table {
				if !info.IsDirty {
					info.IsDirty = true
					info.DirtyReason = reason
					info.DirtyAt = time.Now()
					select {
					case im.dirtyQueue <- info:
						marked++
					default:
					}
				}
				break
			}
		}
	}
	return marked
}

func (im *IncrementalManager) MarkDirtyByEvent(event *TableChangeEvent) int {
	im.mu.Lock()
	defer im.mu.Unlock()

	marked := 0
	for _, info := range im.queries {
		affected := false
		for _, t := range info.Tables {
			if t == event.Table {
				affected = true
				break
			}
		}
		if !affected {
			continue
		}

		refreshType := im.determineRefreshType(info, event)

		if !info.IsDirty {
			info.IsDirty = true
			info.DirtyReason = fmt.Sprintf("%s on %s", event.Operation, event.Table)
			info.DirtyAt = event.Timestamp
			info.RefreshType = refreshType
			info.RefreshPriority = im.calculatePriority(info, event)

			select {
			case im.dirtyQueue <- info:
				marked++
			default:
			}
		} else {
			if refreshType == RefreshTypeFull && info.RefreshType != RefreshTypeFull {
				info.RefreshType = RefreshTypeFull
			}
			newPriority := im.calculatePriority(info, event)
			if newPriority > info.RefreshPriority {
				info.RefreshPriority = newPriority
			}
		}
	}
	return marked
}

func (im *IncrementalManager) determineRefreshType(info *QueryRefreshInfo, event *TableChangeEvent) RefreshType {
	if event.RowCount > 1000 {
		return RefreshTypeFull
	}

	if len(event.AffectedPKs) > 0 && len(info.QuerySQL) > 0 {
		for _, pk := range event.AffectedPKs {
			pkStr := fmt.Sprintf("%v", pk)
			if containsValue(info.QuerySQL, pkStr) {
				return RefreshTypeFull
			}
		}
	}

	if len(event.AffectedCols) > 0 {
		for _, col := range event.AffectedCols {
			if containsValue(info.QuerySQL, col) {
				return RefreshTypeDelta
			}
		}
	}

	return RefreshTypeIncremental
}

func (im *IncrementalManager) calculatePriority(info *QueryRefreshInfo, event *TableChangeEvent) float64 {
	basePriority := info.HotScore * 0.6
	rowWeight := 0.0
	if event.RowCount > 0 {
		rowWeight = float64(event.RowCount) / 100.0
		if rowWeight > 0.4 {
			rowWeight = 0.4
		}
	}

	age := time.Since(event.Timestamp).Seconds()
	ageDecay := 1.0 / (1.0 + age/60.0)

	return basePriority + rowWeight*0.4*ageDecay
}

func (im *IncrementalManager) GetDirtyQueries(limit int) []*QueryRefreshInfo {
	im.mu.RLock()
	defer im.mu.RUnlock()

	dirty := make([]*QueryRefreshInfo, 0, len(im.queries))
	for _, info := range im.queries {
		if info.IsDirty {
			dirty = append(dirty, info)
		}
	}

	sort.Slice(dirty, func(i, j int) bool {
		return dirty[i].RefreshPriority > dirty[j].RefreshPriority
	})

	if limit > 0 && limit < len(dirty) {
		dirty = dirty[:limit]
	}

	return dirty
}

func (im *IncrementalManager) GetDirtyQueue() <-chan *QueryRefreshInfo {
	return im.dirtyQueue
}

func (im *IncrementalManager) MarkRefreshed(queryHash string, dataHash string, rowCount int) {
	im.mu.Lock()
	defer im.mu.Unlock()

	if info, exists := im.queries[queryHash]; exists {
		info.IsDirty = false
		info.LastRefreshedAt = time.Now()
		info.LastDataHash = dataHash
		info.LastRowCount = rowCount
		info.RefreshCount++
		info.RefreshType = RefreshTypeIncremental
	}
}

func (im *IncrementalManager) ComputeDataHash(rows []map[string]interface{}) *DataHashResult {
	if len(rows) == 0 {
		return &DataHashResult{
			Hash:      "empty",
			RowCount:  0,
			Timestamp: time.Now(),
		}
	}

	keys := make([]string, 0, len(rows[0]))
	for k := range rows[0] {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	h := md5.New()
	h.Write([]byte(fmt.Sprintf("rows:%d", len(rows))))

	for _, row := range rows {
		rowHash := fnv.New64a()
		for _, k := range keys {
			val := fmt.Sprintf("%v", row[k])
			rowHash.Write([]byte(k + "=" + val + ";"))
		}
		h.Write([]byte(fmt.Sprintf("%x", rowHash.Sum64())))
	}

	return &DataHashResult{
		Hash:      fmt.Sprintf("%x", h.Sum(nil)),
		RowCount:  len(rows),
		Timestamp: time.Now(),
	}
}

func (im *IncrementalManager) NeedsRefresh(queryHash string, newHash *DataHashResult) bool {
	im.mu.RLock()
	defer im.mu.RUnlock()

	info, exists := im.queries[queryHash]
	if !exists {
		return true
	}

	if info.LastDataHash != newHash.Hash {
		return true
	}

	if info.LastRowCount != newHash.RowCount {
		return true
	}

	return false
}

func (im *IncrementalManager) GetQueryInfo(queryHash string) (*QueryRefreshInfo, bool) {
	im.mu.RLock()
	defer im.mu.RUnlock()
	info, exists := im.queries[queryHash]
	return info, exists
}

func (im *IncrementalManager) GetAllQueryInfos() []*QueryRefreshInfo {
	im.mu.RLock()
	defer im.mu.RUnlock()

	infos := make([]*QueryRefreshInfo, 0, len(im.queries))
	for _, info := range im.queries {
		infos = append(infos, info)
	}
	return infos
}

func (im *IncrementalManager) GetDirtyCount() int {
	im.mu.RLock()
	defer im.mu.RUnlock()

	count := 0
	for _, info := range im.queries {
		if info.IsDirty {
			count++
		}
	}
	return count
}

func (im *IncrementalManager) GetTotalCount() int {
	im.mu.RLock()
	defer im.mu.RUnlock()
	return len(im.queries)
}

func (im *IncrementalManager) SaveState(ctx context.Context, key string) error {
	im.mu.RLock()
	defer im.mu.RUnlock()

	data, err := json.Marshal(im.queries)
	if err != nil {
		return err
	}

	entry := &cache.CacheEntry{
		QueryHash: key,
		Value:     string(data),
		TTL:       24 * time.Hour,
	}

	return im.cacheLayer.Set(ctx, entry)
}

func (im *IncrementalManager) LoadState(ctx context.Context, key string) error {
	entry, err := im.cacheLayer.Get(ctx, key)
	if err != nil {
		return err
	}
	if entry == nil {
		return nil
	}

	var loaded map[string]*QueryRefreshInfo
	if err := json.Unmarshal([]byte(entry.Value), &loaded); err != nil {
		return err
	}

	im.mu.Lock()
	defer im.mu.Unlock()
	im.queries = loaded
	return nil
}

func (im *IncrementalManager) Cleanup(maxAge time.Duration) int {
	im.mu.Lock()
	defer im.mu.Unlock()

	cutoff := time.Now().Add(-maxAge)
	removed := 0

	for hash, info := range im.queries {
		if info.LastRefreshedAt.Before(cutoff) && !info.IsDirty {
			delete(im.queries, hash)
			removed++
		}
	}
	return removed
}

func containsValue(s, substr string) bool {
	return len(substr) > 0 && len(s) > 0 && (len(s) >= len(substr)) &&
		(s == substr || len(s) > len(substr) && (s[:len(substr)] == substr ||
			s[len(s)-len(substr):] == substr ||
			containsSubstring(s, substr)))
}

func containsSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
