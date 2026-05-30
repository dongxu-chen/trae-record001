package cache

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
)

type InvalidationStrategy string

const (
	InvalidationTTL        InvalidationStrategy = "ttl"
	InvalidationLRU        InvalidationStrategy = "lru"
	InvalidationDependency InvalidationStrategy = "dependency"
	InvalidationHybrid     InvalidationStrategy = "hybrid"
)

type CacheEntry struct {
	Key       string
	Value     string
	Tables    []string
	QueryHash string
	TTL       time.Duration
	CreatedAt time.Time
	AccessAt  time.Time
	HitCount  int64
	Size      int64
}

type CacheConfig struct {
	RedisAddr     string
	RedisPassword string
	RedisDB       int
	DefaultTTL    time.Duration
	MaxMemory     int64
	Strategy      InvalidationStrategy
	KeyPrefix     string
	LRUMaxKeys    int
}

type RedisCache struct {
	client     *redis.Client
	config     CacheConfig
	depGraph   *DependencyGraph
	lruTracker *LRUTracker
	mu         sync.RWMutex
}

type DependencyGraph struct {
	tableToKeys map[string]map[string]bool
	keyToTables map[string]map[string]bool
	mu          sync.RWMutex
}

func NewDependencyGraph() *DependencyGraph {
	return &DependencyGraph{
		tableToKeys: make(map[string]map[string]bool),
		keyToTables: make(map[string]map[string]bool),
	}
}

func (dg *DependencyGraph) AddMapping(key string, tables []string) {
	dg.mu.Lock()
	defer dg.mu.Unlock()

	if _, ok := dg.keyToTables[key]; !ok {
		dg.keyToTables[key] = make(map[string]bool)
	}
	for _, t := range tables {
		dg.keyToTables[key][t] = true
		if _, ok := dg.tableToKeys[t]; !ok {
			dg.tableToKeys[t] = make(map[string]bool)
		}
		dg.tableToKeys[t][key] = true
	}
}

func (dg *DependencyGraph) GetKeysForTable(table string) []string {
	dg.mu.RLock()
	defer dg.mu.RUnlock()

	keys := make([]string, 0, len(dg.tableToKeys[table]))
	for k := range dg.tableToKeys[table] {
		keys = append(keys, k)
	}
	return keys
}

func (dg *DependencyGraph) GetTablesForKey(key string) []string {
	dg.mu.RLock()
	defer dg.mu.RUnlock()

	tables := make([]string, 0, len(dg.keyToTables[key]))
	for t := range dg.keyToTables[key] {
		tables = append(tables, t)
	}
	return tables
}

func (dg *DependencyGraph) RemoveKey(key string) {
	dg.mu.Lock()
	defer dg.mu.Unlock()

	tables, ok := dg.keyToTables[key]
	if !ok {
		return
	}
	for t := range tables {
		delete(dg.tableToKeys[t], key)
		if len(dg.tableToKeys[t]) == 0 {
			delete(dg.tableToKeys, t)
		}
	}
	delete(dg.keyToTables, key)
}

type LRUTracker struct {
	maxKeys int
	keys    []string
	access  map[string]time.Time
	mu      sync.Mutex
}

func NewLRUTracker(maxKeys int) *LRUTracker {
	return &LRUTracker{
		maxKeys: maxKeys,
		keys:    make([]string, 0),
		access:  make(map[string]time.Time),
	}
}

func (l *LRUTracker) Touch(key string) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.access[key] = time.Now()
}

func (l *LRUTracker) EvictKeys() []string {
	l.mu.Lock()
	defer l.mu.Unlock()

	if len(l.access) <= l.maxKeys {
		return nil
	}

	type kv struct {
		key string
		t   time.Time
	}

	items := make([]kv, 0, len(l.access))
	for k, v := range l.access {
		items = append(items, kv{k, v})
	}

	for i := 0; i < len(items)-1; i++ {
		for j := i + 1; j < len(items); j++ {
			if items[i].t.After(items[j].t) {
				items[i], items[j] = items[j], items[i]
			}
		}
	}

	evictCount := len(items) - l.maxKeys
	evicted := make([]string, 0, evictCount)
	for i := 0; i < evictCount; i++ {
		evicted = append(evicted, items[i].key)
		delete(l.access, items[i].key)
	}

	return evicted
}

