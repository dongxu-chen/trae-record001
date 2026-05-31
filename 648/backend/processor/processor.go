package processor

import (
	"context"
	"redis-keyspace-notifier/logger"
	"redis-keyspace-notifier/models"
	"redis-keyspace-notifier/retry"
	"sync"
	"time"

	"go.uber.org/zap"
)

type EventProcessor struct {
	eventChan      <-chan models.KeyEvent
	sortedQueue    *SortedEventQueue
	filter         *EventFilter
	sampler        *EventSampler
	latencyAnalyzer *LatencyAnalyzer
	hotKeyAnalyzer  *HotKeyAnalyzer
	callback       *CallbackHandler
	retryQueue     *retry.RetryQueue
	store          *EventStore
	wg             sync.WaitGroup
	ctx            context.Context
	cancel         context.CancelFunc
}

func NewEventProcessor(eventChan <-chan models.KeyEvent, store *EventStore) *EventProcessor {
	ctx, cancel := context.WithCancel(context.Background())

	sortedQueue := NewSortedEventQueue(eventChan, 100*time.Millisecond, 10000)

	processor := &EventProcessor{
		eventChan:       eventChan,
		sortedQueue:     sortedQueue,
		filter:          NewEventFilter(),
		sampler:         NewEventSampler(),
		latencyAnalyzer: NewLatencyAnalyzer(10000),
		hotKeyAnalyzer:  NewHotKeyAnalyzer(10000, 5*time.Minute),
		callback:        NewCallbackHandler(),
		store:           store,
		ctx:             ctx,
		cancel:          cancel,
	}

	processor.retryQueue = retry.NewRetryQueue(processor.processEventWithRetry)

	return processor
}

func (p *EventProcessor) Start() {
	p.sortedQueue.Start()
	p.retryQueue.Start()

	p.wg.Add(1)
	go p.processLoop()

	go p.listenRetryNotifications()
}

func (p *EventProcessor) processLoop() {
	defer p.wg.Done()

	for {
		select {
		case <-p.ctx.Done():
			return
		case event := <-p.sortedQueue.OutputChan():
			p.processEvent(&event)
		}
	}
}

func (p *EventProcessor) processEvent(event *models.KeyEvent) {
	if !p.filter.Filter(event) {
		logger.Debug("Event filtered out",
			zap.String("key", event.Key),
			zap.String("event_type", event.EventType))
		return
	}

	if !p.sampler.ShouldProcess(event) {
		logger.Debug("Event sampled out",
			zap.String("key", event.Key),
			zap.String("event_type", event.EventType))
		return
	}

	p.hotKeyAnalyzer.Record(event)

	if err := p.callback.HandleEvent(event); err != nil {
		event.Error = err.Error()
		logger.Error("Event processing failed, queuing for retry",
			zap.String("event_id", event.ID),
			zap.String("key", event.Key),
			zap.Error(err))
		p.retryQueue.Add(event)
	} else {
		event.Processed = true
		logger.Debug("Event processed successfully",
			zap.String("event_id", event.ID),
			zap.String("key", event.Key))
	}

	p.latencyAnalyzer.Record(event)
	p.store.Add(*event)
}

func (p *EventProcessor) processEventWithRetry(event *models.KeyEvent) error {
	return p.callback.HandleEvent(event)
}

func (p *EventProcessor) listenRetryNotifications() {
	notifChan := p.retryQueue.GetNotificationChannel()

	for event := range notifChan {
		p.store.Update(*event)
	}
}

func (p *EventProcessor) Stop() {
	p.cancel()
	p.sortedQueue.Stop()
	p.retryQueue.Stop()
	p.wg.Wait()
}

func (p *EventProcessor) GetRetryQueueSize() int {
	return p.retryQueue.GetPendingCount()
}

func (p *EventProcessor) GetSortedQueueSize() int {
	return p.sortedQueue.GetPendingCount()
}

func (p *EventProcessor) GetLatencyStats() models.LatencyStats {
	return p.latencyAnalyzer.GetStats()
}

func (p *EventProcessor) GetLatencyStatsByEventType(eventType string) models.LatencyStats {
	return p.latencyAnalyzer.GetStatsByEventType(eventType)
}

func (p *EventProcessor) GetTopKeys(limit int) []models.KeyEventCount {
	return p.hotKeyAnalyzer.GetTopKeys(limit)
}

func (p *EventProcessor) GetTopKeysByEventType(eventType string, limit int) []models.KeyEventCount {
	return p.hotKeyAnalyzer.GetTopKeysByEventType(eventType, limit)
}

func (p *EventProcessor) GetSamplingConfig() SamplingConfig {
	return p.sampler.GetConfig()
}

func (p *EventProcessor) ResetAnalytics() {
	p.latencyAnalyzer.Reset()
	p.hotKeyAnalyzer.Reset()
}
