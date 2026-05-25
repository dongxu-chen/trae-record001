package resource

import (
	"context"
	"fmt"
	"log"
	"sync"
	"sync/atomic"
	"time"

	"scheduler/internal/models"
	"scheduler/internal/queue"
)

type TaskFunc func(ctx context.Context) error

type ResourcePool struct {
	Name            string
	WorkerCount     int
	MaxWorkerCount  int
	RunningTasks    int64
	QueuedTasks     int64
	CPUQuota        int
	MemoryQuotaMB   int
	taskQueue       chan *PoolTask
	workerTokens    chan struct{}
	wg              sync.WaitGroup
	ctx             context.Context
	cancel          context.CancelFunc
	mu              sync.RWMutex
}

type PoolTask struct {
	TaskID     string
	Resource   string
	Priority   int
	TaskFunc   TaskFunc
	SubmittedAt time.Time
}

type PoolManager struct {
	pools   map[string]*ResourcePool
	mu      sync.RWMutex
	queue   *queue.RedisQueue
}

func NewPoolManager(queue *queue.RedisQueue) *PoolManager {
	return &PoolManager{
		pools: make(map[string]*ResourcePool),
		queue: queue,
	}
}

func (pm *PoolManager) CreatePool(name string, workerCount, maxWorkerCount, cpuQuota, memQuota int) (*ResourcePool, error) {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	if _, exists := pm.pools[name]; exists {
		return nil, fmt.Errorf("pool %s already exists", name)
	}

	ctx, cancel := context.WithCancel(context.Background())

	pool := &ResourcePool{
		Name:           name,
		WorkerCount:    workerCount,
		MaxWorkerCount: maxWorkerCount,
		CPUQuota:       cpuQuota,
		MemoryQuotaMB:  memQuota,
		taskQueue:      make(chan *PoolTask, 10000),
		workerTokens:   make(chan struct{}, maxWorkerCount),
		ctx:            ctx,
		cancel:         cancel,
	}

	pm.pools[name] = pool

	for i := 0; i < workerCount; i++ {
		pool.workerTokens <- struct{}{}
	}

	go pool.run()

	log.Printf("Resource pool %s created with %d workers", name, workerCount)
	return pool, nil
}

func (pm *PoolManager) GetPool(name string) (*ResourcePool, bool) {
	pm.mu.RLock()
	defer pm.mu.RUnlock()
	pool, exists := pm.pools[name]
	return pool, exists
}

func (pm *PoolManager) RemovePool(name string) {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	if pool, exists := pm.pools[name]; exists {
		pool.Shutdown()
		delete(pm.pools, name)
		log.Printf("Resource pool %s removed", name)
	}
}

func (pm *PoolManager) GetAllPools() []*models.ResourcePool {
	pm.mu.RLock()
	defer pm.mu.RUnlock()

	var result []*models.ResourcePool
	for name, pool := range pm.pools {
		pool.mu.RLock()
		result = append(result, &models.ResourcePool{
			Name:           name,
			WorkerCount:    pool.WorkerCount,
			MaxWorkerCount: pool.MaxWorkerCount,
			RunningTasks:   int(atomic.LoadInt64(&pool.RunningTasks)),
			QueuedTasks:    int(atomic.LoadInt64(&pool.QueuedTasks)),
			CPUQuota:       pool.CPUQuota,
			MemoryQuotaMB:  pool.MemoryQuotaMB,
		})
		pool.mu.RUnlock()
	}
	return result
}

func (pm *PoolManager) SubmitTask(poolName string, task *PoolTask) error {
	pool, exists := pm.GetPool(poolName)
	if !exists {
		return fmt.Errorf("pool %s not found", poolName)
	}

	select {
	case pool.taskQueue <- task:
		atomic.AddInt64(&pool.QueuedTasks, 1)
		return nil
	default:
		return fmt.Errorf("pool %s task queue is full", poolName)
	}
}

func (pm *PoolManager) AutoScale() {
	pm.mu.RLock()
	defer pm.mu.RUnlock()

	for _, pool := range pm.pools {
		running := atomic.LoadInt64(&pool.RunningTasks)
		queued := atomic.LoadInt64(&pool.QueuedTasks)

		if queued > running*2 && pool.WorkerCount < pool.MaxWorkerCount {
			pool.ScaleUp(1)
		} else if running < int64(pool.WorkerCount)/2 && pool.WorkerCount > 5 {
			pool.ScaleDown(1)
		}
	}
}

