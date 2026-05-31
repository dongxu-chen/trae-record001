package priority

import (
	"sync"
	"time"

	"clickhouse-rate-limiter/config"
)

type Priority int

const (
	HighPriority   Priority = 3
	MediumPriority Priority = 2
	LowPriority    Priority = 1
)

type QueryRequest struct {
	ID        string
	UserID    string
	Query     string
	Priority  Priority
	Complexity float64
	Timestamp time.Time
	InsertPos int
	Result    chan *QueryResponse
}

type QueryResponse struct {
	Data     interface{}
	Error    error
	Status   string
	Duration time.Duration
}

type queueNode struct {
	req  *QueryRequest
	next *queueNode
	prev *queueNode
}

type PriorityQueue struct {
	config        config.PriorityConfig
	head          *queueNode
	tail          *queueNode
	size          int
	requests      map[string]*queueNode
	highCount     int
	mediumCount   int
	lowCount      int
	preemptCount  int
	mu            sync.Mutex
	cond          *sync.Cond
	closed        bool
}

func NewPriorityQueue(cfg config.PriorityConfig) *PriorityQueue {
	pq := &PriorityQueue{
		config:   cfg,
		requests: make(map[string]*queueNode),
		closed:   false,
	}
	pq.cond = sync.NewCond(&pq.mu)

	return pq
}

func (pq *PriorityQueue) Submit(req *QueryRequest) error {
	pq.mu.Lock()
	defer pq.mu.Unlock()

	if pq.closed {
		return &QueueClosedError{}
	}

	if pq.size >= pq.config.QueueSize {
		if !pq.evictLowPriority() {
			return &QueueFullError{}
		}
	}

	req.Timestamp = time.Now()
	req.Result = make(chan *QueryResponse, 1)

	node := &queueNode{req: req}

	insertPos := pq.calculateInsertPosition(req)
	node.req.InsertPos = insertPos
	pq.insertAtPosition(node, insertPos)

	pq.requests[req.ID] = node
	pq.size++

	switch req.Priority {
	case HighPriority:
		pq.highCount++
		if insertPos < pq.size-1 {
			pq.preemptCount++
		}
	case MediumPriority:
		pq.mediumCount++
	case LowPriority:
		pq.lowCount++
	}

	pq.cond.Signal()

	return nil
}

func (pq *PriorityQueue) calculateInsertPosition(req *QueryRequest) int {
	if pq.size == 0 {
		return 0
	}

	switch req.Priority {
	case HighPriority:
		return pq.findHighPriorityInsertPos()
	case MediumPriority:
		return pq.findMediumPriorityInsertPos()
	case LowPriority:
		return pq.size
	default:
		return pq.size
	}
}

func (pq *PriorityQueue) findHighPriorityInsertPos() int {
	pos := 0
	current := pq.head

	for current != nil && current.req != nil {
		if current.req.Priority >= HighPriority {
			pos++
		} else {
			break
		}
		current = current.next
	}

	if pos > 0 {
		return pos
	}
	return 0
}

func (pq *PriorityQueue) findMediumPriorityInsertPos() int {
	pos := 0
	current := pq.head

	for current != nil && current.req != nil {
		if current.req.Priority >= MediumPriority {
			pos++
		} else {
			break
		}
		current = current.next
	}

	return pos
}

func (pq *PriorityQueue) insertAtPosition(node *queueNode, pos int) {
	if pq.size == 0 {
		pq.head = node
		pq.tail = node
		return
	}

	if pos == 0 {
		node.next = pq.head
		pq.head.prev = node
		pq.head = node
		return
	}

	if pos >= pq.size {
		node.prev = pq.tail
		pq.tail.next = node
		pq.tail = node
		return
	}

	current := pq.head
	for i := 0; i < pos && current != nil; i++ {
		current = current.next
	}

	if current != nil {
		node.prev = current.prev
		node.next = current
		if current.prev != nil {
			current.prev.next = node
		}
		current.prev = node
	}
}

func (pq *PriorityQueue) evictLowPriority() bool {
	current := pq.tail

	for current != nil {
		if current.req.Priority == LowPriority {
			pq.removeNode(current)
			return true
		}
		current = current.prev
	}

	current = pq.tail
	for current != nil {
		if current.req.Priority == MediumPriority {
			pq.removeNode(current)
			return true
		}
		current = current.prev
	}

	return false
}

