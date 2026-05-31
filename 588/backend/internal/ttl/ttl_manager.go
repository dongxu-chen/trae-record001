package ttl

import (
	"encoding/json"
	"log"
	"sync"
	"time"
	"zk-inspector/internal/storage"
	"zk-inspector/internal/types"

	"github.com/go-zookeeper/zk"
)

type TTLConfig struct {
	Enabled           bool
	DefaultTTL        time.Duration
	CheckInterval     time.Duration
	MaxDeletePerCycle int
}

type TTLInfo struct {
	Path        string    `json:"path"`
	TTLSeconds  int64     `json:"ttl_seconds"`
	ExpireAt    time.Time `json:"expire_at"`
	CreatedAt   time.Time `json:"created_at"`
	AutoDelete  bool      `json:"auto_delete"`
}

type TTLManager struct {
	conn     *zk.Conn
	config   TTLConfig
	ttlIndex map[string]*TTLInfo
	mu       sync.RWMutex
	storage  *storage.MemoryStorage
}

func NewTTLManager(conn *zk.Conn, config TTLConfig, storage *storage.MemoryStorage) *TTLManager {
	return &TTLManager{
		conn:     conn,
		config:   config,
		ttlIndex: make(map[string]*TTLInfo),
		storage:  storage,
	}
}

const TTLMarker = "__ttl_info__"

func (m *TTLManager) SetTTL(path string, ttlSeconds int64, autoDelete bool) error {
	exists, stat, err := m.conn.Exists(path)
	if err != nil {
		return err
	}
	if !exists {
		return zk.ErrNoNode
	}

	ttlInfo := &TTLInfo{
		Path:        path,
		TTLSeconds:  ttlSeconds,
		ExpireAt:    time.Now().Add(time.Duration(ttlSeconds) * time.Second),
		CreatedAt:   time.Unix(0, stat.Mtime*int64(time.Millisecond)),
		AutoDelete:  autoDelete,
	}

	ttlData, err := json.Marshal(ttlInfo)
	if err != nil {
		return err
	}

	ttlPath := path + "/" + TTLMarker
	exists, _, err = m.conn.Exists(ttlPath)
	if err != nil {
		return err
	}

	if exists {
		_, err = m.conn.Set(ttlPath, ttlData, -1)
	} else {
		_, err = m.conn.Create(ttlPath, ttlData, 0, zk.WorldACL(zk.PermAll))
	}

	if err != nil {
		return err
	}

	m.mu.Lock()
	m.ttlIndex[path] = ttlInfo
	m.mu.Unlock()

	return nil
}

func (m *TTLManager) GetTTL(path string) (*TTLInfo, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	info, exists := m.ttlIndex[path]
	return info, exists
}

func (m *TTLManager) RemoveTTL(path string) error {
	ttlPath := path + "/" + TTLMarker
	exists, _, err := m.conn.Exists(ttlPath)
	if err != nil {
		return err
	}

	if exists {
		err = m.conn.Delete(ttlPath, -1)
		if err != nil {
			return err
		}
	}

	m.mu.Lock()
	delete(m.ttlIndex, path)
	m.mu.Unlock()

	return nil
}

func (m *TTLManager) LoadAllTTL(snapshot *storage.Snapshot) {
	if snapshot == nil {
		return
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	m.ttlIndex = make(map[string]*TTLInfo)

	for path := range snapshot.Nodes {
		ttlPath := path + "/" + TTLMarker
		data, _, err := m.conn.Get(ttlPath)
		if err != nil || len(data) == 0 {
			continue
		}

		var ttlInfo TTLInfo
		if err := json.Unmarshal(data, &ttlInfo); err == nil {
			m.ttlIndex[path] = &ttlInfo
		}
	}

	log.Printf("Loaded %d TTL configurations", len(m.ttlIndex))
}

func (m *TTLManager) GetExpiredNodes() []*TTLInfo {
	m.mu.RLock()
	defer m.mu.RUnlock()

	now := time.Now()
	expired := make([]*TTLInfo, 0)

	for _, info := range m.ttlIndex {
		if info.AutoDelete && now.After(info.ExpireAt) {
			expired = append(expired, info)
		}
	}

	return expired
}

func (m *TTLManager) DeleteExpiredNodes() (int, error) {
	if !m.config.Enabled {
		return 0, nil
	}

	expired := m.GetExpiredNodes()
	deleted := 0
	maxDelete := m.config.MaxDeletePerCycle

	for i, info := range expired {
		if maxDelete > 0 && i >= maxDelete {
			break
		}

		err := m.deleteNodeRecursive(info.Path)
		if err != nil {
			log.Printf("Failed to delete expired node %s: %v", info.Path, err)
			continue
		}

		m.mu.Lock()
		delete(m.ttlIndex, info.Path)
		m.mu.Unlock()

		deleted++
		log.Printf("Deleted expired node: %s (TTL: %ds)", info.Path, info.TTLSeconds)
	}

	return deleted, nil
}

func (m *TTLManager) deleteNodeRecursive(path string) error {
	children, _, err := m.conn.Children(path)
	if err != nil {
		return err
	}

	for _, child := range children {
		if child == TTLMarker {
			continue
		}
		childPath := path
		if path == "/" {
			childPath = "/" + child
		} else {
			childPath = path + "/" + child
		}
		m.deleteNodeRecursive(childPath)
	}

	return m.conn.Delete(path, -1)
}

func (m *TTLManager) StartCleanupJob() {
	if !m.config.Enabled {
		log.Println("TTL cleanup is disabled")
		return
	}

	ticker := time.NewTicker(m.config.CheckInterval)
	defer ticker.Stop()

	log.Printf("TTL cleanup job started, interval: %v", m.config.CheckInterval)

	for range ticker.C {
		deleted, err := m.DeleteExpiredNodes()
		if err != nil {
			log.Printf("TTL cleanup error: %v", err)
			continue
		}
		if deleted > 0 {
			log.Printf("TTL cleanup: deleted %d expired nodes", deleted)
		}
	}
}

func (m *TTLManager) GetTTLStats() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	total := len(m.ttlIndex)
	autoDeleteCount := 0
	expiredCount := 0
	now := time.Now()

	for _, info := range m.ttlIndex {
		if info.AutoDelete {
			autoDeleteCount++
		}
		if now.After(info.ExpireAt) {
			expiredCount++
		}
	}

	return map[string]interface{}{
		"total_ttl_nodes":    total,
		"auto_delete_count":  autoDeleteCount,
		"expired_count":      expiredCount,
		"enabled":            m.config.Enabled,
		"default_ttl_seconds": int64(m.config.DefaultTTL.Seconds()),
	}
}

func (m *TTLManager) GetAllTTLNodes() []*TTLInfo {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]*TTLInfo, 0, len(m.ttlIndex))
	for _, info := range m.ttlIndex {
		result = append(result, info)
	}
	return result
}
