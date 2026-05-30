package notifier

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"heatcache/internal/binlog"
	"heatcache/internal/cache"
	"heatcache/internal/incremental"
)

type DataChangeNotifier struct {
	cacheLayer        *cache.RedisCache
	incrementalMgr    *incremental.IncrementalManager
	mysqlListeners    map[string]*binlog.BinlogListener
	pgListeners       map[string]*binlog.SimpleTriggerListener
	eventProcessors   []func(*binlog.BinlogEvent)
	ctx               context.Context
	cancel            context.CancelFunc
	wg                sync.WaitGroup
	mu                sync.RWMutex
	eventBuffer       chan *binlog.BinlogEvent
	invalidatedTables map[string]int
	processedEvents   int64
}

func NewDataChangeNotifier(
	cacheLayer *cache.RedisCache,
	incrementalMgr *incremental.IncrementalManager,
	bufferSize int,
) *DataChangeNotifier {
	if bufferSize <= 0 {
		bufferSize = 10000
	}

	return &DataChangeNotifier{
		cacheLayer:        cacheLayer,
		incrementalMgr:    incrementalMgr,
		mysqlListeners:    make(map[string]*binlog.BinlogListener),
		pgListeners:       make(map[string]*binlog.SimpleTriggerListener),
		eventProcessors:   make([]func(*binlog.BinlogEvent), 0),
		eventBuffer:       make(chan *binlog.BinlogEvent, bufferSize),
		invalidatedTables: make(map[string]int),
	}
}

func (dcn *DataChangeNotifier) AddMySQLListener(name string, config binlog.BinlogListenerConfig) error {
	listener, err := binlog.NewBinlogListener(config)
	if err != nil {
		return fmt.Errorf("failed to create mysql listener: %w", err)
	}

	listener.AddHandler(dcn.handleBinlogEvent)

	dcn.mu.Lock()
	dcn.mysqlListeners[name] = listener
	dcn.mu.Unlock()

	return nil
}

func (dcn *DataChangeNotifier) AddPGListener(name string, config binlog.PGReplicationConfig) {
	listener := binlog.NewSimpleTriggerListener(config)
	listener.AddHandler(dcn.handleBinlogEvent)

	dcn.mu.Lock()
	dcn.pgListeners[name] = listener
	dcn.mu.Unlock()
}

func (dcn *DataChangeNotifier) AddProcessor(processor func(*binlog.BinlogEvent)) {
	dcn.mu.Lock()
	defer dcn.mu.Unlock()
	dcn.eventProcessors = append(dcn.eventProcessors, processor)
}

func (dcn *DataChangeNotifier) Start(ctx context.Context) error {
	dcn.mu.Lock()
	dcn.ctx, dcn.cancel = context.WithCancel(ctx)
	dcn.mu.Unlock()

	for name, listener := range dcn.mysqlListeners {
		if err := listener.Start(dcn.ctx); err != nil {
			log.Printf("[notifier] failed to start mysql listener %s: %v", name, err)
		} else {
			log.Printf("[notifier] started mysql binlog listener: %s", name)
		}
	}

	for name, listener := range dcn.pgListeners {
		if err := listener.Start(dcn.ctx); err != nil {
			log.Printf("[notifier] failed to start pg listener %s: %v", name, err)
		} else {
			log.Printf("[notifier] started postgres replication listener: %s", name)
		}
	}

	dcn.wg.Add(1)
	go dcn.processEvents()

	return nil
}

func (dcn *DataChangeNotifier) Stop() {
	if dcn.cancel != nil {
		dcn.cancel()
	}

	for _, listener := range dcn.mysqlListeners {
		listener.Stop()
	}

	for _, listener := range dcn.pgListeners {
		listener.Stop()
	}

	close(dcn.eventBuffer)
	dcn.wg.Wait()
}

func (dcn *DataChangeNotifier) handleBinlogEvent(event *binlog.BinlogEvent) {
	select {
	case dcn.eventBuffer <- event:
	default:
		log.Printf("[notifier] event buffer full, dropping event on table %s", event.Table)
	}
}

func (dcn *DataChangeNotifier) processEvents() {
	defer dcn.wg.Done()

	for event := range dcn.eventBuffer {
		if dcn.ctx.Err() != nil {
			return
		}

		dcn.processSingleEvent(event)

		dcn.mu.RLock()
		processors := dcn.eventProcessors
		dcn.mu.RUnlock()

		for _, processor := range processors {
			processor(event)
		}
	}
}

func (dcn *DataChangeNotifier) processSingleEvent(event *binlog.BinlogEvent) {
	dcn.mu.Lock()
	dcn.processedEvents++
	dcn.mu.Unlock()

	if event.Table == "" {
		return
	}

	changeEvent := &incremental.TableChangeEvent{
		Table:       event.Table,
		Operation:   string(event.Type),
		Timestamp:   event.Timestamp,
		RowCount:    1,
		DbName:      event.Database,
	}

	if event.PrimaryKey != nil {
		changeEvent.AffectedPKs = []interface{}{event.PrimaryKey}
	}

	if len(event.ChangedCols) > 0 {
		changeEvent.AffectedCols = event.ChangedCols
	}

	marked := dcn.incrementalMgr.MarkDirtyByEvent(changeEvent)
	if marked > 0 {
		log.Printf("[notifier] marked %d queries dirty due to %s on %s",
			marked, event.Type, event.Table)
	}

	dcn.mu.Lock()
	dcn.invalidatedTables[event.Table]++
	dcn.mu.Unlock()

	if err := dcn.cacheLayer.InvalidateByTable(dcn.ctx, event.Table); err != nil {
		log.Printf("[notifier] failed to invalidate cache for table %s: %v", event.Table, err)
	}
}

func (dcn *DataChangeNotifier) GetStats() map[string]interface{} {
	dcn.mu.RLock()
	defer dcn.mu.RUnlock()

	stats := make(map[string]interface{})
	stats["processed_events"] = dcn.processedEvents
	stats["invalidated_tables"] = len(dcn.invalidatedTables)
	stats["mysql_listeners"] = len(dcn.mysqlListeners)
	stats["pg_listeners"] = len(dcn.pgListeners)
	stats["buffer_size"] = len(dcn.eventBuffer)

	tableCounts := make(map[string]int)
	for t, c := range dcn.invalidatedTables {
		tableCounts[t] = c
	}
	stats["table_invalidation_counts"] = tableCounts

	return stats
}

func (dcn *DataChangeNotifier) ResetStats() {
	dcn.mu.Lock()
	defer dcn.mu.Unlock()

	dcn.processedEvents = 0
	dcn.invalidatedTables = make(map[string]int)
}

func (dcn *DataChangeNotifier) ManuallyInvalidateTable(table string) int {
	changeEvent := &incremental.TableChangeEvent{
		Table:     table,
		Operation: "MANUAL",
		Timestamp: time.Now(),
		RowCount:  1,
	}

	marked := dcn.incrementalMgr.MarkDirtyByEvent(changeEvent)

	if dcn.ctx != nil {
		dcn.cacheLayer.InvalidateByTable(dcn.ctx, table)
	}

	return marked
}
