package binlog

import (
	"context"
	"database/sql"
	"fmt"
	"sync"
	"time"

	"github.com/lib/pq"
)

type PGReplicationConfig struct {
	Host        string
	Port        int
	User        string
	Password    string
	Database    string
	SlotName    string
	Publication string
	Tables      []string
}

type PGReplicationListener struct {
	config    PGReplicationConfig
	db        *sql.DB
	conn      *sql.Conn
	handlers  []func(*BinlogEvent)
	eventChan chan *BinlogEvent
	ctx       context.Context
	cancel    context.CancelFunc
	running   bool
	mu        sync.RWMutex
	lsn       string
}

func NewPGReplicationListener(config PGReplicationConfig) *PGReplicationListener {
	if config.SlotName == "" {
		config.SlotName = "heatcache_slot"
	}
	if config.Publication == "" {
		config.Publication = "heatcache_pub"
	}

	return &PGReplicationListener{
		config:    config,
		handlers:  make([]func(*BinlogEvent), 0),
		eventChan: make(chan *BinlogEvent, 10000),
	}
}

func (pg *PGReplicationListener) AddHandler(handler func(*BinlogEvent)) {
	pg.mu.Lock()
	defer pg.mu.Unlock()
	pg.handlers = append(pg.handlers, handler)
}

func (pg *PGReplicationListener) Events() <-chan *BinlogEvent {
	return pg.eventChan
}

func (pg *PGReplicationListener) Start(ctx context.Context) error {
	pg.mu.Lock()
	if pg.running {
		pg.mu.Unlock()
		return fmt.Errorf("already running")
	}
	pg.ctx, pg.cancel = context.WithCancel(ctx)
	pg.running = true
	pg.mu.Unlock()

	connStr := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable replication=database",
		pg.config.Host, pg.config.Port, pg.config.User, pg.config.Password, pg.config.Database)

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return fmt.Errorf("failed to open connection: %w", err)
	}
	pg.db = db

	conn, err := db.Conn(ctx)
	if err != nil {
		return fmt.Errorf("failed to acquire connection: %w", err)
	}
	pg.conn = conn

	if err := pg.ensureReplicationSlot(); err != nil {
		return fmt.Errorf("failed to ensure replication slot: %w", err)
	}

	if err := pg.ensurePublication(); err != nil {
		return fmt.Errorf("failed to ensure publication: %w", err)
	}

	go pg.runReplication()

	return nil
}

func (pg *PGReplicationListener) ensureReplicationSlot() error {
	var slotName string
	err := pg.db.QueryRowContext(pg.ctx,
		"SELECT slot_name FROM pg_replication_slots WHERE slot_name = $1",
		pg.config.SlotName,
	).Scan(&slotName)

	if err == sql.ErrNoRows {
		_, err := pg.db.ExecContext(pg.ctx,
			fmt.Sprintf("CREATE_REPLICATION_SLOT %s LOGICAL pgoutput",
				pq.QuoteIdentifier(pg.config.SlotName)))
		if err != nil {
			return fmt.Errorf("failed to create replication slot: %w", err)
		}
	} else if err != nil {
		return fmt.Errorf("failed to check replication slot: %w", err)
	}

	return nil
}

func (pg *PGReplicationListener) ensurePublication() error {
	var pubName string
	err := pg.db.QueryRowContext(pg.ctx,
		"SELECT pubname FROM pg_publication WHERE pubname = $1",
		pg.config.Publication,
	).Scan(&pubName)

	if err == sql.ErrNoRows {
		tablesClause := ""
		if len(pg.config.Tables) > 0 {
			tablesClause = " FOR TABLE "
			for i, tbl := range pg.config.Tables {
				if i > 0 {
					tablesClause += ", "
				}
				tablesClause += tbl
			}
		}
		_, err := pg.db.ExecContext(pg.ctx,
			fmt.Sprintf("CREATE PUBLICATION %s %s",
				pq.QuoteIdentifier(pg.config.Publication),
				tablesClause))
		if err != nil {
			return fmt.Errorf("failed to create publication: %w", err)
		}
	} else if err != nil {
		return fmt.Errorf("failed to check publication: %w", err)
	}

	return nil
}

func (pg *PGReplicationListener) runReplication() {
	defer func() {
		pg.mu.Lock()
		pg.running = false
		pg.mu.Unlock()
		close(pg.eventChan)
		if pg.conn != nil {
			pg.conn.Close()
		}
		if pg.db != nil {
			pg.db.Close()
		}
	}()

	query := fmt.Sprintf("START_REPLICATION SLOT %s LOGICAL 0/0 (proto_version '1', publication_names '%s')",
		pq.QuoteIdentifier(pg.config.SlotName),
		pg.config.Publication)

	rows, err := pg.db.QueryContext(pg.ctx, query)
	if err != nil {
		_ = fmt.Sprintf("failed to start replication: %v", err)
		return
	}
	defer rows.Close()

	for rows.Next() {
		select {
		case <-pg.ctx.Done():
			return
		default:
			var data []byte
			var lsn string
			if err := rows.Scan(&lsn, &data); err != nil {
				_ = fmt.Sprintf("failed to scan replication message: %v", err)
				continue
			}

			pg.mu.Lock()
			pg.lsn = lsn
			pg.mu.Unlock()

			events, err := pg.parsePGOutput(data)
			if err != nil {
				_ = fmt.Sprintf("failed to parse pglogical message: %v", err)
				continue
			}

			for _, event := range events {
				pg.dispatch(event)
			}
		}
	}
}

