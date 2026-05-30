package binlog

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/go-mysql-org/go-mysql/canal"
	"github.com/go-mysql-org/go-mysql/mysql"
	"github.com/go-mysql-org/go-mysql/replication"
	"github.com/siddontang/go-log/log"
)

type EventType string

const (
	EventInsert  EventType = "INSERT"
	EventUpdate  EventType = "UPDATE"
	EventDelete  EventType = "DELETE"
	EventDDL     EventType = "DDL"
	EventXID     EventType = "XID"
)

type BinlogEvent struct {
	Type         EventType
	Database     string
	Table        string
	Timestamp    time.Time
	BeforeValues map[string]interface{}
	AfterValues  map[string]interface{}
	ChangedCols  []string
	PrimaryKey   interface{}
	QuerySQL     string
	Position     mysql.Position
	GTID         string
}

type BinlogListenerConfig struct {
	Host          string
	Port          int
	User          string
	Password      string
	Database      string
	Tables        []string
	ServerID      uint32
	StartPosition *mysql.Position
	Flavor        string
	UseGTID       bool
}

type BinlogListener struct {
	config      BinlogListenerConfig
	canal       *canal.Canal
	handlers    []func(*BinlogEvent)
	eventChan   chan *BinlogEvent
	ctx         context.Context
	cancel      context.CancelFunc
	running     bool
	mu          sync.RWMutex
	lastPos     mysql.Position
	lastGTID    string
}

func NewBinlogListener(config BinlogListenerConfig) (*BinlogListener, error) {
	if config.ServerID == 0 {
		config.ServerID = 1001
	}
	if config.Flavor == "" {
		config.Flavor = "mysql"
	}

	cfg := canal.NewDefaultConfig()
	cfg.Addr = fmt.Sprintf("%s:%d", config.Host, config.Port)
	cfg.User = config.User
	cfg.Password = config.Password
	cfg.Dump.DumpExec = ""
	cfg.Dump.DiscardErr = true
	cfg.Dump.SkipMasterData = 1
	cfg.Flavor = config.Flavor
	cfg.ServerID = config.ServerID

	if len(config.Tables) > 0 {
		includeRules := make([]string, 0, len(config.Tables))
		for _, tbl := range config.Tables {
			if config.Database != "" {
				includeRules = append(includeRules, fmt.Sprintf("%s\\.%s", config.Database, tbl))
			} else {
				includeRules = append(includeRules, "*\\."+tbl)
			}
		}
		cfg.IncludeTableRegex = includeRules
	} else if config.Database != "" {
		cfg.IncludeTableRegex = []string{fmt.Sprintf("%s\\..*", config.Database)}
	}

	c, err := canal.NewCanal(cfg)
	if err != nil {
		return nil, fmt.Errorf("failed to create canal: %w", err)
	}

	return &BinlogListener{
		config:    config,
		canal:     c,
		handlers:  make([]func(*BinlogEvent), 0),
		eventChan: make(chan *BinlogEvent, 10000),
	}, nil
}

func (bl *BinlogListener) AddHandler(handler func(*BinlogEvent)) {
	bl.mu.Lock()
	defer bl.mu.Unlock()
	bl.handlers = append(bl.handlers, handler)
}

func (bl *BinlogListener) Events() <-chan *BinlogEvent {
	return bl.eventChan
}

func (bl *BinlogListener) Start(ctx context.Context) error {
	bl.mu.Lock()
	if bl.running {
		bl.mu.Unlock()
		return fmt.Errorf("already running")
	}
	bl.ctx, bl.cancel = context.WithCancel(ctx)
	bl.running = true
	bl.mu.Unlock()

	handler := &eventHandler{
		listener: bl,
	}
	bl.canal.SetEventHandler(handler)

	go bl.run()

	return nil
}

func (bl *BinlogListener) run() {
	defer func() {
		bl.mu.Lock()
		bl.running = false
		bl.mu.Unlock()
		close(bl.eventChan)
	}()

	var startPos mysql.Position
	if bl.config.StartPosition != nil {
		startPos = *bl.config.StartPosition
	}

	streamer, err := bl.canal.StartSyncFrom(startPos)
	if err != nil {
		_ = fmt.Sprintf("binlog sync error: %v", err)
		return
	}

	for {
		select {
		case <-bl.ctx.Done():
			return
		default:
			ev, err := streamer.GetEvent(bl.ctx)
			if err != nil {
				_ = fmt.Sprintf("failed to get binlog event: %v", err)
				continue
			}
			bl.processEvent(ev)
		}
	}
}

func (bl *BinlogListener) processEvent(ev *replication.BinlogEvent) {
	switch e := ev.Event.(type) {
	case *replication.RowsEvent:
		bl.processRowsEvent(e, ev.Header)
	case *replication.QueryEvent:
		bl.processQueryEvent(e, ev.Header)
	case *replication.XIDEvent:
		bl.processXIDEvent(e, ev.Header)
	}
}

