package pool

import (
	"context"
	"sync"
	"sync/atomic"
	"time"
	"health-check/internal/model"
)

type ProbeTask struct {
	Endpoint *model.Endpoint
	Result   chan *model.ProbeResult
}

type ProbeFunc func(ctx context.Context, endpoint *model.Endpoint) *model.ProbeResult

type ProbePool struct {
	mu          sync.RWMutex
	minWorkers  int
	maxWorkers  int
	activeWorkers int64
	queueSize   int
	taskQueue   chan *ProbeTask
	probeFunc   ProbeFunc
	workers     []*worker
	stopChan    chan struct{}
	wg          sync.WaitGroup
	started     bool
}

type worker struct {
	id     int
	pool   *ProbePool
	stop   chan struct{}
	active int32
}

func New(minWorkers, maxWorkers, queueSize int, probeFunc ProbeFunc) *ProbePool {
	if minWorkers <= 0 {
		minWorkers = 5
	}
	if maxWorkers < minWorkers {
		maxWorkers = minWorkers * 2
	}
	if queueSize <= 0 {
		queueSize = 1000
	}

	return &ProbePool{
		minWorkers: minWorkers,
		maxWorkers: maxWorkers,
		queueSize:  queueSize,
		taskQueue:  make(chan *ProbeTask, queueSize),
		probeFunc:  probeFunc,
		workers:    make([]*worker, 0, maxWorkers),
		stopChan:   make(chan struct{}),
	}
}

func (p *ProbePool) Start() {
	p.mu.Lock()
	defer p.mu.Unlock()

	if p.started {
		return
	}
	p.started = true

	for i := 0; i < p.minWorkers; i++ {
		p.spawnWorker(i)
	}

	go p.monitor()
}

func (p *ProbePool) spawnWorker(id int) {
	w := &worker{
		id:   id,
		pool: p,
		stop: make(chan struct{}),
	}

	p.workers = append(p.workers, w)
	p.wg.Add(1)
	atomic.AddInt64(&p.activeWorkers, 1)

	go func() {
		defer p.wg.Done()
		defer atomic.AddInt64(&p.activeWorkers, -1)

		for {
			select {
			case task, ok := <-p.taskQueue:
				if !ok {
					return
				}
				atomic.StoreInt32(&w.active, 1)
				ctx, cancel := context.WithTimeout(context.Background(), time.Duration(task.Endpoint.Timeout)*time.Second)
				result := p.probeFunc(ctx, task.Endpoint)
				cancel()
				task.Result <- result
				atomic.StoreInt32(&w.active, 0)
			case <-w.stop:
				return
			}
		}
	}()
}

func (p *ProbePool) monitor() {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			p.adjustWorkers()
		case <-p.stopChan:
			return
		}
	}
}

func (p *ProbePool) adjustWorkers() {
	p.mu.Lock()
	defer p.mu.Unlock()

	queueLen := len(p.taskQueue)
	activeWorkers := atomic.LoadInt64(&p.activeWorkers)
	currentWorkers := len(p.workers)

	if queueLen > currentWorkers/2 && currentWorkers < p.maxWorkers {
		newCount := min(currentWorkers+5, p.maxWorkers)
		for i := currentWorkers; i < newCount; i++ {
			p.spawnWorker(i)
		}
	} else if queueLen == 0 && currentWorkers > p.minWorkers && activeWorkers < int64(currentWorkers)/2 {
		removeCount := min(currentWorkers-p.minWorkers, 5)
		for i := 0; i < removeCount; i++ {
			if len(p.workers) > p.minWorkers {
				w := p.workers[len(p.workers)-1]
				close(w.stop)
				p.workers = p.workers[:len(p.workers)-1]
			}
		}
	}
}

func (p *ProbePool) Submit(endpoint *model.Endpoint) chan *model.ProbeResult {
	resultChan := make(chan *model.ProbeResult, 1)

	task := &ProbeTask{
		Endpoint: endpoint,
		Result:   resultChan,
	}

	select {
	case p.taskQueue <- task:
	default:
		result := &model.ProbeResult{
			EndpointID: endpoint.ID,
			Name:       endpoint.Name,
			Protocol:   endpoint.Protocol,
			Timestamp:  time.Now(),
			Status:     model.StatusDown,
			Error:      "probe pool queue is full",
		}
		resultChan <- result
	}

	return resultChan
}

func (p *ProbePool) Stop() {
	p.mu.Lock()
	defer p.mu.Unlock()

	if !p.started {
		return
	}
	p.started = false

	close(p.stopChan)

	for _, w := range p.workers {
		close(w.stop)
	}

	p.wg.Wait()
	close(p.taskQueue)
}

func (p *ProbePool) Stats() (activeWorkers int64, queueLength int, totalWorkers int) {
	p.mu.RLock()
	defer p.mu.RUnlock()

	return atomic.LoadInt64(&p.activeWorkers), len(p.taskQueue), len(p.workers)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
