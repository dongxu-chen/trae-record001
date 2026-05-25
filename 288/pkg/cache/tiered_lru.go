package cache

import (
	"container/list"
	"sync"
	"time"
)

type CacheTier string

const (
	TierCore    CacheTier = "core"
	TierHot     CacheTier = "hot"
	TierWarm    CacheTier = "warm"
	TierCold    CacheTier = "cold"
)

type TieredCacheItem struct {
	Key        string
	Size       int64
	AccessedAt time.Time
	CreatedAt  time.Time
	Tier       CacheTier
	HitCount   int
	LastTierUpgrade time.Time
}

type TieredLRUCache struct {
	mu           sync.RWMutex
	tierSizes    map[CacheTier]int64
	maxTotalSize int64
	items        map[string]*list.Element
	tierLists    map[CacheTier]*list.List
	onEvict      func(key string, size int64, tier CacheTier)
	tierRatio    map[CacheTier]float64
}

type TieredLRUOption func(*TieredLRUCache)

func WithTierRatio(core, hot, warm, cold float64) TieredLRUOption {
	return func(c *TieredLRUCache) {
		c.tierRatio[TierCore] = core
		c.tierRatio[TierHot] = hot
		c.tierRatio[TierWarm] = warm
		c.tierRatio[TierCold] = cold
	}
}

func WithOnTieredEvict(fn func(key string, size int64, tier CacheTier)) TieredLRUOption {
	return func(c *TieredLRUCache) {
		c.onEvict = fn
	}
}

func NewTieredLRUCache(maxTotalSize int64, opts ...TieredLRUOption) *TieredLRUCache {
	c := &TieredLRUCache{
		maxTotalSize: maxTotalSize,
		items:        make(map[string]*list.Element),
		tierLists:    make(map[CacheTier]*list.List),
		tierSizes:    make(map[CacheTier]int64),
		tierRatio: map[CacheTier]float64{
			TierCore: 0.25,
			TierHot:  0.35,
			TierWarm: 0.25,
			TierCold: 0.15,
		},
	}

	for _, tier := range []CacheTier{TierCore, TierHot, TierWarm, TierCold} {
		c.tierLists[tier] = list.New()
	}

	for _, opt := range opts {
		opt(c)
	}

	return c
}

func (c *TieredLRUCache) getTierMaxSize(tier CacheTier) int64 {
	return int64(float64(c.maxTotalSize) * c.tierRatio[tier])
}

func (c *TieredLRUCache) Get(key string) (*TieredCacheItem, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if elem, ok := c.items[key]; ok {
		item := elem.Value.(*TieredCacheItem)
		item.HitCount++
		item.AccessedAt = time.Now()

		c.promoteItem(item, elem)
		c.tierLists[item.Tier].MoveToFront(elem)

		return item, true
	}
	return nil, false
}

func (c *TieredLRUCache) promoteItem(item *TieredCacheItem, elem *list.Element) {
	now := time.Now()
	upgradeInterval := 5 * time.Minute

	if now.Sub(item.LastTierUpgrade) < upgradeInterval {
		return
	}

	hitThreshold := map[CacheTier]int{
		TierCold: 3,
		TierWarm: 5,
		TierHot:  10,
		TierCore: 999,
	}

	nextTier := map[CacheTier]CacheTier{
		TierCold: TierWarm,
		TierWarm: TierHot,
		TierHot:  TierCore,
		TierCore: TierCore,
	}

	if item.HitCount >= hitThreshold[item.Tier] && item.Tier != TierCore {
		c.moveToTier(item, elem, nextTier[item.Tier])
		item.LastTierUpgrade = now
		item.HitCount = 0
	}
}

func (c *TieredLRUCache) moveToTier(item *TieredCacheItem, elem *list.Element, newTier CacheTier) {
	oldTier := item.Tier
	c.tierLists[oldTier].Remove(elem)
	c.tierSizes[oldTier] -= item.Size

	newElem := c.tierLists[newTier].PushFront(item)
	c.items[item.Key] = newElem
	c.tierSizes[newTier] += item.Size

	item.Tier = newTier
}

func (c *TieredLRUCache) Put(key string, size int64, tierHint ...CacheTier) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if elem, ok := c.items[key]; ok {
		item := elem.Value.(*TieredCacheItem)
		c.tierSizes[item.Tier] -= item.Size
		item.Size = size
		item.AccessedAt = time.Now()
		c.tierSizes[item.Tier] += size
		c.tierLists[item.Tier].MoveToFront(elem)
		c.evictIfNeeded()
		return nil
	}

	tier := TierCold
	if len(tierHint) > 0 {
		tier = tierHint[0]
	}

	item := &TieredCacheItem{
		Key:        key,
		Size:       size,
		AccessedAt: time.Now(),
		CreatedAt:  time.Now(),
		Tier:       tier,
		HitCount:   1,
		LastTierUpgrade: time.Now(),
	}

	elem := c.tierLists[tier].PushFront(item)
	c.items[key] = elem
	c.tierSizes[tier] += size

	c.evictIfNeeded()
	return nil
}

