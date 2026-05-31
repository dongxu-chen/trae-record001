package redis

import (
	"context"
	"fmt"
	"redis-keyspace-notifier/logger"
	"redis-keyspace-notifier/models"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

type DBSubscriber struct {
	db         int
	rdb        *redis.Client
	eventChan  chan<- models.KeyEvent
	localChan  chan models.KeyEvent
	ctx        context.Context
	cancel     context.CancelFunc
	wg         sync.WaitGroup
}

type Subscriber struct {
	eventChan   chan<- models.KeyEvent
	dbSubs      map[int]*DBSubscriber
	wg          sync.WaitGroup
	ctx         context.Context
	cancel      context.CancelFunc
}

var keyspacePattern = regexp.MustCompile(`__keyspace@(\d+)__:.*`)

func NewSubscriber(eventChan chan<- models.KeyEvent) *Subscriber {
	ctx, cancel := context.WithCancel(context.Background())
	return &Subscriber{
		eventChan: eventChan,
		dbSubs:    make(map[int]*DBSubscriber),
		ctx:       ctx,
		cancel:    cancel,
	}
}

func (s *Subscriber) Start() error {
	client := GetClient()
	dbs := client.GetAllDBs()

	for db, rdb := range dbs {
		dbSub := &DBSubscriber{
			db:        db,
			rdb:       rdb,
			eventChan: s.eventChan,
			localChan: make(chan models.KeyEvent, 1000),
		}
		s.dbSubs[db] = dbSub
		s.wg.Add(1)
		go s.startDBSuscriber(dbSub)
	}

	return nil
}

func (s *Subscriber) startDBSuscriber(dbSub *DBSubscriber) {
	defer s.wg.Done()

	dbSub.ctx, dbSub.cancel = context.WithCancel(s.ctx)

	dbSub.wg.Add(2)
	go dbSub.subscribe()
	go dbSub.processEvents()

	logger.Info("DB subscriber started", zap.Int("db", dbSub.db))

	<-dbSub.ctx.Done()
	dbSub.wg.Wait()
	close(dbSub.localChan)

	logger.Info("DB subscriber stopped", zap.Int("db", dbSub.db))
}

func (d *DBSubscriber) subscribe() {
	defer d.wg.Done()

	pattern := fmt.Sprintf("__keyspace@%d__:*", d.db)
	pubsub := d.rdb.PSubscribe(d.ctx, pattern)
	defer pubsub.Close()

	logger.Info("Subscribed to keyspace events",
		zap.Int("db", d.db),
		zap.String("pattern", pattern))

	ch := pubsub.Channel()

	for {
		select {
		case <-d.ctx.Done():
			logger.Info("Stopping subscription", zap.Int("db", d.db))
			return
		case msg, ok := <-ch:
			if !ok {
				logger.Warn("Subscription channel closed", zap.Int("db", d.db))
				return
			}
			d.handleMessage(msg)
		}
	}
}

func (d *DBSubscriber) handleMessage(msg *redis.Message) {
	matches := keyspacePattern.FindStringSubmatch(msg.Channel)
	if len(matches) < 2 {
		return
	}

	key := strings.TrimPrefix(msg.Channel, fmt.Sprintf("__keyspace@%d__:", d.db))
	eventType := msg.Payload

	event := models.KeyEvent{
		ID:        uuid.New().String(),
		DB:        d.db,
		Key:       key,
		EventType: eventType,
		Timestamp: time.Now(),
		Processed: false,
	}

	logger.Debug("Received keyspace event",
		zap.Int("db", d.db),
		zap.String("key", key),
		zap.String("event_type", eventType))

	select {
	case d.localChan <- event:
	default:
		logger.Warn("DB local channel full, dropping event",
			zap.Int("db", d.db),
			zap.String("key", key),
			zap.String("event_type", eventType))
	}
}

func (d *DBSubscriber) processEvents() {
	defer d.wg.Done()

	for {
		select {
		case <-d.ctx.Done():
			return
		case event, ok := <-d.localChan:
			if !ok {
				return
			}
			select {
			case d.eventChan <- event:
			default:
				logger.Warn("Global event channel full, dropping event",
					zap.Int("db", d.db),
					zap.String("key", event.Key))
			}
		}
	}
}

func (s *Subscriber) Stop() {
	s.cancel()
	s.wg.Wait()
	logger.Info("All DB subscribers stopped")
}

func (s *Subscriber) GetDBPendingCount(db int) int {
	if sub, ok := s.dbSubs[db]; ok {
		return len(sub.localChan)
	}
	return 0
}

func (s *Subscriber) GetAllPendingCounts() map[int]int {
	counts := make(map[int]int)
	for db, sub := range s.dbSubs {
		counts[db] = len(sub.localChan)
	}
	return counts
}
