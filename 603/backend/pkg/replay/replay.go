package replay

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/apache/pulsar-client-go/pulsar"
	"pulsar-backlog-manager/pkg/audit"
	"pulsar-backlog-manager/pkg/strategy"
)

type ReplayRequest struct {
	Topic        string    `json:"topic"`
	Subscription string    `json:"subscription"`
	StartTime    time.Time `json:"start_time"`
	EndTime      time.Time `json:"end_time"`
	MaxMessages  int       `json:"max_messages"`
	TargetTopic  string    `json:"target_topic"`
}

type ReplayResult struct {
	Topic        string    `json:"topic"`
	Replayed     int       `json:"replayed"`
	Failed       int       `json:"failed"`
	StartTime    time.Time `json:"start_time"`
	EndTime      time.Time `json:"end_time"`
	CompletedAt  time.Time `json:"completed_at"`
	TargetTopic  string    `json:"target_topic"`
}

type ReplayStatus struct {
	Active   bool          `json:"active"`
	Topic    string        `json:"topic"`
	Progress int           `json:"progress"`
	Total    int           `json:"total"`
	Started  time.Time     `json:"started"`
}

type ReplayManager struct {
	client   pulsar.Client
	strategy *strategy.Manager
	audit    *audit.AuditLogger
	history  []ReplayResult
	status   map[string]*ReplayStatus
	mu       sync.Mutex
}

func NewReplayManager(pulsarClient pulsar.Client, strategyMgr *strategy.Manager, auditLog *audit.AuditLogger) *ReplayManager {
	return &ReplayManager{
		client:  pulsarClient,
		strategy: strategyMgr,
		audit:   auditLog,
		history: make([]ReplayResult, 0, 100),
		status:  make(map[string]*ReplayStatus),
	}
}

func (r *ReplayManager) ReplayMessages(req ReplayRequest) (*ReplayResult, error) {
	if req.MaxMessages <= 0 {
		req.MaxMessages = 1000
	}
	if req.TargetTopic == "" {
		req.TargetTopic = req.Topic + "-replay"
	}

	r.mu.Lock()
	if _, active := r.status[req.Topic]; active {
		r.mu.Unlock()
		return nil, fmt.Errorf("replay already in progress for topic %s", req.Topic)
	}
	r.status[req.Topic] = &ReplayStatus{
		Active:   true,
		Topic:    req.Topic,
		Total:    req.MaxMessages,
		Started:  time.Now(),
	}
	r.mu.Unlock()

	defer func() {
		r.mu.Lock()
		delete(r.status, req.Topic)
		r.mu.Unlock()
	}()

	reader, err := r.client.CreateReader(pulsar.ReaderOptions{
		Topic:          req.Topic,
		StartMessageID: pulsar.EarliestMessageID(),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create reader: %w", err)
	}
	defer reader.Close()

	producer, err := r.client.CreateProducer(pulsar.ProducerOptions{
		Topic:           req.TargetTopic,
		DisableBatching: false,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create replay producer: %w", err)
	}
	defer producer.Close()

	result := &ReplayResult{
		Topic:       req.Topic,
		StartTime:   req.StartTime,
		EndTime:     req.EndTime,
		TargetTopic: req.TargetTopic,
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	hasTimeFilter := !req.StartTime.IsZero() || !req.EndTime.IsZero()

	for result.Replayed+result.Failed < req.MaxMessages {
		msg, err := reader.Next(ctx)
		if err != nil {
			break
		}

		if hasTimeFilter {
			msgTime := msg.PublishTime()
			if !req.StartTime.IsZero() && msgTime.Before(req.StartTime) {
				continue
			}
			if !req.EndTime.IsZero() && msgTime.After(req.EndTime) {
				break
			}
		}

		_, err = producer.Send(ctx, &pulsar.ProducerMessage{
			Payload: msg.Payload(),
			Properties: map[string]string{
				"replay_source_topic": req.Topic,
				"replay_source_sub":   req.Subscription,
				"replay_timestamp":    time.Now().Format(time.RFC3339),
				"original_publish":    msg.PublishTime().Format(time.RFC3339),
			},
		})
		if err != nil {
			result.Failed++
		} else {
			result.Replayed++
		}

		r.mu.Lock()
		if st, exists := r.status[req.Topic]; exists {
			st.Progress = result.Replayed + result.Failed
		}
		r.mu.Unlock()
	}

	result.CompletedAt = time.Now()

	r.mu.Lock()
	r.history = append(r.history, *result)
	if len(r.history) > 100 {
		r.history = r.history[1:]
	}
	r.mu.Unlock()

	strategyCfg := r.strategy.GetStrategy(req.Topic)
	_ = strategyCfg

	r.audit.Log(audit.ActionReplay, req.Topic,
		"Replayed %d messages (%d failed) from %s to %s, time range: %s ~ %s",
		result.Replayed, result.Failed, req.Topic, req.TargetTopic,
		req.StartTime.Format(time.RFC3339), req.EndTime.Format(time.RFC3339))

	return result, nil
}

func (r *ReplayManager) ReplayByTimestamp(topic string, startTime, endTime time.Time, maxMessages int) (*ReplayResult, error) {
	return r.ReplayMessages(ReplayRequest{
		Topic:        topic,
		Subscription: "default",
		StartTime:    startTime,
		EndTime:      endTime,
		MaxMessages:  maxMessages,
	})
}

func (r *ReplayManager) ReplayLastN(topic string, n int) (*ReplayResult, error) {
	return r.ReplayMessages(ReplayRequest{
		Topic:        topic,
		Subscription: "default",
		MaxMessages:  n,
	})
}

func (r *ReplayManager) GetReplayStatus(topic string) *ReplayStatus {
	r.mu.Lock()
	defer r.mu.Unlock()
	if st, exists := r.status[topic]; exists {
		result := *st
		return &result
	}
	return nil
}

func (r *ReplayManager) GetReplayHistory(topic string) []ReplayResult {
	r.mu.Lock()
	defer r.mu.Unlock()

	if topic == "" {
		result := make([]ReplayResult, len(r.history))
		copy(result, r.history)
		return result
	}

	result := make([]ReplayResult, 0)
	for _, h := range r.history {
		if h.Topic == topic {
			result = append(result, h)
		}
	}
	return result
}

func (r *ReplayManager) CancelReplay(topic string) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if _, active := r.status[topic]; active {
		delete(r.status, topic)
		r.audit.Log(audit.ActionReplayCancel, topic, "Cancelled replay for topic %s", topic)
	}
}