func (c *TieredLRUCache) evictIfNeeded() {
	var totalSize int64
	for _, size := range c.tierSizes {
		totalSize += size
	}

	for totalSize > c.maxTotalSize {
		evicted := false

		for _, tier := range []CacheTier{TierCold, TierWarm, TierHot} {
			if c.tierSizes[tier] > 0 {
				elem := c.tierLists[tier].Back()
				if elem != nil {
					c.evictElement(elem, tier)
					evicted = true
					break
				}
			}
		}

		if !evicted {
			if c.tierSizes[TierCore] > 0 {
				elem := c.tierLists[TierCore].Back()
				if elem != nil {
					c.evictElement(elem, TierCore)
				}
			}
		}

		totalSize = 0
		for _, size := range c.tierSizes {
			totalSize += size
		}
	}

	for tier, maxSize := range map[CacheTier]int64{
		TierCore: c.getTierMaxSize(TierCore),
		TierHot:  c.getTierMaxSize(TierHot),
		TierWarm: c.getTierMaxSize(TierWarm),
		TierCold: c.getTierMaxSize(TierCold),
	} {
		for c.tierSizes[tier] > maxSize && tier != TierCore {
			elem := c.tierLists[tier].Back()
			if elem == nil {
				break
			}

			item := elem.Value.(*TieredCacheItem)
			if tier == TierCold {
				c.evictElement(elem, tier)
			} else {
				demoteTier := map[CacheTier]CacheTier{
					TierHot:  TierWarm,
					TierWarm: TierCold,
				}
				c.moveToTier(item, elem, demoteTier[tier])
			}
		}
	}
}

func (c *TieredLRUCache) evictElement(elem *list.Element, tier CacheTier) {
	item := elem.Value.(*TieredCacheItem)
	c.tierLists[tier].Remove(elem)
	delete(c.items, item.Key)
	c.tierSizes[tier] -= item.Size

	if c.onEvict != nil {
		c.onEvict(item.Key, item.Size, tier)
	}
}

func (c *TieredLRUCache) Remove(key string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()

	if elem, ok := c.items[key]; ok {
		item := elem.Value.(*TieredCacheItem)
		c.evictElement(elem, item.Tier)
		return true
	}
	return false
}

func (c *TieredLRUCache) Contains(key string) bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	_, ok := c.items[key]
	return ok
}

func (c *TieredLRUCache) Size() int64 {
	c.mu.RLock()
	defer c.mu.RUnlock()
	var total int64
	for _, size := range c.tierSizes {
		total += size
	}
	return total
}

func (c *TieredLRUCache) Count() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return len(c.items)
}

func (c *TieredLRUCache) GetTierStats() map[CacheTier]map[string]int64 {
	c.mu.RLock()
	defer c.mu.RUnlock()

	stats := make(map[CacheTier]map[string]int64)
	for tier, list := range c.tierLists {
		stats[tier] = map[string]int64{
			"count": int64(list.Len()),
			"size":  c.tierSizes[tier],
		}
	}
	return stats
}

func (c *TieredLRUCache) GetItems() []TieredCacheItem {
	c.mu.RLock()
	defer c.mu.RUnlock()

	items := make([]TieredCacheItem, 0, len(c.items))
	for _, list := range c.tierLists {
		for elem := list.Front(); elem != nil; elem = elem.Next() {
			item := elem.Value.(*TieredCacheItem)
			items = append(items, *item)
		}
	}
	return items
}

func (c *TieredLRUCache) Clear() {
	c.mu.Lock()
	defer c.mu.Unlock()

	for tier, list := range c.tierLists {
		for list.Len() > 0 {
			elem := list.Back()
			if elem == nil {
				break
			}
			c.evictElement(elem, tier)
		}
	}
}

func (c *TieredLRUCache) PromoteToCore(key string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()

	if elem, ok := c.items[key]; ok {
		item := elem.Value.(*TieredCacheItem)
		if item.Tier != TierCore {
			c.moveToTier(item, elem, TierCore)
		}
		return true
	}
	return false
}

func (c *TieredLRUCache) Resize(newMaxSize int64) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.maxTotalSize = newMaxSize
	c.evictIfNeeded()
}