func NewRedisCache(config CacheConfig) *RedisCache {
	if config.KeyPrefix == "" {
		config.KeyPrefix = "heatcache:"
	}
	if config.DefaultTTL == 0 {
		config.DefaultTTL = 30 * time.Minute
	}
	if config.Strategy == "" {
		config.Strategy = InvalidationHybrid
	}
	if config.LRUMaxKeys == 0 {
		config.LRUMaxKeys = 10000
	}

	return &RedisCache{
		config:     config,
		depGraph:   NewDependencyGraph(),
		lruTracker: NewLRUTracker(config.LRUMaxKeys),
	}
}

func (rc *RedisCache) Connect(ctx context.Context) error {
	rc.client = redis.NewClient(&redis.Options{
		Addr:         rc.config.RedisAddr,
		Password:     rc.config.RedisPassword,
		DB:           rc.config.RedisDB,
		MaxRetries:   3,
		DialTimeout:  5 * time.Second,
		ReadTimeout:  3 * time.Second,
		WriteTimeout: 3 * time.Second,
		PoolSize:     10,
	})

	if err := rc.client.Ping(ctx).Err(); err != nil {
		return fmt.Errorf("failed to connect to redis: %w", err)
	}
	return nil
}

func (rc *RedisCache) Close() error {
	if rc.client != nil {
		return rc.client.Close()
	}
	return nil
}

func (rc *RedisCache) buildKey(queryHash string) string {
	return rc.config.KeyPrefix + "query:" + queryHash
}

func (rc *RedisCache) Set(ctx context.Context, entry *CacheEntry) error {
	if rc.client == nil {
		return fmt.Errorf("redis not connected")
	}

	key := rc.buildKey(entry.QueryHash)
	ttl := entry.TTL
	if ttl == 0 {
		ttl = rc.config.DefaultTTL
	}

	entry.Key = key
	entry.CreatedAt = time.Now()
	entry.AccessAt = time.Now()

	data, err := json.Marshal(entry)
	if err != nil {
		return fmt.Errorf("failed to marshal cache entry: %w", err)
	}

	pipe := rc.client.Pipeline()
	pipe.Set(ctx, key, data, ttl)

	if rc.config.Strategy == InvalidationDependency || rc.config.Strategy == InvalidationHybrid {
		rc.depGraph.AddMapping(key, entry.Tables)
	}

	if rc.config.Strategy == InvalidationLRU || rc.config.Strategy == InvalidationHybrid {
		rc.lruTracker.Touch(key)
	}

	if _, err := pipe.Exec(ctx); err != nil {
		return fmt.Errorf("failed to set cache entry: %w", err)
	}

	return nil
}

func (rc *RedisCache) Get(ctx context.Context, queryHash string) (*CacheEntry, error) {
	if rc.client == nil {
		return nil, fmt.Errorf("redis not connected")
	}

	key := rc.buildKey(queryHash)
	data, err := rc.client.Get(ctx, key).Result()
	if err == redis.Nil {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get cache entry: %w", err)
	}

	var entry CacheEntry
	if err := json.Unmarshal([]byte(data), &entry); err != nil {
		return nil, fmt.Errorf("failed to unmarshal cache entry: %w", err)
	}

	entry.HitCount++
	entry.AccessAt = time.Now()

	rc.lruTracker.Touch(key)

	return &entry, nil
}

func (rc *RedisCache) Delete(ctx context.Context, queryHash string) error {
	if rc.client == nil {
		return fmt.Errorf("redis not connected")
	}

	key := rc.buildKey(queryHash)
	rc.depGraph.RemoveKey(key)
	return rc.client.Del(ctx, key).Err()
}

func (rc *RedisCache) InvalidateByTable(ctx context.Context, table string) error {
	if rc.client == nil {
		return fmt.Errorf("redis not connected")
	}

	keys := rc.depGraph.GetKeysForTable(table)
	if len(keys) == 0 {
		return nil
	}

	pipe := rc.client.Pipeline()
	for _, k := range keys {
		pipe.Del(ctx, k)
		rc.depGraph.RemoveKey(k)
	}

	if _, err := pipe.Exec(ctx); err != nil {
		return fmt.Errorf("failed to invalidate by table: %w", err)
	}

	return nil
}

