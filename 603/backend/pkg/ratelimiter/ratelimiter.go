package ratelimiter

import (
	"fmt"
	"sync"
	"time"

	"golang.org/x/time/rate"
	"pulsar-backlog-manager/pkg/audit"
	"pulsar-backlog-manager/pkg/config"
	"pulsar-backlog-manager/pkg/monitor"
	"pulsar-backlog-manager/pkg/pulsar"
	"pulsar-backlog-manager/pkg/strategy"
)

type throttleLevel int

const (
	throttleNone   throttleLevel = iota
	throttleLight                = 70
	throttleMedium               = 40
	throttleHeavy                = 10
)

type subLimiter struct {
	limiter      *rate.Limiter
	currentRate  float64
	baseRate     float64
	level        throttleLevel
	lastAdjusted time.Time
}

type topicLimiter struct {
	topicRate    float64
	baseRate     float64
	currentRate  float64
	level        throttleLevel
	lastAdjusted time.Time
	subs         map[string]*subLimiter
}

type RateLimiter struct {
	config     config.RateLimiterConfig
	pulsar     *pulsar.Client
	strategy   *strategy.Manager
	audit      *audit.AuditLogger
	topics     map[string]*topicLimiter
	mu         sync.Mutex
}

func NewRateLimiter(cfg config.RateLimiterConfig, pulsarClient *pulsar.Client, strategyMgr *strategy.Manager, auditLog *audit.AuditLogger) *RateLimiter {
	return &RateLimiter{
		config:   cfg,
		pulsar:   pulsarClient,
		strategy: strategyMgr,
		audit:    auditLog,
		topics:   make(map[string]*topicLimiter),
	}
}

func (r *RateLimiter) HandleBacklog(backlog monitor.TopicBacklog) {
	if !r.config.Enabled {
		return
	}

	strategyCfg := r.strategy.GetStrategy(backlog.Topic)
	if strategyCfg != nil && !strategyCfg.RateLimit.Enabled {
		return
	}

	r.mu.Lock()
	defer r.mu.Unlock()

	maxRate := r.config.MaxRate
	subBacklogThreshold := 10000
	subRecoveryThreshold := 1000
	topicBacklogThreshold := 50000

	if strategyCfg != nil {
		maxRate = float64(strategyCfg.RateLimit.MaxRate)
		subBacklogThreshold = strategyCfg.RateLimit.BacklogThreshold
		subRecoveryThreshold = strategyCfg.RateLimit.RecoveryThreshold
		topicBacklogThreshold = strategyCfg.RateLimit.TopicBacklogThreshold
	}

	tl, exists := r.topics[backlog.Topic]
	if !exists {
		tl = &topicLimiter{
			topicRate:   maxRate,
			baseRate:    maxRate,
			currentRate: maxRate,
			level:       throttleNone,
			subs:        make(map[string]*subLimiter),
		}
		r.topics[backlog.Topic] = tl
	}

	r.adjustSubscription(tl, backlog, subBacklogThreshold, subRecoveryThreshold)
	r.adjustTopicLevel(tl, backlog, topicBacklogThreshold)
}

func (r *RateLimiter) adjustSubscription(tl *topicLimiter, backlog monitor.TopicBacklog, threshold, recoveryThreshold int) {
	subKey := backlog.Subscription
	sl, exists := tl.subs[subKey]
	if !exists {
		subRate := tl.baseRate
		sl = &subLimiter{
			limiter:     rate.NewLimiter(rate.Limit(subRate), int(subRate)),
			currentRate: subRate,
			baseRate:    subRate,
			level:       throttleNone,
		}
		tl.subs[subKey] = sl
	}

	if time.Since(sl.lastAdjusted) < 1*time.Minute {
		return
	}

	var newLevel throttleLevel
	if backlog.BacklogSize > int64(threshold)*4 {
		newLevel = throttleHeavy
	} else if backlog.BacklogSize > int64(threshold)*2 {
		newLevel = throttleMedium
	} else if backlog.BacklogSize > int64(threshold) {
		newLevel = throttleLight
	} else if backlog.BacklogSize < int64(recoveryThreshold) {
		newLevel = throttleNone
	} else {
		return
	}

	if newLevel == sl.level {
		return
	}

	oldLevel := sl.level
	sl.level = newLevel

	if newLevel == throttleNone {
		sl.currentRate = sl.baseRate
	} else {
		sl.currentRate = sl.baseRate * float64(newLevel) / 100.0
		if sl.currentRate < 1 {
			sl.currentRate = 1
		}
	}

	sl.limiter.SetLimit(rate.Limit(sl.currentRate))
	sl.limiter.SetBurst(int(sl.currentRate))
	sl.lastAdjusted = time.Now()

	r.audit.Log(audit.ActionRateLimit, backlog.Topic,
		"Subscription [%s] throttle: level %d%% → %d%%, rate %.2f → %.2f msg/s (backlog %d)",
		subKey, oldLevel, newLevel, sl.baseRate, sl.currentRate, backlog.BacklogSize)
}