func (p *ResourcePool) run() {
	for {
		select {
		case <-p.ctx.Done():
			return
		case task := <-p.taskQueue:
			atomic.AddInt64(&p.QueuedTasks, -1)

			select {
			case <-p.workerTokens:
				p.wg.Add(1)
				go p.executeTask(task)
			default:
				go func(t *PoolTask) {
					select {
					case <-p.workerTokens:
						p.wg.Add(1)
						p.executeTask(t)
					case <-p.ctx.Done():
					}
				}(task)
			}
		}
	}
}

func (p *ResourcePool) executeTask(task *PoolTask) {
	defer func() {
		p.workerTokens <- struct{}{}
		p.wg.Done()
		atomic.AddInt64(&p.RunningTasks, -1)

		if r := recover(); r != nil {
			log.Printf("Task %s in pool %s panicked: %v", task.TaskID, p.Name, r)
		}
	}()

	atomic.AddInt64(&p.RunningTasks, 1)

	ctx, cancel := context.WithTimeout(p.ctx, 1*time.Hour)
	defer cancel()

	waitDuration := time.Since(task.SubmittedAt)
	if waitDuration > 5*time.Second {
		log.Printf("Task %s waited %v in pool %s queue", task.TaskID, waitDuration, p.Name)
	}

	if err := task.TaskFunc(ctx); err != nil {
		log.Printf("Task %s in pool %s failed: %v", task.TaskID, p.Name, err)
	}
}

func (p *ResourcePool) ScaleUp(workers int) {
	p.mu.Lock()
	defer p.mu.Unlock()

	newCount := p.WorkerCount + workers
	if newCount > p.MaxWorkerCount {
		newCount = p.MaxWorkerCount
	}

	added := newCount - p.WorkerCount
	for i := 0; i < added; i++ {
		select {
		case p.workerTokens <- struct{}{}:
			p.WorkerCount++
		default:
			break
		}
	}

	if added > 0 {
		log.Printf("Pool %s scaled up to %d workers", p.Name, p.WorkerCount)
	}
}

func (p *ResourcePool) ScaleDown(workers int) {
	p.mu.Lock()
	defer p.mu.Unlock()

	newCount := p.WorkerCount - workers
	if newCount < 1 {
		newCount = 1
	}

	removed := p.WorkerCount - newCount
	for i := 0; i < removed; i++ {
		select {
		case <-p.workerTokens:
			p.WorkerCount--
		default:
			break
		}
	}

	if removed > 0 {
		log.Printf("Pool %s scaled down to %d workers", p.Name, p.WorkerCount)
	}
}

func (p *ResourcePool) Shutdown() {
	p.cancel()
	p.wg.Wait()
	close(p.taskQueue)
	log.Printf("Resource pool %s shutdown complete", p.Name)
}

func (p *ResourcePool) GetStats() map[string]interface{} {
	p.mu.RLock()
	defer p.mu.RUnlock()

	running := atomic.LoadInt64(&p.RunningTasks)
	queued := atomic.LoadInt64(&p.QueuedTasks)
	utilization := float64(running) / float64(p.WorkerCount) * 100

	var status string
	switch {
	case utilization > 90:
		status = "high"
	case utilization > 70:
		status = "medium"
	case utilization > 30:
		status = "normal"
	default:
		status = "low"
	}

	return map[string]interface{}{
		"name":             p.Name,
		"worker_count":     p.WorkerCount,
		"max_workers":      p.MaxWorkerCount,
		"running_tasks":    running,
		"queued_tasks":     queued,
		"cpu_quota":        p.CPUQuota,
		"memory_quota_mb":  p.MemoryQuotaMB,
		"utilization_pct":  utilization,
		"status":           status,
	}
}

func (pm *PoolManager) ShutdownAll() {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	for name, pool := range pm.pools {
		pool.Shutdown()
		delete(pm.pools, name)
	}
	log.Println("All resource pools shutdown")
}
