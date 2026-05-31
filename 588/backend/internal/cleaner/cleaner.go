package cleaner

import (
	"log"
	"strings"
	"sync"
	"time"
	"zk-inspector/internal/types"

	"github.com/go-zookeeper/zk"
)

type TTLCleaner struct {
	conn       *zk.Conn
	ttlRecords map[string]*types.TTLRecord
	mu         sync.RWMutex
	history    []*types.CleanResult
	maxHistory int
	enabled    bool
}

func NewTTLCleaner(conn *zk.Conn) *TTLCleaner {
	return &TTLCleaner{
		conn:       conn,
		ttlRecords: make(map[string]*types.TTLRecord),
		maxHistory: 100,
		enabled:    true,
	}
}

func (tc *TTLCleaner) RegisterTTL(path string, ttlSeconds int64) {
	tc.mu.Lock()
	defer tc.mu.Unlock()
	now := time.Now()
	tc.ttlRecords[path] = &types.TTLRecord{
		Path:      path,
		TTL:       ttlSeconds,
		CreatedAt: now,
		ExpiresAt: now.Add(time.Duration(ttlSeconds) * time.Second),
	}
}

func (tc *TTLCleaner) UnregisterTTL(path string) {
	tc.mu.Lock()
	defer tc.mu.Unlock()
	delete(tc.ttlRecords, path)
}

func (tc *TTLCleaner) GetTTLRecords() []*types.TTLRecord {
	tc.mu.RLock()
	defer tc.mu.RUnlock()
	records := make([]*types.TTLRecord, 0, len(tc.ttlRecords))
	for _, r := range tc.ttlRecords {
		records = append(records, r)
	}
	return records
}

func (tc *TTLCleaner) GetCleanHistory() []*types.CleanResult {
	tc.mu.RLock()
	defer tc.mu.RUnlock()
	return tc.history
}

func (tc *TTLCleaner) SetEnabled(enabled bool) {
	tc.mu.Lock()
	defer tc.mu.Unlock()
	tc.enabled = enabled
}

func (tc *TTLCleaner) scanAndClean() *types.CleanResult {
	result := &types.CleanResult{
		Timestamp:    time.Now(),
		Deleted:      []string{},
		Errors:       []string{},
		Scanned:      0,
		DeletedCount: 0,
	}

	tc.mu.RLock()
	records := make(map[string]*types.TTLRecord)
	for k, v := range tc.ttlRecords {
		records[k] = v
	}
	enabled := tc.enabled
	tc.mu.RUnlock()

	if !enabled {
		return result
	}

	tc.scanStaleNodes("/", result)

	now := time.Now()
	for path, record := range records {
		result.Scanned++
		if now.After(record.ExpiresAt) {
			if err := tc.deleteRecursive(path); err != nil {
				result.Errors = append(result.Errors, "Failed to delete "+path+": "+err.Error())
			} else {
				result.Deleted = append(result.Deleted, path)
				result.DeletedCount++
				tc.UnregisterTTL(path)
				log.Printf("TTL cleaner: deleted expired node %s", path)
			}
		}
	}

	return result
}

func (tc *TTLCleaner) scanStaleNodes(rootPath string, result *types.CleanResult) {
	stack := []string{rootPath}
	visited := make(map[string]bool)

	for len(stack) > 0 {
		currentPath := stack[len(stack)-1]
		stack = stack[:len(stack)-1]

		if visited[currentPath] {
			continue
		}
		visited[currentPath] = true

		exists, stat, err := tc.conn.Exists(currentPath)
		if err != nil || !exists {
			continue
		}

		result.Scanned++

		modTime := time.Unix(0, stat.Mtime*int64(time.Millisecond))
		if time.Since(modTime) > 7*24*time.Hour && stat.EphemeralOwner == 0 {
			data, _, _ := tc.conn.Get(currentPath)
			if len(data) == 0 {
				subChildren, _, err := tc.conn.Children(currentPath)
				if err == nil && len(subChildren) == 0 {
					if err := tc.conn.Delete(currentPath, -1); err == nil {
						result.Deleted = append(result.Deleted, currentPath)
						result.DeletedCount++
						log.Printf("TTL cleaner: auto-cleaned stale empty node %s", currentPath)
					}
				}
			}
		}

		if strings.HasPrefix(currentPath, "/_ttl_") || strings.HasSuffix(currentPath, "_ttl") {
			data, _, err := tc.conn.Get(currentPath)
			if err == nil && len(data) > 0 {
				if ttlSeconds := parseDuration(string(data)); ttlSeconds > 0 {
					tc.RegisterTTL(currentPath, int64(ttlSeconds.Seconds()))
				}
			}
		}

		children, _, err := tc.conn.Children(currentPath)
		if err != nil {
			continue
		}
		for i := len(children) - 1; i >= 0; i-- {
			child := children[i]
			childPath := currentPath
			if childPath == "/" {
				childPath = "/" + child
			} else {
				childPath = childPath + "/" + child
			}
			if !visited[childPath] {
				stack = append(stack, childPath)
			}
		}
	}
}

func (tc *TTLCleaner) deleteRecursive(path string) error {
	children, _, err := tc.conn.Children(path)
	if err != nil {
		if err == zk.ErrNoNode {
			return nil
		}
		return err
	}
	for _, child := range children {
		childPath := path + "/" + child
		if path == "/" {
			childPath = "/" + child
		}
		if err := tc.deleteRecursive(childPath); err != nil {
			return err
		}
	}
	_, stat, err := tc.conn.Exists(path)
	if err != nil {
		return err
	}
	if stat != nil {
		return tc.conn.Delete(path, stat.Version)
	}
	return nil
}

func (tc *TTLCleaner) StartCleanupJob(interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	log.Printf("TTL cleaner started with interval %v", interval)
	for range ticker.C {
		result := tc.scanAndClean()
		if result.DeletedCount > 0 || len(result.Errors) > 0 {
			log.Printf("TTL clean: scanned=%d deleted=%d errors=%d",
				result.Scanned, result.DeletedCount, len(result.Errors))
		}
		tc.mu.Lock()
		tc.history = append(tc.history, result)
		if len(tc.history) > tc.maxHistory {
			tc.history = tc.history[1:]
		}
		tc.mu.Unlock()
	}
}

func (tc *TTLCleaner) ManualClean() *types.CleanResult {
	return tc.scanAndClean()
}

func parseDuration(s string) time.Duration {
	d, err := time.ParseDuration(s)
	if err != nil {
		if strings.HasSuffix(s, "d") {
			return 0
		}
		return 0
	}
	return d
}
