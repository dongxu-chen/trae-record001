package prediction

import (
	"context"
	"math"
	"sync"
	"time"

	"pulsar-backlog-manager/pkg/audit"
	"pulsar-backlog-manager/pkg/config"
	"pulsar-backlog-manager/pkg/monitor"
	"pulsar-backlog-manager/pkg/pulsar"
	"pulsar-backlog-manager/pkg/strategy"
)

type Prediction struct {
	Topic               string
	PredictedTime       time.Time
	PredictedBacklog    int64
	PredictedByteBacklog int64
	MsgSizeFactor       float64
	AvgMsgSize          float64
	Confidence          float64
	Model               string
}

type Predictor struct {
	config      config.PredictionConfig
	pulsar      *pulsar.Client
	strategy    *strategy.Manager
	audit       *audit.AuditLogger
	predictions map[string][]Prediction
	history     map[string][]monitor.TopicBacklog
	mu          sync.Mutex
}

func NewPredictor(cfg config.PredictionConfig, pulsarClient *pulsar.Client, strategyMgr *strategy.Manager, auditLog *audit.AuditLogger) *Predictor {
	return &Predictor{
		config:      cfg,
		pulsar:      pulsarClient,
		strategy:    strategyMgr,
		audit:       auditLog,
		predictions: make(map[string][]Prediction),
		history:     make(map[string][]monitor.TopicBacklog),
	}
}

func (p *Predictor) HandleBacklog(backlog monitor.TopicBacklog) {
	p.mu.Lock()
	defer p.mu.Unlock()

	key := backlog.Topic
	if _, exists := p.history[key]; !exists {
		p.history[key] = make([]monitor.TopicBacklog, 0, 1000)
	}
	p.history[key] = append(p.history[key], backlog)

	maxHistory := p.config.HistoryHours * 3600 / 30
	if len(p.history[key]) > maxHistory {
		p.history[key] = p.history[key][len(p.history[key])-maxHistory:]
	}
}

func (p *Predictor) StartPredictionLoop(ctx context.Context) {
	if !p.config.Enabled {
		return
	}

	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			p.runPredictions()
		}
	}
}

func (p *Predictor) runPredictions() {
	p.mu.Lock()
	defer p.mu.Unlock()

	for topic, history := range p.history {
		if len(history) < 10 {
			continue
		}

		prediction := p.linearRegressionPrediction(topic, history)
		key := topic
		if _, exists := p.predictions[key]; !exists {
			p.predictions[key] = make([]Prediction, 0, 100)
		}
		p.predictions[key] = append(p.predictions[key], prediction)
		if len(p.predictions[key]) > 100 {
			p.predictions[key] = p.predictions[key][1:]
		}

		strategyCfg := p.strategy.GetStrategy(topic)
		if strategyCfg != nil && strategyCfg.Prediction.AlertThreshold > 0 {
			alertBacklog := prediction.PredictedByteBacklog
			if alertBacklog == 0 {
				alertBacklog = prediction.PredictedBacklog
			}
			if alertBacklog > int64(strategyCfg.Prediction.AlertThreshold) {
				p.audit.Log(audit.ActionPredictionAlert, topic,
					"Predicted effective backlog %d bytes (raw %d msgs, factor %.2fx) will exceed threshold %d in 1 hour",
					alertBacklog, prediction.PredictedBacklog, prediction.MsgSizeFactor, strategyCfg.Prediction.AlertThreshold)
			}
		}
	}
}

func (p *Predictor) linearRegressionPrediction(topic string, history []monitor.TopicBacklog) Prediction {
	n := len(history)

	var sumX, sumYMsg, sumYByte, sumXYMsg, sumXYByte, sumX2 float64
	var avgMsgSize float64
	var msgSizeCount int

	for i, item := range history {
		x := float64(i)
		yMsg := float64(item.BacklogSize)
		yByte := float64(item.EffectiveBacklog)
		sumX += x
		sumYMsg += yMsg
		sumYByte += yByte
		sumXYMsg += x * yMsg
		sumXYByte += x * yByte
		sumX2 += x * x

		if item.AvgMsgSize > 0 {
			avgMsgSize += item.AvgMsgSize
			msgSizeCount++
		}
	}

	if msgSizeCount > 0 {
		avgMsgSize = avgMsgSize / float64(msgSizeCount)
	}

	slopeMsg := (float64(n)*sumXYMsg - sumX*sumYMsg) / (float64(n)*sumX2 - sumX*sumX)
	interceptMsg := (sumYMsg - slopeMsg*sumX) / float64(n)

	slopeByte := (float64(n)*sumXYByte - sumX*sumYByte) / (float64(n)*sumX2 - sumX*sumX)
	interceptByte := (sumYByte - slopeByte*sumX) / float64(n)

	predictionPoints := 120

	predictedBacklog := int64(math.Max(0, slopeMsg*float64(n+predictionPoints)+interceptMsg))
	predictedByteBacklog := int64(math.Max(0, slopeByte*float64(n+predictionPoints)+interceptByte))

	var msgSizeFactor float64
	if sumYMsg > 0 {
		msgSizeFactor = sumYByte / sumYMsg
	} else {
		msgSizeFactor = 1.0
	}

	if predictedByteBacklog == 0 && predictedBacklog > 0 && msgSizeFactor > 0 {
		predictedByteBacklog = int64(float64(predictedBacklog) * msgSizeFactor)
	}

	var residuals float64
	for i, item := range history {
		predicted := slopeByte*float64(i) + interceptByte
		residuals += math.Abs(float64(item.EffectiveBacklog) - predicted)
	}
	mae := residuals / float64(n)
	confidence := 1.0
	if meanBacklog := sumYByte / float64(n); meanBacklog > 0 {
		confidence = math.Max(0, 1-mae/meanBacklog)
	}

	return Prediction{
		Topic:               topic,
		PredictedTime:       time.Now().Add(time.Duration(predictionPoints*30) * time.Second),
		PredictedBacklog:    predictedBacklog,
		PredictedByteBacklog: predictedByteBacklog,
		MsgSizeFactor:       msgSizeFactor,
		AvgMsgSize:          avgMsgSize,
		Confidence:          confidence,
		Model:               "linear_regression_with_size",
	}
}

func (p *Predictor) GetPrediction(topic string) *Prediction {
	p.mu.Lock()
	defer p.mu.Unlock()

	if predictions, exists := p.predictions[topic]; exists && len(predictions) > 0 {
		latest := predictions[len(predictions)-1]
		return &latest
	}
	return nil
}

func (p *Predictor) GetPredictionHistory(topic string) []Prediction {
	p.mu.Lock()
	defer p.mu.Unlock()

	if predictions, exists := p.predictions[topic]; exists {
		result := make([]Prediction, len(predictions))
		copy(result, predictions)
		return result
	}
	return []Prediction{}
}
