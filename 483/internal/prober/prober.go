package prober

import (
	"context"
	"fmt"
	"net"
	"sync"
	"time"

	"kafka-lag-analyzer/internal/config"

	"github.com/IBM/sarama"
)

type BrokerRTT struct {
	BrokerID  int32
	Host      string
	Port      int32
	RTT       time.Duration
	MinRTT    time.Duration
	MaxRTT    time.Duration
	AvgRTT    time.Duration
	Jitter    time.Duration
	Timestamp time.Time
	Success   bool
	Error     string
}

type PartitionRTT struct {
	Topic          string
	Partition      int32
	LeaderBrokerID int32
	RTT            time.Duration
	Timestamp      time.Time
}

type ProbeResult struct {
	BrokerRTTs     map[int32]BrokerRTT
	PartitionRTTs  map[string]map[int32]PartitionRTT
	OverallAvgRTT  time.Duration
	OverallMaxRTT  time.Duration
	HighRTTBrokers []int32
	Timestamp      time.Time
}

type Prober interface {
	Probe(ctx context.Context) (*ProbeResult, error)
	GetLatestResult() *ProbeResult
	Start(ctx context.Context, interval time.Duration)
}

type rttProber struct {
	cfg      *config.KafkaConfig
	client   sarama.Client
	admin    sarama.ClusterAdmin
	latest   *ProbeResult
	rttHist  map[int32][]time.Duration
	mu       sync.RWMutex
}

func NewProber(cfg *config.KafkaConfig) (Prober, error) {
	saramaCfg := sarama.NewConfig()
	saramaCfg.Net.DialTimeout = cfg.Timeout
	saramaCfg.Net.ReadTimeout = cfg.Timeout
	saramaCfg.Net.WriteTimeout = cfg.Timeout
	saramaCfg.Version = sarama.V2_8_0_0

	if cfg.Username != "" && cfg.Password != "" {
		saramaCfg.Net.SASL.Enable = true
		saramaCfg.Net.SASL.Mechanism = sarama.SASLTypePlaintext
		saramaCfg.Net.SASL.User = cfg.Username
		saramaCfg.Net.SASL.Password = cfg.Password
	}
	if cfg.TLSEnabled {
		saramaCfg.Net.TLS.Enable = true
	}

	client, err := sarama.NewClient(cfg.Brokers, saramaCfg)
	if err != nil {
		return nil, fmt.Errorf("failed to create prober client: %w", err)
	}

	admin, err := sarama.NewClusterAdmin(cfg.Brokers, saramaCfg)
	if err != nil {
		client.Close()
		return nil, fmt.Errorf("failed to create prober admin: %w", err)
	}

	return &rttProber{
		cfg:     cfg,
		client:  client,
		admin:   admin,
		rttHist: make(map[int32][]time.Duration),
	}, nil
}

func (p *rttProber) Probe(ctx context.Context) (*ProbeResult, error) {
	result := &ProbeResult{
		BrokerRTTs:    make(map[int32]BrokerRTT),
		PartitionRTTs: make(map[string]map[int32]PartitionRTT),
		Timestamp:     time.Now(),
	}

	brokers := p.client.Brokers()
	var totalRTT time.Duration
	var maxRTT time.Duration
	var successCount int

	var wg sync.WaitGroup
	resultCh := make(chan BrokerRTT, len(brokers))

	for _, broker := range brokers {
		wg.Add(1)
		go func(b *sarama.Broker) {
			defer wg.Done()
			rtt := p.probeBroker(ctx, b)
			resultCh <- rtt
		}(broker)
	}

	wg.Wait()
	close(resultCh)

	for rtt := range resultCh {
		result.BrokerRTTs[rtt.BrokerID] = rtt
		if rtt.Success {
			totalRTT += rtt.RTT
			if rtt.RTT > maxRTT {
				maxRTT = rtt.RTT
			}
			successCount++
		}
	}

	if successCount > 0 {
		result.OverallAvgRTT = totalRTT / time.Duration(successCount)
		result.OverallMaxRTT = maxRTT

		threshold := time.Duration(p.cfg.RTTWarningThreshold) * time.Millisecond
		for id, rtt := range result.BrokerRTTs {
			if rtt.Success && rtt.RTT > threshold {
				result.HighRTTBrokers = append(result.HighRTTBrokers, id)
			}
		}
	}

	p.probeTopicPartitions(ctx, result)

	p.mu.Lock()
	p.latest = result
	p.mu.Unlock()

	return result, nil
}

