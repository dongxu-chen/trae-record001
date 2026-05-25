package cache

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"cicache/pkg/storage"
)

type DistributedLock struct {
	storage    storage.Storage
	lockKey    string
	nodeID     string
	expiration time.Duration
	acquired   bool
}

type LockInfo struct {
	NodeID    string    `json:"node_id"`
	ExpiresAt time.Time `json:"expires_at"`
	Status    string    `json:"status"`
}

func NewDistributedLock(store storage.Storage, lockKey string, expiration time.Duration) *DistributedLock {
	nodeID := generateNodeID()
	return &DistributedLock{
		storage:    store,
		lockKey:    lockKey,
		nodeID:     nodeID,
		expiration: expiration,
		acquired:   false,
	}
}

func generateNodeID() string {
	b := make([]byte, 16)
	rand.Read(b)
	return hex.EncodeToString(b)
}

func (l *DistributedLock) TryAcquire(ctx context.Context) (bool, error) {
	exists, err := l.storage.Exists(ctx, l.lockKey)
	if err != nil {
		return false, err
	}

	if exists {
		reader, err := l.storage.Download(ctx, l.lockKey)
		if err != nil {
			return false, err
		}
		defer reader.Close()

		var lockInfo LockInfo
		if err := json.NewDecoder(reader).Decode(&lockInfo); err != nil {
			return false, err
		}

		if time.Now().Before(lockInfo.ExpiresAt) {
			return false, nil
		}
	}

	lockInfo := LockInfo{
		NodeID:    l.nodeID,
		ExpiresAt: time.Now().Add(l.expiration),
		Status:    "acquired",
	}

	data, err := json.Marshal(lockInfo)
	if err != nil {
		return false, err
	}

	if err := storage.UploadBytes(ctx, l.storage, l.lockKey, data); err != nil {
		return false, err
	}

	l.acquired = true
	return true, nil
}

func (l *DistributedLock) Acquire(ctx context.Context, maxWait time.Duration) error {
	deadline := time.Now().Add(maxWait)
	for time.Now().Before(deadline) {
		acquired, err := l.TryAcquire(ctx)
		if err != nil {
			return err
		}
		if acquired {
			return nil
		}
		time.Sleep(500 * time.Millisecond)
	}
	return errors.New("timeout waiting for lock")
}

func (l *DistributedLock) Release(ctx context.Context) error {
	if !l.acquired {
		return nil
	}

	reader, err := l.storage.Download(ctx, l.lockKey)
	if err != nil {
		return err
	}
	defer reader.Close()

	var lockInfo LockInfo
	if err := json.NewDecoder(reader).Decode(&lockInfo); err != nil {
		return err
	}

	if lockInfo.NodeID != l.nodeID {
		return errors.New("not the lock owner")
	}

	l.acquired = false
	return l.storage.Delete(ctx, l.lockKey)
}

func (l *DistributedLock) Renew(ctx context.Context) error {
	if !l.acquired {
		return errors.New("lock not acquired")
	}

	lockInfo := LockInfo{
		NodeID:    l.nodeID,
		ExpiresAt: time.Now().Add(l.expiration),
		Status:    "acquired",
	}

	data, err := json.Marshal(lockInfo)
	if err != nil {
		return err
	}

	return storage.UploadBytes(ctx, l.storage, l.lockKey, data)
}

func (l *DistributedLock) GetNodeID() string {
	return l.nodeID
}

func (l *DistributedLock) IsAcquired() bool {
	return l.acquired
}

type PreWarmCoordinator struct {
	storage      storage.Storage
	cacheManager *Manager
	nodeID       string
}

func NewPreWarmCoordinator(store storage.Storage, cm *Manager) *PreWarmCoordinator {
	return &PreWarmCoordinator{
		storage:      store,
		cacheManager: cm,
		nodeID:       generateNodeID(),
	}
}

func (c *PreWarmCoordinator) ExecuteIfMaster(ctx context.Context, cacheKey string, execute func() error) (bool, error) {
	lockKey := fmt.Sprintf("prewarm-lock-%s", cacheKey)
	resultKey := fmt.Sprintf("prewarm-result-%s", cacheKey)

	resultExists, err := c.storage.Exists(ctx, resultKey)
	if err != nil {
		return false, err
	}

	if resultExists {
		return false, nil
	}

	lock := NewDistributedLock(c.storage, lockKey, 5*time.Minute)
	acquired, err := lock.TryAcquire(ctx)
	if err != nil {
		return false, err
	}

	if !acquired {
		waited, err := c.waitForResult(ctx, resultKey, 2*time.Minute)
		if err != nil {
			return false, err
		}
		return !waited, nil
	}

	defer lock.Release(ctx)

	go func() {
		ticker := time.NewTicker(2 * time.Minute)
		defer ticker.Stop()
		for range ticker.C {
			lock.Renew(context.Background())
		}
	}()

	if err := execute(); err != nil {
		return true, err
	}

	resultData := map[string]interface{}{
		"node_id":   c.nodeID,
		"completed_at": time.Now(),
		"status":    "success",
	}
	data, _ := json.Marshal(resultData)
	storage.UploadBytes(ctx, c.storage, resultKey, data)

	return true, nil
}

func (c *PreWarmCoordinator) waitForResult(ctx context.Context, resultKey string, maxWait time.Duration) (bool, error) {
	deadline := time.Now().Add(maxWait)
	for time.Now().Before(deadline) {
		exists, err := c.storage.Exists(ctx, resultKey)
		if err != nil {
			return false, err
		}
		if exists {
			return true, nil
		}
		time.Sleep(1 * time.Second)
	}
	return false, nil
}

func (c *PreWarmCoordinator) IsResultReady(ctx context.Context, cacheKey string) (bool, error) {
	resultKey := fmt.Sprintf("prewarm-result-%s", cacheKey)
	return c.storage.Exists(ctx, resultKey)
}