func (r *RateLimiter) adjustTopicLevel(tl *topicLimiter, backlog monitor.TopicBacklog, topicThreshold int) {
	if time.Since(tl.lastAdjusted) < 2*time.Minute {
		return
	}

	heavyCount := 0
	mediumCount := 0
	for _, sl := range tl.subs {
		if sl.level == throttleHeavy {
			heavyCount++
		} else if sl.level == throttleMedium {
			mediumCount++
		}
	}

	var newLevel throttleLevel
	if heavyCount >= 2 || (heavyCount >= 1 && mediumCount >= 1) || backlog.BacklogSize > int64(topicThreshold) {
		newLevel = throttleMedium
		if heavyCount >= 3 || backlog.BacklogSize > int64(topicThreshold)*2 {
			newLevel = throttleHeavy
		}
	} else if heavyCount == 0 && mediumCount == 0 {
		allRecovered := true
		for _, sl := range tl.subs {
			if sl.level != throttleNone {
				allRecovered = false
				break
			}
		}
		if allRecovered {
			newLevel = throttleNone
		}
	}

	if newLevel == tl.level {
		return
	}

	oldLevel := tl.level
	tl.level = newLevel

	if newLevel == throttleNone {
		tl.currentRate = tl.baseRate
	} else {
		tl.currentRate = tl.baseRate * float64(newLevel) / 100.0
		if tl.currentRate < 1 {
			tl.currentRate = 1
		}
	}

	tl.lastAdjusted = time.Now()

	r.audit.Log(audit.ActionRateLimit, backlog.Topic,
		"Topic-level throttle: %d%% → %d%%, rate %.2f → %.2f msg/s (heavy_subs=%d, medium_subs=%d)",
		oldLevel, newLevel, tl.baseRate, tl.currentRate, heavyCount, mediumCount)
}

func (r *RateLimiter) Allow(topic, subscription string) bool {
	r.mu.Lock()
	defer r.mu.Unlock()

	tl, exists := r.topics[topic]
	if !exists {
		return true
	}

	if subscription != "" {
		if sl, subExists := tl.subs[subscription]; subExists {
			if !sl.limiter.Allow() {
				return false
			}
		}
	}

	return true
}

func (r *RateLimiter) SetSubscriptionRateLimit(topic, subscription string, rateLimit float64) {
	r.mu.Lock()
	defer r.mu.Unlock()

	tl, exists := r.topics[topic]
	if !exists {
		tl = &topicLimiter{
			topicRate:   r.config.MaxRate,
			baseRate:    r.config.MaxRate,
			currentRate: r.config.MaxRate,
			level:       throttleNone,
			subs:        make(map[string]*subLimiter),
		}
		r.topics[topic] = tl
	}

	sl, exists := tl.subs[subscription]
	if !exists {
		sl = &subLimiter{
			limiter:     rate.NewLimiter(rate.Limit(rateLimit), int(rateLimit)),
			currentRate: rateLimit,
			baseRate:    rateLimit,
			level:       throttleNone,
		}
		tl.subs[subscription] = sl
	} else {
		sl.limiter.SetLimit(rate.Limit(rateLimit))
		sl.limiter.SetBurst(int(rateLimit))
		sl.currentRate = rateLimit
		sl.baseRate = rateLimit
		sl.level = throttleNone
	}

	r.audit.Log(audit.ActionManualRateLimit, topic,
		"Manually set subscription [%s] rate limit to %.2f msg/s", subscription, rateLimit)
}

func (r *RateLimiter) SetTopicRateLimit(topic string, rateLimit float64) {
	r.mu.Lock()
	defer r.mu.Unlock()

	tl, exists := r.topics[topic]
	if !exists {
		tl = &topicLimiter{
			topicRate:   rateLimit,
			baseRate:    rateLimit,
			currentRate: rateLimit,
			level:       throttleNone,
			subs:        make(map[string]*subLimiter),
		}
		r.topics[topic] = tl
	} else {
		tl.baseRate = rateLimit
		tl.currentRate = rateLimit
		tl.topicRate = rateLimit
		tl.level = throttleNone
	}

	r.audit.Log(audit.ActionManualRateLimit, topic,
		"Manually set topic-level rate limit to %.2f msg/s", rateLimit)
}

func (r *RateLimiter) SetRateLimit(topic string, rateLimit float64) {
	r.SetTopicRateLimit(topic, rateLimit)
}

func (r *RateLimiter) GetCurrentRate(topic string) float64 {
	r.mu.Lock()
	defer r.mu.Unlock()

	tl, exists := r.topics[topic]
	if !exists {
		return 0
	}
	return tl.currentRate
}

func (r *RateLimiter) GetSubscriptionRate(topic, subscription string) float64 {
	r.mu.Lock()
	defer r.mu.Unlock()

	tl, exists := r.topics[topic]
	if !exists {
		return 0
	}
	sl, subExists := tl.subs[subscription]
	if !subExists {
		return tl.currentRate
	}
	return sl.currentRate
}

func (r *RateLimiter) GetThrottleStatus(topic string) map[string]interface{} {
	r.mu.Lock()
	defer r.mu.Unlock()

	tl, exists := r.topics[topic]
	if !exists {
		return map[string]interface{}{
			"topic_rate":  0,
			"topic_level": throttleNone,
			"subscriptions": map[string]interface{}{},
		}
	}

	subs := make(map[string]interface{})
	for name, sl := range tl.subs {
		subs[name] = map[string]interface{}{
			"rate":  sl.currentRate,
			"level": sl.level,
		}
	}

	return map[string]interface{}{
		"topic_rate":    tl.currentRate,
		"topic_base":    tl.baseRate,
		"topic_level":   tl.level,
		"subscriptions": subs,
	}
}