func (pq *PriorityQueue) removeNode(node *queueNode) {
	if node.prev != nil {
		node.prev.next = node.next
	} else {
		pq.head = node.next
	}

	if node.next != nil {
		node.next.prev = node.prev
	} else {
		pq.tail = node.prev
	}

	switch node.req.Priority {
	case HighPriority:
		pq.highCount--
	case MediumPriority:
		pq.mediumCount--
	case LowPriority:
		pq.lowCount--
	}

	delete(pq.requests, node.req.ID)
	close(node.req.Result)
	pq.size--
}

func (pq *PriorityQueue) Next() (*QueryRequest, bool) {
	pq.mu.Lock()
	defer pq.mu.Unlock()

	for pq.size == 0 && !pq.closed {
		pq.cond.Wait()
	}

	if pq.closed && pq.size == 0 {
		return nil, false
	}

	if pq.head == nil {
		return nil, false
	}

	node := pq.head
	pq.head = node.next
	if pq.head != nil {
		pq.head.prev = nil
	} else {
		pq.tail = nil
	}

	switch node.req.Priority {
	case HighPriority:
		pq.highCount--
	case MediumPriority:
		pq.mediumCount--
	case LowPriority:
		pq.lowCount--
	}

	delete(pq.requests, node.req.ID)
	pq.size--

	return node.req, true
}

func (pq *PriorityQueue) Preempt(requestID string) bool {
	pq.mu.Lock()
	defer pq.mu.Unlock()

	node, exists := pq.requests[requestID]
	if !exists {
		return false
	}

	if node == pq.head {
		return true
	}

	if node.prev != nil {
		node.prev.next = node.next
	}
	if node.next != nil {
		node.next.prev = node.prev
	}
	if node == pq.tail {
		pq.tail = node.prev
	}

	node.prev = nil
	node.next = pq.head
	if pq.head != nil {
		pq.head.prev = node
	}
	pq.head = node

	pq.preemptCount++
	node.req.InsertPos = 0

	pq.cond.Signal()

	return true
}

func (pq *PriorityQueue) Cancel(requestID string) bool {
	pq.mu.Lock()
	defer pq.mu.Unlock()

	node, exists := pq.requests[requestID]
	if !exists {
		return false
	}

	pq.removeNode(node)
	return true
}

func (pq *PriorityQueue) Size() int {
	pq.mu.Lock()
	defer pq.mu.Unlock()
	return pq.size
}

func (pq *PriorityQueue) Close() {
	pq.mu.Lock()
	defer pq.mu.Unlock()

	pq.closed = true
	pq.cond.Broadcast()

	for _, node := range pq.requests {
		close(node.req.Result)
	}
}

func (pq *PriorityQueue) GetMetrics() map[string]interface{} {
	pq.mu.Lock()
	defer pq.mu.Unlock()

	return map[string]interface{}{
		"total":         pq.size,
		"high":          pq.highCount,
		"medium":        pq.mediumCount,
		"low":           pq.lowCount,
		"max_size":      pq.config.QueueSize,
		"is_closed":     pq.closed,
		"preempt_count": pq.preemptCount,
	}
}

func (pq *PriorityQueue) GetQueueOrder() []map[string]interface{} {
	pq.mu.Lock()
	defer pq.mu.Unlock()

	result := make([]map[string]interface{}, 0, pq.size)
	current := pq.head
	position := 0

	for current != nil {
		result = append(result, map[string]interface{}{
			"position":   position,
			"id":         current.req.ID,
			"priority":   current.req.Priority,
			"user_id":    current.req.UserID,
			"insert_pos": current.req.InsertPos,
			"timestamp":  current.req.Timestamp,
			"preempted":  current.req.InsertPos < position,
		})
		current = current.next
		position++
	}

	return result
}

type QueueFullError struct{}

func (e *QueueFullError) Error() string {
	return "priority queue is full"
}

type QueueClosedError struct{}

func (e *QueueClosedError) Error() string {
	return "priority queue is closed"
}

func ParsePriority(p string) Priority {
	switch p {
	case "high":
		return HighPriority
	case "medium":
		return MediumPriority
	case "low":
		return LowPriority
	default:
		return MediumPriority
	}
}
