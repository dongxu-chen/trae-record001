package retry

import (
	"container/heap"
	"context"
	"redis-keyspace-notifier/config"
	"redis-keyspace-notifier/logger"
	"redis-keyspace-notifier/models"
	"sync"
	"time"

	"go.uber.org/zap"
)

type RetryItem struct {
	event     *models.KeyEvent
	retryAt   time.Time
	index     int
}

type RetryHeap []*RetryItem

func (h RetryHeap) Len() int           { return len(h) }
func (h RetryHeap) Less(i, j int) bool { return h[i].retryAt.Before(h[j].retryAt) }
func (h RetryHeap) Swap(i, j int) {
	h[i], h[j] = h[j], h[i]
	h[i].index = i
	h[j].index = j
}

func (h *RetryHeap) Push(x interface{}) {
	n := len(*h)
	item := x.(*RetryItem)
	item.index = n
	*h = append(*h, item)
}

func (h *RetryHeap) Pop() interface{} {
	old := *h
	n := len(old)
	item := old[n-1]
	old[n-1] = nil
	item.index = -1
	*h = old[0 : n-1]
	return item
}

type RetryQueue struct {
	heap           RetryHeap
	mu             sync.Mutex
	itemChan       chan *models.KeyEvent
	resultChan     chan *models.KeyEvent
	wg             sync.WaitGroup
	ctx            context.Context
	cancel         context.CancelFunc
	handler        func(*models.KeyEvent) error
	notifications  chan *models.KeyEvent
	baseDelay      time.Duration
	minDelay       time.Duration
	maxDelay       time.Duration
	targetQueueLen int
}

func NewRetryQueue(handler func(*models.KeyEvent) error) *RetryQueue {
	ctx, cancel := context.WithCancel(context.Background())
	return &RetryQueue{
		heap:           make(RetryHeap, 0),
		itemChan:       make(chan *models.KeyEvent, 1000),
		resultChan:     make(chan *models.KeyEvent, 1000),
		ctx:            ctx,
		cancel:         cancel,
		handler:        handler,
		notifications:  make(chan *models.KeyEvent, 100),
		baseDelay:      config.AppConfig.Retry.InitialDelay,
		minDelay:       100 * time.Millisecond,
		maxDelay:       config.AppConfig.Retry.MaxDelay,
		targetQueueLen: 100,
	}
}

func (q *RetryQueue) Start() {
	heap.Init(&q.heap)

	q.wg.Add(2)
	go q.processLoop()
	go q.retryLoop()
}

func (q *RetryQueue) Add(event *models.KeyEvent) {
	select {
	case q.itemChan <- event:
	default:
		logger.Warn("Retry queue full, dropping event",
			zap.String("event_id", event.ID),
			zap.String("key", event.Key))
	}
}

func (q *RetryQueue) processLoop() {
	defer q.wg.Done()

	for {
		select {
		case <-q.ctx.Done():
			return
		case event := <-q.itemChan:
			q.addToHeap(event)
		}
	}
}

func (q *RetryQueue) addToHeap(event *models.KeyEvent) {
	if !config.AppConfig.Retry.Enabled {
		return
	}

	if event.RetryCount >= config.AppConfig.Retry.MaxAttempts {
		logger.Warn("Max retry attempts reached",
			zap.String("event_id", event.ID),
			zap.String("key", event.Key),
			zap.Int("attempts", event.RetryCount))
		return
	}

	delay := q.calculateDelay(event.RetryCount)
	retryAt := time.Now().Add(delay)

	q.mu.Lock()
	heap.Push(&q.heap, &RetryItem{
		event:   event,
		retryAt: retryAt,
	})
	q.mu.Unlock()

	logger.Info("Event scheduled for retry",
		zap.String("event_id", event.ID),
		zap.String("key", event.Key),
		zap.Int("attempt", event.RetryCount+1),
		zap.Time("retry_at", retryAt))
}

func (q *RetryQueue) calculateDelay(retryCount int) time.Duration {
	queueLen := q.GetPendingCount()

	loadFactor := float64(queueLen) / float64(q.targetQueueLen)
	if loadFactor < 0.1 {
		loadFactor = 0.1
	}
	if loadFactor > 10 {
		loadFactor = 10
	}

	adjustedBaseDelay := time.Duration(float64(q.baseDelay) / loadFactor)
	if adjustedBaseDelay < q.minDelay {
		adjustedBaseDelay = q.minDelay
	}
	if adjustedBaseDelay > q.maxDelay {
		adjustedBaseDelay = q.maxDelay
	}

	delay := adjustedBaseDelay
	for i := 0; i < retryCount; i++ {
		delay = time.Duration(float64(delay) * config.AppConfig.Retry.BackoffFactor)
		if delay > q.maxDelay {
			delay = q.maxDelay
			break
		}
	}

	logger.Debug("Dynamic retry delay calculated",
		zap.Int("queue_len", queueLen),
		zap.Float64("load_factor", loadFactor),
		zap.Duration("base_delay", q.baseDelay),
		zap.Duration("adjusted_delay", adjustedBaseDelay),
		zap.Duration("final_delay", delay),
		zap.Int("retry_count", retryCount))

	return delay
}

func (q *RetryQueue) retryLoop() {
	defer q.wg.Done()

	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-q.ctx.Done():
			return
		case <-ticker.C:
			q.processDueItems()
		}
	}
}

func (q *RetryQueue) processDueItems() {
	q.mu.Lock()
	defer q.mu.Unlock()

	now := time.Now()

	for q.heap.Len() > 0 {
		item := q.heap[0]
		if item.retryAt.After(now) {
			break
		}

		heap.Pop(&q.heap)
		go q.retryItem(item)
	}
}

func (q *RetryQueue) retryItem(item *RetryItem) {
	item.event.RetryCount++

	logger.Info("Retrying event",
		zap.String("event_id", item.event.ID),
		zap.String("key", item.event.Key),
		zap.Int("attempt", item.event.RetryCount))

	if err := q.handler(item.event); err != nil {
		item.event.Error = err.Error()
		logger.Error("Retry failed",
			zap.String("event_id", item.event.ID),
			zap.String("key", item.event.Key),
			zap.Error(err))
		q.Add(item.event)
	} else {
		item.event.Processed = true
		item.event.Error = ""
		logger.Info("Retry succeeded",
			zap.String("event_id", item.event.ID),
			zap.String("key", item.event.Key))
	}

	select {
	case q.notifications <- item.event:
	default:
	}
}

func (q *RetryQueue) Stop() {
	q.cancel()
	q.wg.Wait()
}

func (q *RetryQueue) GetNotificationChannel() <-chan *models.KeyEvent {
	return q.notifications
}

func (q *RetryQueue) GetPendingCount() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return q.heap.Len()
}