func (bl *BinlogListener) processRowsEvent(e *replication.RowsEvent, header *replication.EventHeader) {
	table := e.Table
	dbName := string(table.Schema)
	tableName := string(table.Table)

	var eventType EventType
	switch header.EventType {
	case replication.WRITE_ROWS_EVENTv0, replication.WRITE_ROWS_EVENTv1, replication.WRITE_ROWS_EVENTv2:
		eventType = EventInsert
	case replication.UPDATE_ROWS_EVENTv0, replication.UPDATE_ROWS_EVENTv1, replication.UPDATE_ROWS_EVENTv2:
		eventType = EventUpdate
	case replication.DELETE_ROWS_EVENTv0, replication.DELETE_ROWS_EVENTv1, replication.DELETE_ROWS_EVENTv2:
		eventType = EventDelete
	default:
		return
	}

	colNames := make([]string, len(table.Columns))
	for i, col := range table.Columns {
		colNames[i] = string(col.Name)
	}

	for i := 0; i < len(e.Rows); i++ {
		row := e.Rows[i]
		beforeValues := make(map[string]interface{})
		afterValues := make(map[string]interface{})
		changedCols := make([]string, 0)

		if eventType == EventUpdate {
			if i%2 == 0 && i+1 < len(e.Rows) {
				beforeRow := e.Rows[i]
				afterRow := e.Rows[i+1]
				for j, name := range colNames {
					beforeValues[name] = beforeRow[j]
					afterValues[name] = afterRow[j]
					if fmt.Sprintf("%v", beforeRow[j]) != fmt.Sprintf("%v", afterRow[j]) {
						changedCols = append(changedCols, name)
					}
				}
				i++
			}
		} else {
			for j, name := range colNames {
				afterValues[name] = row[j]
			}
			if eventType == EventDelete {
				beforeValues = afterValues
				afterValues = nil
			}
		}

		var pk interface{}
		if len(table.PKColumns) > 0 && len(afterValues) > 0 {
			pk = afterValues[colNames[table.PKColumns[0]]]
		} else if len(table.PKColumns) > 0 && len(beforeValues) > 0 {
			pk = beforeValues[colNames[table.PKColumns[0]]]
		}

		event := &BinlogEvent{
			Type:         eventType,
			Database:     dbName,
			Table:        tableName,
			Timestamp:    time.Unix(int64(header.Timestamp), 0),
			BeforeValues: beforeValues,
			AfterValues:  afterValues,
			ChangedCols:  changedCols,
			PrimaryKey:   pk,
		}

		bl.dispatch(event)
	}
}

func (bl *BinlogListener) processQueryEvent(e *replication.QueryEvent, header *replication.EventHeader) {
	query := string(e.Query)
	dbName := string(e.Schema)

	event := &BinlogEvent{
		Type:      EventDDL,
		Database:  dbName,
		Timestamp: time.Unix(int64(header.Timestamp), 0),
		QuerySQL:  query,
	}

	bl.dispatch(event)
}

func (bl *BinlogListener) processXIDEvent(e *replication.XIDEvent, header *replication.EventHeader) {
	event := &BinlogEvent{
		Type:      EventXID,
		Timestamp: time.Unix(int64(header.Timestamp), 0),
	}
	bl.dispatch(event)
}

func (bl *BinlogListener) dispatch(event *BinlogEvent) {
	bl.mu.RLock()
	handlers := bl.handlers
	bl.mu.RUnlock()

	for _, handler := range handlers {
		handler(event)
	}

	select {
	case bl.eventChan <- event:
	default:
	}
}

func (bl *BinlogListener) Stop() {
	bl.mu.Lock()
	defer bl.mu.Unlock()

	if !bl.running {
		return
	}

	if bl.cancel != nil {
		bl.cancel()
	}

	if bl.canal != nil {
		bl.canal.Close()
	}
}

func (bl *BinlogListener) GetLastPosition() mysql.Position {
	bl.mu.RLock()
	defer bl.mu.RUnlock()
	return bl.lastPos
}

func (bl *BinlogListener) GetLastGTID() string {
	bl.mu.RLock()
	defer bl.mu.RUnlock()
	return bl.lastGTID
}

func (bl *BinlogListener) IsRunning() bool {
	bl.mu.RLock()
	defer bl.mu.RUnlock()
	return bl.running
}

type eventHandler struct {
	canal.DummyEventHandler
	listener *BinlogListener
}

func (h *eventHandler) OnRow(e *canal.RowsEvent) error {
	return nil
}

func (h *eventHandler) OnDDL(nextPos mysql.Position, queryEvent *replication.QueryEvent) error {
	return nil
}

func (h *eventHandler) OnXID(nextPos mysql.Position) error {
	h.listener.mu.Lock()
	h.listener.lastPos = nextPos
	h.listener.mu.Unlock()
	return nil
}

func (h *eventHandler) OnGTID(gtid mysql.GTIDSet) error {
	h.listener.mu.Lock()
	if gtid != nil {
		h.listener.lastGTID = gtid.String()
	}
	h.listener.mu.Unlock()
	return nil
}

func (h *eventHandler) OnPosSynced(pos mysql.Position, set mysql.GTIDSet, force bool) error {
	h.listener.mu.Lock()
	h.listener.lastPos = pos
	if set != nil {
		h.listener.lastGTID = set.String()
	}
	h.listener.mu.Unlock()
	return nil
}

func (h *eventHandler) String() string {
	return "HeatCacheBinlogHandler"
}

func init() {
	log.SetLevel(log.LevelError)
}
