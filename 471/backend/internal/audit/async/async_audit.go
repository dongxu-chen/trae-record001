package async

import (
	"context"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
	"gorm.io/gorm"

	"github.com/keymgmt/service/backend/internal/models"
)

type AsyncAuditService struct {
	db         *gorm.DB
	log        *logrus.Logger
	queue      chan *models.AuditLog
	bufferSize int
	batchSize  int
	flushInterval time.Duration
	wg         sync.WaitGroup
	ctx        context.Context
	cancel     context.CancelFunc
	metrics    *Metrics
}

type Metrics struct {
	TotalReceived   int64
	TotalWritten    int64
	TotalDropped    int64
	CurrentQueueLen int
	mu              sync.Mutex
}

type Config struct {
	BufferSize    int
	BatchSize     int
	FlushInterval time.Duration
}

func DefaultConfig() Config {
	return Config{
		BufferSize:    10000,
		BatchSize:     100,
		FlushInterval: 5 * time.Second,
	}
}

func NewAsyncAuditService(db *gorm.DB, log *logrus.Logger, cfg Config) *AsyncAuditService {
	if cfg.BufferSize == 0 {
		cfg.BufferSize = 10000
	}
	if cfg.BatchSize == 0 {
		cfg.BatchSize = 100
	}
	if cfg.FlushInterval == 0 {
		cfg.FlushInterval = 5 * time.Second
	}

	ctx, cancel := context.WithCancel(context.Background())

	return &AsyncAuditService{
		db:         db,
		log:        log,
		queue:      make(chan *models.AuditLog, cfg.BufferSize),
		bufferSize: cfg.BufferSize,
		batchSize:  cfg.BatchSize,
		flushInterval: cfg.FlushInterval,
		ctx:        ctx,
		cancel:     cancel,
		metrics:    &Metrics{},
	}
}

func (s *AsyncAuditService) Start() {
	s.wg.Add(1)
	go s.run()

	s.wg.Add(1)
	go s.metricsReporter()

	s.log.Infof("Async audit service started with buffer=%d, batch=%d, interval=%v",
		s.bufferSize, s.batchSize, s.flushInterval)
}

func (s *AsyncAuditService) Stop() {
	s.log.Info("Stopping async audit service...")
	s.cancel()
	close(s.queue)
	s.wg.Wait()
	s.log.Info("Async audit service stopped")
}

func (s *AsyncAuditService) Log(entry *models.AuditLog) {
	s.metrics.mu.Lock()
	s.metrics.TotalReceived++
	s.metrics.mu.Unlock()

	select {
	case s.queue <- entry:
	default:
		s.metrics.mu.Lock()
		s.metrics.TotalDropped++
		s.metrics.mu.Unlock()
		s.log.Warnf("Audit queue full, dropping entry: action=%s, secret=%s", entry.Action, entry.SecretID)
	}
}

func (s *AsyncAuditService) run() {
	defer s.wg.Done()

	batch := make([]*models.AuditLog, 0, s.batchSize)
	ticker := time.NewTicker(s.flushInterval)
	defer ticker.Stop()

	for {
		select {
		case entry, ok := <-s.queue:
			if !ok {
				s.flush(batch)
				return
			}
			batch = append(batch, entry)
			if len(batch) >= s.batchSize {
				s.flush(batch)
				batch = batch[:0]
			}
		case <-ticker.C:
			if len(batch) > 0 {
				s.flush(batch)
				batch = batch[:0]
			}
		case <-s.ctx.Done():
			remaining := len(s.queue)
			if remaining > 0 {
				s.log.Infof("Flushing remaining %d audit entries before shutdown", remaining)
				for entry := range s.queue {
					batch = append(batch, entry)
					if len(batch) >= s.batchSize {
						s.flush(batch)
						batch = batch[:0]
					}
					remaining--
					if remaining == 0 {
						break
					}
				}
				s.flush(batch)
			}
			return
		}
	}
}

func (s *AsyncAuditService) flush(batch []*models.AuditLog) {
	if len(batch) == 0 {
		return
	}

	start := time.Now()
	tx := s.db.CreateInBatches(batch, s.batchSize)
	if tx.Error != nil {
		s.log.Errorf("Failed to write audit batch: %v, entries=%d", tx.Error, len(batch))
		return
	}

	duration := time.Since(start)
	written := len(batch)

	s.metrics.mu.Lock()
	s.metrics.TotalWritten += int64(written)
	s.metrics.CurrentQueueLen = len(s.queue)
	s.metrics.mu.Unlock()

	s.log.Debugf("Audit batch flushed: entries=%d, duration=%v", written, duration)
}

func (s *AsyncAuditService) metricsReporter() {
	defer s.wg.Done()

	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			s.metrics.mu.Lock()
			s.log.Infof("Audit metrics - received=%d, written=%d, dropped=%d, queue_len=%d",
				s.metrics.TotalReceived, s.metrics.TotalWritten, s.metrics.TotalDropped, len(s.queue))
			s.metrics.mu.Unlock()
		case <-s.ctx.Done():
			return
		}
	}
}

func (s *AsyncAuditService) GetMetrics() Metrics {
	s.metrics.mu.Lock()
	defer s.metrics.mu.Unlock()
	return Metrics{
		TotalReceived:   s.metrics.TotalReceived,
		TotalWritten:    s.metrics.TotalWritten,
		TotalDropped:    s.metrics.TotalDropped,
		CurrentQueueLen: len(s.queue),
	}
}

type AuditEntry struct {
	SecretID  string
	Action    string
	User      string
	IPAddress string
	UserAgent string
	Success   bool
	Message   string
}

func (s *AsyncAuditService) LogEntry(entry AuditEntry) {
	auditLog := &models.AuditLog{
		Action:    entry.Action,
		User:      entry.User,
		IPAddress: entry.IPAddress,
		UserAgent: entry.UserAgent,
		Success:   entry.Success,
		Message:   entry.Message,
		CreatedAt: time.Now(),
	}

	if entry.SecretID != "" {
		if uid, err := parseUUID(entry.SecretID); err == nil {
			auditLog.SecretID = uid
		}
	}

	s.Log(auditLog)
}

func parseUUID(s string) (uuid.UUID, error) {
	return uuid.Parse(s)
}