func (rc *RedisCache) InvalidateByPattern(ctx context.Context, pattern string) error {
	if rc.client == nil {
		return fmt.Errorf("redis not connected")
	}

	fullPattern := rc.config.KeyPrefix + "query:" + pattern
	var cursor uint64
	var allKeys []string

	for {
		keys, nextCursor, err := rc.client.Scan(ctx, cursor, fullPattern, 100).Result()
		if err != nil {
			return fmt.Errorf("failed to scan keys: %w", err)
		}
		allKeys = append(allKeys, keys...)
		cursor = nextCursor
		if cursor == 0 {
			break
		}
	}

	if len(allKeys) == 0 {
		return nil
	}

	pipe := rc.client.Pipeline()
	for _, k := range allKeys {
		pipe.Del(ctx, k)
		rc.depGraph.RemoveKey(k)
	}

	if _, err := pipe.Exec(ctx); err != nil {
		return fmt.Errorf("failed to invalidate by pattern: %w", err)
	}

	return nil
}

func (rc *RedisCache) PerformLRUEviction(ctx context.Context) error {
	evicted := rc.lruTracker.EvictKeys()
	if len(evicted) == 0 {
		return nil
	}

	pipe := rc.client.Pipeline()
	for _, k := range evicted {
		pipe.Del(ctx, k)
		rc.depGraph.RemoveKey(k)
	}

	if _, err := pipe.Exec(ctx); err != nil {
		return fmt.Errorf("failed to evict LRU keys: %w", err)
	}

	return nil
}

func (rc *RedisCache) Preheat(ctx context.Context, entries []*CacheEntry) (int, error) {
	if rc.client == nil {
		return 0, fmt.Errorf("redis not connected")
	}

	successCount := 0
	pipe := rc.client.Pipeline()

	for _, entry := range entries {
		key := rc.buildKey(entry.QueryHash)
		ttl := entry.TTL
		if ttl == 0 {
			ttl = rc.config.DefaultTTL
		}

		entry.Key = key
		entry.CreatedAt = time.Now()
		entry.AccessAt = time.Now()

		data, err := json.Marshal(entry)
		if err != nil {
			continue
		}

		pipe.Set(ctx, key, data, ttl)

		if rc.config.Strategy == InvalidationDependency || rc.config.Strategy == InvalidationHybrid {
			rc.depGraph.AddMapping(key, entry.Tables)
		}
		if rc.config.Strategy == InvalidationLRU || rc.config.Strategy == InvalidationHybrid {
			rc.lruTracker.Touch(key)
		}

		successCount++
	}

	if _, err := pipe.Exec(ctx); err != nil {
		return successCount, fmt.Errorf("partial failure during preheat: %w", err)
	}

	return successCount, nil
}

type CacheStats struct {
	TotalKeys  int64
	HitRate    float64
	MemoryUsed int64
	TableCount int
	KeyCount   int
}

func (rc *RedisCache) Stats(ctx context.Context) (*CacheStats, error) {
	if rc.client == nil {
		return nil, fmt.Errorf("redis not connected")
	}

	var cursor uint64
	var count int64
	prefix := rc.config.KeyPrefix + "query:*"

	for {
		keys, nextCursor, err := rc.client.Scan(ctx, cursor, prefix, 100).Result()
		if err != nil {
			return nil, fmt.Errorf("failed to scan: %w", err)
		}
		count += int64(len(keys))
		cursor = nextCursor
		if cursor == 0 {
			break
		}
	}

	info, err := rc.client.Info(ctx, "memory").Result()
	if err != nil {
		return nil, fmt.Errorf("failed to get memory info: %w", err)
	}

	var memoryUsed int64
	for _, line := range strings.Split(info, "\n") {
		if strings.HasPrefix(line, "used_memory:") {
			fmt.Sscanf(strings.TrimPrefix(line, "used_memory:"), "%d", &memoryUsed)
			break
		}
	}

	rc.depGraph.mu.RLock()
	tableCount := len(rc.depGraph.tableToKeys)
	keyCount := len(rc.depGraph.keyToTables)
	rc.depGraph.mu.RUnlock()

	return &CacheStats{
		TotalKeys:  count,
		MemoryUsed: memoryUsed,
		TableCount: tableCount,
		KeyCount:   keyCount,
	}, nil
}

func (rc *RedisCache) Exists(ctx context.Context, queryHash string) (bool, error) {
	if rc.client == nil {
		return false, fmt.Errorf("redis not connected")
	}
	key := rc.buildKey(queryHash)
	n, err := rc.client.Exists(ctx, key).Result()
	if err != nil {
		return false, err
	}
	return n > 0, nil
}