func (pg *PGReplicationListener) parsePGOutput(data []byte) ([]*BinlogEvent, error) {
	if len(data) < 1 {
		return nil, fmt.Errorf("empty message")
	}

	events := make([]*BinlogEvent, 0)
	msgType := data[0]

	switch msgType {
	case 'I':
		event := &BinlogEvent{
			Type:      EventInsert,
			Timestamp: time.Now(),
		}
		events = append(events, event)
	case 'U':
		event := &BinlogEvent{
			Type:      EventUpdate,
			Timestamp: time.Now(),
		}
		events = append(events, event)
	case 'D':
		event := &BinlogEvent{
			Type:      EventDelete,
			Timestamp: time.Now(),
		}
		events = append(events, event)
	case 'T':
		event := &BinlogEvent{
			Type:      EventDDL,
			Timestamp: time.Now(),
		}
		events = append(events, event)
	}

	return events, nil
}

func (pg *PGReplicationListener) dispatch(event *BinlogEvent) {
	pg.mu.RLock()
	handlers := pg.handlers
	pg.mu.RUnlock()

	for _, handler := range handlers {
		handler(event)
	}

	select {
	case pg.eventChan <- event:
	default:
	}
}

func (pg *PGReplicationListener) Stop() {
	pg.mu.Lock()
	defer pg.mu.Unlock()

	if !pg.running {
		return
	}

	if pg.cancel != nil {
		pg.cancel()
	}
}

func (pg *PGReplicationListener) GetLSN() string {
	pg.mu.RLock()
	defer pg.mu.RUnlock()
	return pg.lsn
}

func (pg *PGReplicationListener) IsRunning() bool {
	pg.mu.RLock()
	defer pg.mu.RUnlock()
	return pg.running
}

type SimpleTriggerListener struct {
	config    PGReplicationConfig
	db        *sql.DB
	handlers  []func(*BinlogEvent)
	eventChan chan *BinlogEvent
	ctx       context.Context
	cancel    context.CancelFunc
	running   bool
	mu        sync.RWMutex
	pollInterval time.Duration
}

func NewSimpleTriggerListener(config PGReplicationConfig) *SimpleTriggerListener {
	return &SimpleTriggerListener{
		config:       config,
		handlers:     make([]func(*BinlogEvent), 0),
		eventChan:    make(chan *BinlogEvent, 1000),
		pollInterval: 500 * time.Millisecond,
	}
}

func (stl *SimpleTriggerListener) AddHandler(handler func(*BinlogEvent)) {
	stl.mu.Lock()
	defer stl.mu.Unlock()
	stl.handlers = append(stl.handlers, handler)
}

func (stl *SimpleTriggerListener) Events() <-chan *BinlogEvent {
	return stl.eventChan
}

func (stl *SimpleTriggerListener) Start(ctx context.Context) error {
	stl.mu.Lock()
	if stl.running {
		stl.mu.Unlock()
		return fmt.Errorf("already running")
	}
	stl.ctx, stl.cancel = context.WithCancel(ctx)
	stl.running = true
	stl.mu.Unlock()

	connStr := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
		stl.config.Host, stl.config.Port, stl.config.User, stl.config.Password, stl.config.Database)

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return fmt.Errorf("failed to open connection: %w", err)
	}
	stl.db = db

	go stl.pollLoop()

	return nil
}

func (stl *SimpleTriggerListener) pollLoop() {
	defer func() {
		stl.mu.Lock()
		stl.running = false
		stl.mu.Unlock()
		close(stl.eventChan)
		if stl.db != nil {
			stl.db.Close()
		}
	}()

	ticker := time.NewTicker(stl.pollInterval)
	defer ticker.Stop()

	lastCheck := time.Now()

	for {
		select {
		case <-stl.ctx.Done():
			return
		case <-ticker.C:
			events := stl.checkForChanges(lastCheck)
			for _, event := range events {
				stl.dispatch(event)
			}
			lastCheck = time.Now()
		}
	}
}

func (stl *SimpleTriggerListener) checkForChanges(since time.Time) []*BinlogEvent {
	events := make([]*BinlogEvent, 0)

	for _, table := range stl.config.Tables {
		query := fmt.Sprintf("SELECT COUNT(*) FROM %s", table)
		var count int
		err := stl.db.QueryRowContext(stl.ctx, query).Scan(&count)
		if err == nil {
			event := &BinlogEvent{
				Type:      EventUpdate,
				Database:  stl.config.Database,
				Table:     table,
				Timestamp: time.Now(),
			}
			events = append(events, event)
		}
	}

	return events
}

func (stl *SimpleTriggerListener) dispatch(event *BinlogEvent) {
	stl.mu.RLock()
	handlers := stl.handlers
	stl.mu.RUnlock()

	for _, handler := range handlers {
		handler(event)
	}

	select {
	case stl.eventChan <- event:
	default:
	}
}

func (stl *SimpleTriggerListener) Stop() {
	stl.mu.Lock()
	defer stl.mu.Unlock()

	if !stl.running {
		return
	}

	if stl.cancel != nil {
		stl.cancel()
	}
}

func (stl *SimpleTriggerListener) IsRunning() bool {
	stl.mu.RLock()
	defer stl.mu.RUnlock()
	return stl.running
}
