package cache

import (
	"container/list"
	"sync"
	"time"
)

type CacheItem struct {
	Key        string
	Size       int64
	AccessedAt time.Time
	CreatedAt  time.Time
}

type LRUCache struct {
	maxSize   int64
	currSize  int64
	items     map[string]*list.Element
	orderList *list.List
	mu        sync.RWMutex
	onEvict   func(key string, size int64)
}

func NewLRUCache(maxSize int64, onEvict func(key string, size int64)) *LRUCache {
	return &LRUCache{
		maxSize:   maxSize,
		items:     make(map[string]*list.Element),
		orderList: list.New(),
		onEvict:   onEvict,
	}
}

func (c *LRUCache) Get(key string) (*CacheItem, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if elem, ok := c.items[key]; ok {
		c.orderList.MoveToFront(elem)
		item := elem.Value.(*CacheItem)
		item.AccessedAt = time.Now()
		return item, true
	}
	return nil, false
}

func (c *LRUCache) Put(key string, size int64) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if elem, ok := c.items[key]; ok {
		c.orderList.MoveToFront(elem)
		item := elem.Value.(*CacheItem)
		c.currSize -= item.Size
		item.Size = size
		item.AccessedAt = time.Now()
		c.currSize += size
		c.evictIfNeeded()
		return nil
	}

	item := &CacheItem{
		Key:        key,
		Size:       size,
		AccessedAt: time.Now(),
		CreatedAt:  time.Now(),
	}

	elem := c.orderList.PushFront(item)
	c.items[key] = elem
	c.currSize += size

	c.evictIfNeeded()
	return nil
}

func (c *LRUCache) Remove(key string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()

	if elem, ok := c.items[key]; ok {
		c.removeElement(elem)
		return true
	}
	return false
}

func (c *LRUCache) removeElement(elem *list.Element) {
	item := elem.Value.(*CacheItem)
	c.orderList.Remove(elem)
	delete(c.items, item.Key)
	c.currSize -= item.Size

	if c.onEvict != nil {
		c.onEvict(item.Key, item.Size)
	}
}

func (c *LRUCache) evictIfNeeded() {
	for c.currSize > c.maxSize && c.orderList.Len() > 0 {
		elem := c.orderList.Back()
		if elem == nil {
			break
		}
		c.removeElement(elem)
	}
}

func (c *LRUCache) Contains(key string) bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	_, ok := c.items[key]
	return ok
}

func (c *LRUCache) Size() int64 {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.currSize
}

func (c *LRUCache) Count() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return len(c.items)
}

func (c *LRUCache) Clear() {
	c.mu.Lock()
	defer c.mu.Unlock()

	for c.orderList.Len() > 0 {
		elem := c.orderList.Back()
		if elem == nil {
			break
		}
		c.removeElement(elem)
	}
}

func (c *LRUCache) Keys() []string {
	c.mu.RLock()
	defer c.mu.RUnlock()

	keys := make([]string, 0, len(c.items))
	for elem := c.orderList.Front(); elem != nil; elem = elem.Next() {
		item := elem.Value.(*CacheItem)
		keys = append(keys, item.Key)
	}
	return keys
}

func (c *LRUCache) GetItems() []CacheItem {
	c.mu.RLock()
	defer c.mu.RUnlock()

	items := make([]CacheItem, 0, len(c.items))
	for elem := c.orderList.Front(); elem != nil; elem = elem.Next() {
		item := elem.Value.(*CacheItem)
		items = append(items, *item)
	}
	return items
}

func (c *LRUCache) Resize(newMaxSize int64) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.maxSize = newMaxSize
	c.evictIfNeeded()
}
