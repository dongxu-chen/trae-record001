package processor

import (
	"container/heap"
	"redis-keyspace-notifier/models"
	"sync"
	"time"
)

type SortedEventItem struct {
	event     models.KeyEvent
	timestamp time.Time
	index     int
}

type SortedEventHeap []*SortedEventItem

func (h SortedEventHeap) Len() int { return len(h) }
func (h SortedEventHeap) Less(i, j int) bool {
	return h[i].timestamp.Before(h[j].timestamp)
}
func (h SortedEventHeap) Swap(i, j int) {
	h[i], h[j] = h[j], h[i]
	h[i].index = i
	h[j].index = j
}

func (h *SortedEventHeap) Push(x interface{}) {
	n := len(*h)
	item := x.(*SortedEventItem)
	item.index = n
	*h = append(*h, item)
}

func (h *SortedEventHeap) Pop() interface{} {
	old := *h
	n := len(old)
	item := old[n-1]
	old[n-1] = nil
	item.index = -1
	*h = old[0 : n-1]
	return item
}

type SortedEventQueue struct {
	heap       SortedEventHeap
	mu         sync.Mutex
	eventChan  <-chan models.KeyEvent
	outputChan chan models.KeyEvent
	wg         sync.WaitGroup
	bufferTime time.Duration
	maxSize    int
}

func NewSortedEventQueue(eventChan <-chan models.KeyEvent, bufferTime time.Duration, maxSize int) *SortedEventQueue {
	return &SortedEventQueue{
		heap:       make(SortedEventHeap, 0),
		eventChan:  eventChan,
		outputChan: make(chan models.KeyEvent, maxSize),
		bufferTime: bufferTime,
		maxSize:    maxSize,
	}
}

func (q *SortedEventQueue) Start() {
	heap.Init(&q.heap)
	q.wg.Add(2)
	go q.collectLoop()
	go q.dispatchLoop()
}

func (q *SortedEventQueue) collectLoop() {
	defer q.wg.Done()

	for event := range q.eventChan {
		q.mu.Lock()
		if q.heap.Len() >= q.maxSize {
			q.dispatchOldestLocked()
		}
		heap.Push(&q.heap, &SortedEventItem{
			event:     event,
			timestamp: event.Timestamp,
		})
		q.mu.Unlock()
	}
}

func (q *SortedEventQueue) dispatchLoop() {
	defer q.wg.Done()

	ticker := time.NewTicker(q.bufferTime)
	defer ticker.Stop()

	for range ticker.C {
		q.mu.Lock()
		for q.heap.Len() > 0 {
			q.dispatchOldestLocked()
		}
		q.mu.Unlock()
	}
}

func (q *SortedEventQueue) dispatchOldestLocked() {
	if q.heap.Len() == 0 {
		return
	}

	item := heap.Pop(&q.heap).(*SortedEventItem)
	select {
	case q.outputChan <- item.event:
	default:
	}
}

func (q *SortedEventQueue) OutputChan() <-chan models.KeyEvent {
	return q.outputChan
}

func (q *SortedEventQueue) Stop() {
	close(q.outputChan)
	q.wg.Wait()
}

func (q *SortedEventQueue) GetPendingCount() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return q.heap.Len()
}