func (p *rttProber) probeBroker(ctx context.Context, broker *sarama.Broker) BrokerRTT {
	result := BrokerRTT{
		BrokerID:  broker.ID(),
		Host:      broker.Addr(),
		Timestamp: time.Now(),
	}

	host, port, err := net.SplitHostPort(broker.Addr())
	if err != nil {
		host = broker.Addr()
		port = "9092"
	}
	result.Host = host
	var portInt int32
	fmt.Sscanf(port, "%d", &portInt)
	result.Port = portInt

	rtt, err := p.measureTCPRTT(broker.Addr())
	if err != nil {
		result.Success = false
		result.Error = err.Error()
		return result
	}
	result.RTT = rtt
	result.Success = true

	p.mu.Lock()
	p.rttHist[broker.ID()] = append(p.rttHist[broker.ID()], rtt)
	if len(p.rttHist[broker.ID()]) > 20 {
		p.rttHist[broker.ID()] = p.rttHist[broker.ID()][1:]
	}
	hist := p.rttHist[broker.ID()]
	p.mu.Unlock()

	if len(hist) > 0 {
		var minD, maxD, sum time.Duration
		minD = hist[0]
		maxD = hist[0]
		for _, d := range hist {
			if d < minD {
				minD = d
			}
			if d > maxD {
				maxD = d
			}
			sum += d
		}
		result.MinRTT = minD
		result.MaxRTT = maxD
		result.AvgRTT = sum / time.Duration(len(hist))
		result.Jitter = maxD - minD
	}

	apiRTT, err := p.measureAPIRTT(broker)
	if err == nil && apiRTT > 0 {
		result.RTT = (result.RTT + apiRTT) / 2
	}

	return result
}

func (p *rttProber) measureTCPRTT(addr string) (time.Duration, error) {
	start := time.Now()
	conn, err := net.DialTimeout("tcp", addr, p.cfg.Timeout)
	if err != nil {
		return 0, fmt.Errorf("tcp connect failed: %w", err)
	}
	conn.Close()
	return time.Since(start), nil
}

func (p *rttProber) measureAPIRTT(broker *sarama.Broker) (time.Duration, error) {
	start := time.Now()

	if !broker.IsConnected() {
		if err := broker.Open(sarama.NewConfig()); err != nil {
			return 0, err
		}
	}

	req := &sarama.MetadataRequest{
		Topics: []string{},
	}
	_, err := broker.GetMetadata(req)
	if err != nil {
		return 0, err
	}

	return time.Since(start), nil
}

func (p *rttProber) probeTopicPartitions(ctx context.Context, result *ProbeResult) {
	topics, err := p.client.Topics()
	if err != nil {
		return
	}

	for _, topic := range topics {
		if len(p.cfg.Topics) > 0 {
			found := false
			for _, t := range p.cfg.Topics {
				if t == topic {
					found = true
					break
				}
			}
			if !found {
				continue
			}
		}

		partitions, err := p.client.Partitions(topic)
		if err != nil {
			continue
		}

		if _, ok := result.PartitionRTTs[topic]; !ok {
			result.PartitionRTTs[topic] = make(map[int32]PartitionRTT)
		}

		for _, partition := range partitions {
			leader := p.client.Leader(topic, partition)
			if leader == nil {
				continue
			}

			start := time.Now()
			_, err := p.client.GetOffset(topic, partition, sarama.OffsetNewest)
			rtt := time.Since(start)

			if err == nil {
				result.PartitionRTTs[topic][partition] = PartitionRTT{
					Topic:          topic,
					Partition:      partition,
					LeaderBrokerID: leader.ID(),
					RTT:            rtt,
					Timestamp:      time.Now(),
				}
			}
		}
	}
}

func (p *rttProber) GetLatestResult() *ProbeResult {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.latest
}

func (p *rttProber) Start(ctx context.Context, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	p.Probe(ctx)

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			if _, err := p.Probe(ctx); err != nil {
				continue
			}
		}
	}
}

func (p *rttProber) Close() error {
	if p.admin != nil {
		p.admin.Close()
	}
	return p.client.Close()
}
