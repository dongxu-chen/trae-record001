package mirror

import (
	"context"
	"fmt"
	"log"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/Shopify/sarama"
	"golang.org/x/sync/errgroup"

	"kafka-mirror/config"
	"kafka-mirror/interceptor"
	"kafka-mirror/metrics"
)

type ClusterType string

const (
	PrimaryCluster ClusterType = "primary"
	StandbyCluster ClusterType = "standby"
)

type ClusterState struct {
	Name           string
	ClusterType    ClusterType
	BrokerList     []string
	Healthy        bool
	FailedChecks   int
	LastSuccess    time.Time
	Config         *config.KafkaConfig
	Client         sarama.Client
	Admin          sarama.ClusterAdmin
}

type KafkaMirror struct {
	cfg                *config.MirrorConfig
	primaryState       *ClusterState
	standbyState       *ClusterState
	activeState        *ClusterState
	activeStateMu      sync.RWMutex
	consumer           sarama.ConsumerGroup
	producer           sarama.SyncProducer
	targetAdminClient  sarama.ClusterAdmin
	interceptor        interceptor.MessageInterceptor
	metrics            *metrics.Metrics
	ctx                context.Context
	cancel             context.CancelFunc
	wg                 sync.WaitGroup
	topicsMu           sync.RWMutex
	topics             []string
	topicPattern       *regexp.Regexp
	topicAutoCreateMu  sync.Mutex
	createdTopics      map[string]bool
}

func NewKafkaMirror(cfg *config.MirrorConfig) (*KafkaMirror, error) {
	m := &KafkaMirror{
		cfg:           cfg,
		metrics:       metrics.NewMetrics(),
		createdTopics: make(map[string]bool),
	}

	var err error
	m.primaryState, err = m.initClusterState("primary", PrimaryCluster, &cfg.SourceCluster.KafkaConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize primary cluster: %w", err)
	}

	if cfg.StandbyCluster.Enabled {
		m.standbyState, err = m.initClusterState("standby", StandbyCluster, &cfg.StandbyCluster.KafkaConfig)
		if err != nil {
			log.Printf("Warning: failed to initialize standby cluster: %v", err)
		}
	}

	m.activeState = m.primaryState

	if err := m.setupTargetAdminClient(); err != nil {
		return nil, fmt.Errorf("failed to setup target admin client: %w", err)
	}

	if err := m.setupProducer(); err != nil {
		return nil, fmt.Errorf("failed to setup producer: %w", err)
	}

	if err := m.setupConsumer(); err != nil {
		return nil, fmt.Errorf("failed to setup consumer: %w", err)
	}

	if err := m.setupInterceptor(); err != nil {
		return nil, fmt.Errorf("failed to setup interceptor: %w", err)
	}

	m.ctx, m.cancel = context.WithCancel(context.Background())

	m.metrics.InitLagMonitor(
		cfg.LagMonitor.WindowSize,
		time.Duration(cfg.LagMonitor.CollectIntervalSeconds)*time.Second,
		cfg.LagMonitor.AlertThreshold,
	)

	if cfg.TopicDiscovery.Enabled && cfg.TopicDiscovery.TopicNameRegex != "" {
		m.topicPattern, err = regexp.Compile(cfg.TopicDiscovery.TopicNameRegex)
		if err != nil {
			return nil, fmt.Errorf("invalid topic discovery regex: %w", err)
		}
	}

	m.topics = make([]string, len(cfg.Topics))
	copy(m.topics, cfg.Topics)

	m.metrics.SetActiveSourceCluster("primary")
	m.metrics.SetClusterHealthStatus("primary", string(PrimaryCluster), true)
	if m.standbyState != nil {
		m.metrics.SetClusterHealthStatus("standby", string(StandbyCluster), true)
	}

	return m, nil
}

func (m *KafkaMirror) initClusterState(name string, clusterType ClusterType, cfg *config.KafkaConfig) (*ClusterState, error) {
	state := &ClusterState{
		Name:        name,
		ClusterType: clusterType,
		BrokerList:  cfg.GetBrokers(),
		Healthy:     true,
		Config:      cfg,
		LastSuccess: time.Now(),
	}

	clientConfig := sarama.NewConfig()
	if cfg.SecurityProtocol == "SASL_SSL" {
		clientConfig.Net.SASL.Enable = true
		clientConfig.Net.SASL.User = cfg.Username
		clientConfig.Net.SASL.Password = cfg.Password
		clientConfig.Net.SASL.Mechanism = sarama.SASLMechanism(cfg.SASLMechanism)
		clientConfig.Net.TLS.Enable = true
	}

	client, err := sarama.NewClient(state.BrokerList, clientConfig)
	if err != nil {
		return nil, err
	}
	state.Client = client

	admin, err := sarama.NewClusterAdminFromClient(client)
	if err != nil {
		client.Close()
		return nil, err
	}
	state.Admin = admin

	return state, nil
}

func (m *KafkaMirror) setupTargetAdminClient() error {
	adminConfig := sarama.NewConfig()
	if m.cfg.TargetCluster.SecurityProtocol == "SASL_SSL" {
		adminConfig.Net.SASL.Enable = true
		adminConfig.Net.SASL.User = m.cfg.TargetCluster.Username
		adminConfig.Net.SASL.Password = m.cfg.TargetCluster.Password
		adminConfig.Net.SASL.Mechanism = sarama.SASLMechanism(m.cfg.TargetCluster.SASLMechanism)
		adminConfig.Net.TLS.Enable = true
	}

	var err error
	m.targetAdminClient, err = sarama.NewClusterAdmin(m.cfg.TargetCluster.GetBrokers(), adminConfig)
	return err
}

func (m *KafkaMirror) setupProducer() error {
	producerConfig := sarama.NewConfig()
	producerConfig.Producer.RequiredAcks = sarama.WaitForAll
	producerConfig.Producer.Retry.Max = 5
	producerConfig.Producer.Return.Successes = true
	producerConfig.Producer.Return.Errors = true

	if m.cfg.Compression.Enabled {
		switch m.cfg.Compression.Codec {
		case "zstd":
			producerConfig.Producer.Compression = sarama.CompressionZSTD
			producerConfig.Producer.CompressionLevel = m.cfg.Compression.Level
		case "snappy":
			producerConfig.Producer.Compression = sarama.CompressionSnappy
		case "lz4":
			producerConfig.Producer.Compression = sarama.CompressionLZ4
		case "gzip":
			producerConfig.Producer.Compression = sarama.CompressionGZIP
			producerConfig.Producer.CompressionLevel = m.cfg.Compression.Level
		}
		log.Printf("Compression enabled: %s (level: %d)", m.cfg.Compression.Codec, m.cfg.Compression.Level)
	}

	if m.cfg.TargetCluster.SecurityProtocol == "SASL_SSL" {
		producerConfig.Net.SASL.Enable = true
		producerConfig.Net.SASL.User = m.cfg.TargetCluster.Username
		producerConfig.Net.SASL.Password = m.cfg.TargetCluster.Password
		producerConfig.Net.SASL.Mechanism = sarama.SASLMechanism(m.cfg.TargetCluster.SASLMechanism)
		producerConfig.Net.TLS.Enable = true
	}

	var err error
	m.producer, err = sarama.NewSyncProducer(m.cfg.TargetCluster.GetBrokers(), producerConfig)
	return err
}

func (m *KafkaMirror) setupConsumer() error {
	m.activeStateMu.RLock()
	state := m.activeState
	m.activeStateMu.RUnlock()

	consumerConfig := sarama.NewConfig()
	consumerConfig.Consumer.Group.Rebalance.Strategy = sarama.NewBalanceStrategyRange()
	consumerConfig.Consumer.Offsets.Initial = sarama.OffsetOldest
	consumerConfig.Consumer.Return.Errors = true

	if state.Config.SecurityProtocol == "SASL_SSL" {
		consumerConfig.Net.SASL.Enable = true
		consumerConfig.Net.SASL.User = state.Config.Username
		consumerConfig.Net.SASL.Password = state.Config.Password
		consumerConfig.Net.SASL.Mechanism = sarama.SASLMechanism(state.Config.SASLMechanism)
		consumerConfig.Net.TLS.Enable = true
	}

	var err error
	m.consumer, err = sarama.NewConsumerGroup(
		state.BrokerList,
		m.cfg.ConsumerGroupID,
		consumerConfig,
	)
	return err
}

func (m *KafkaMirror) setupInterceptor() error {
	var interceptors []interceptor.MessageInterceptor

	var rawPaths []interceptor.RawJSONPath
	for _, jp := range m.cfg.Filter.JSONPaths {
		rawPaths = append(rawPaths, interceptor.RawJSONPath{
			Path:     jp.Path,
			Operator: jp.Operator,
			Value:    jp.Value,
		})
	}

	filterInterceptor, err := interceptor.NewFilterInterceptor(
		m.cfg.Filter.KeyRegex,
		m.cfg.Filter.ValueRegex,
		m.cfg.Filter.TopicRegex,
		rawPaths,
	)
	if err != nil {
		return fmt.Errorf("failed to create filter interceptor: %w", err)
	}
	interceptors = append(interceptors, filterInterceptor)

	if m.cfg.LoopPrevention.Enabled {
		loopInterceptor := interceptor.NewLoopPreventionInterceptor(
			m.cfg.LoopPrevention.HeaderKey,
			m.cfg.LoopPrevention.MaxHops,
		)
		interceptors = append(interceptors, loopInterceptor)
	}

	m.interceptor = interceptor.NewChainInterceptor(interceptors...)
	return nil
}

func (m *KafkaMirror) Start() error {
	log.Println("Starting Kafka Mirror service...")

	go func() {
		if err := m.metrics.StartServer(m.cfg.PrometheusPort); err != nil {
			log.Printf("Metrics server error: %v", err)
		}
	}()
	log.Printf("Metrics server started on port %d", m.cfg.PrometheusPort)

	if m.cfg.TopicDiscovery.Enabled {
		go m.topicDiscoveryLoop()
	}

	if m.cfg.StandbyCluster.Enabled && m.standbyState != nil {
		go m.healthCheckLoop()
	}

	go m.lagCollectorLoop()

	m.topicsMu.RLock()
	partitions := m.discoverPartitions(m.topics)
	m.topicsMu.RUnlock()

	m.metrics.StartLagCollector(m.topics, partitions)

	switch m.cfg.SyncMode {
	case "full":
		return m.doFullSync()
	case "incremental":
		return m.doIncrementalSync()
	case "full+incremental":
		if err := m.doFullSync(); err != nil {
			return err
		}
		return m.doIncrementalSync()
	default:
		return fmt.Errorf("unsupported sync mode: %s", m.cfg.SyncMode)
	}
}

func (m *KafkaMirror) topicDiscoveryLoop() {
	interval := time.Duration(m.cfg.TopicDiscovery.IntervalSeconds) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			m.discoverNewTopics()
		case <-m.ctx.Done():
			return
		}
	}
}

func (m *KafkaMirror) discoverNewTopics() {
	m.activeStateMu.RLock()
	state := m.activeState
	m.activeStateMu.RUnlock()

	topics, err := state.Admin.ListTopics()
	if err != nil {
		log.Printf("Failed to list topics for discovery: %v", err)
		return
	}

	m.topicsMu.Lock()
	defer m.topicsMu.Unlock()

	existingTopics := make(map[string]bool)
	for _, t := range m.topics {
		existingTopics[t] = true
	}

	var newTopics []string
	for topic := range topics {
		if existingTopics[topic] {
			continue
		}

		if m.cfg.TopicDiscovery.ExcludeInternalTopics && (strings.HasPrefix(topic, "__") || strings.HasPrefix(topic, "_confluent")) {
			continue
		}

		if m.topicPattern != nil && !m.topicPattern.MatchString(topic) {
			continue
		}

		newTopics = append(newTopics, topic)
		log.Printf("Discovered new topic: %s", topic)
		m.metrics.IncTopicDiscovered(topic)
	}

	if len(newTopics) > 0 {
		m.topics = append(m.topics, newTopics...)
		log.Printf("Total topics now: %d", len(m.topics))

		for _, topic := range newTopics {
			if err := m.ensureTopicExists(topic); err != nil {
				log.Printf("Failed to create topic %s on target cluster: %v", topic, err)
			}
		}

		m.consumer.Close()
		if err := m.setupConsumer(); err != nil {
			log.Printf("Failed to recreate consumer with new topics: %v", err)
		}
	}
}

func (m *KafkaMirror) ensureTopicExists(topic string) error {
	if !m.cfg.TopicAutoCreate.Enabled {
		return nil
	}

	m.topicAutoCreateMu.Lock()
	defer m.topicAutoCreateMu.Unlock()

	if m.createdTopics[topic] {
		return nil
	}

	topics, err := m.targetAdminClient.ListTopics()
	if err != nil {
		return err
	}

	if _, exists := topics[topic]; exists {
		m.createdTopics[topic] = true
		m.metrics.IncTopicCreated(topic, "already_exists")
		return nil
	}

	detail := &sarama.TopicDetail{
		NumPartitions:     int32(m.cfg.TopicAutoCreate.DefaultPartitions),
		ReplicationFactor: int16(m.cfg.TopicAutoCreate.DefaultReplicationFactor),
		ConfigEntries: map[string]*string{
			"retention.ms": ptrString(fmt.Sprintf("%d", m.cfg.TopicAutoCreate.RetentionMs)),
		},
	}

	if err := m.targetAdminClient.CreateTopic(topic, detail, false); err != nil {
		m.metrics.IncTopicCreated(topic, "failed")
		return err
	}

	log.Printf("Created topic %s on target cluster (partitions: %d, replication: %d)",
		topic, detail.NumPartitions, detail.ReplicationFactor)
	m.createdTopics[topic] = true
	m.metrics.IncTopicCreated(topic, "created")
	return nil
}

func (m *KafkaMirror) healthCheckLoop() {
	interval := time.Duration(m.cfg.StandbyCluster.HealthCheckIntervalSeconds) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			m.checkClustersHealth()
		case <-m.ctx.Done():
			return
		}
	}
}

func (m *KafkaMirror) checkClustersHealth() {
	m.checkClusterHealth(m.primaryState)

	if m.standbyState != nil {
		m.checkClusterHealth(m.standbyState)
	}

	m.activeStateMu.RLock()
	currentActive := m.activeState
	m.activeStateMu.RUnlock()

	if !currentActive.Healthy && currentActive.ClusterType == PrimaryCluster && m.standbyState != nil && m.standbyState.Healthy {
		m.switchToStandby()
	} else if currentActive.ClusterType == StandbyCluster && m.cfg.StandbyCluster.AutoSwitchBack && m.primaryState.Healthy {
		sinceLastSuccess := time.Since(m.primaryState.LastSuccess)
		if sinceLastSuccess >= time.Duration(m.cfg.StandbyCluster.SwitchBackIntervalMinutes)*time.Minute {
			m.switchToPrimary()
		}
	}
}

func (m *KafkaMirror) checkClusterHealth(state *ClusterState) {
	if state == nil || state.Client == nil {
		return
	}

	_, err := state.Client.Brokers()
	if err != nil {
		state.FailedChecks++
		state.Healthy = false
		m.metrics.SetClusterHealthStatus(state.Name, string(state.ClusterType), false)
		log.Printf("Cluster %s health check failed (%d/%d): %v",
			state.Name, state.FailedChecks, m.cfg.StandbyCluster.FailoverThreshold, err)
		return
	}

	state.FailedChecks = 0
	state.Healthy = true
	state.LastSuccess = time.Now()
	m.metrics.SetClusterHealthStatus(state.Name, string(state.ClusterType), true)
}

func (m *KafkaMirror) switchToStandby() {
	m.switchCluster(m.primaryState, m.standbyState, "standby", "primary_unhealthy")
}

func (m *KafkaMirror) switchToPrimary() {
	m.switchCluster(m.standbyState, m.primaryState, "primary", "auto_switch_back")
}

func (m *KafkaMirror) switchCluster(from, to *ClusterState, toName, reason string) {
	log.Printf("Initiating cluster switch from %s to %s (reason: %s)", from.Name, to.Name, reason)

	m.activeStateMu.Lock()
	m.activeState = to
	m.activeStateMu.Unlock()

	if m.consumer != nil {
		m.consumer.Close()
	}

	if err := m.setupConsumer(); err != nil {
		log.Printf("Failed to setup consumer after cluster switch: %v", err)
	}

	m.metrics.IncClusterSwitch(from.Name, to.Name, reason)
	m.metrics.SetActiveSourceCluster(toName)
	log.Printf("Successfully switched to %s cluster", to.Name)
}

func (m *KafkaMirror) discoverPartitions(topics []string) map[string][]int32 {
	result := make(map[string][]int32)

	m.activeStateMu.RLock()
	state := m.activeState
	m.activeStateMu.RUnlock()

	for _, topic := range topics {
		partitions, err := state.Client.Partitions(topic)
		if err != nil {
			log.Printf("Failed to discover partitions for topic %s: %v", topic, err)
			continue
		}
		result[topic] = partitions
	}
	return result
}

func (m *KafkaMirror) lagCollectorLoop() {
	m.wg.Add(1)
	defer m.wg.Done()

	interval := time.Duration(m.cfg.LagMonitor.CollectIntervalSeconds) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			m.collectLagSamples()
		case <-m.ctx.Done():
			return
		}
	}
}

func (m *KafkaMirror) collectLagSamples() {
	m.topicsMu.RLock()
	topics := make([]string, len(m.topics))
	copy(topics, m.topics)
	m.topicsMu.RUnlock()

	m.activeStateMu.RLock()
	state := m.activeState
	m.activeStateMu.RUnlock()

	for _, topic := range topics {
		partitions, err := state.Client.Partitions(topic)
		if err != nil {
			continue
		}

		for _, partition := range partitions {
			highWaterMark, err := state.Client.GetOffset(topic, partition, sarama.OffsetNewest)
			if err != nil {
				continue
			}

			lag := highWaterMark - 1
			if lag < 0 {
				lag = 0
			}
			m.metrics.UpdateLag(topic, partition, lag)
		}
	}
}

func (m *KafkaMirror) doFullSync() error {
	log.Println("Starting full sync...")

	m.topicsMu.RLock()
	topics := make([]string, len(m.topics))
	copy(topics, m.topics)
	m.topicsMu.RUnlock()

	for _, topic := range topics {
		if err := m.ensureTopicExists(topic); err != nil {
			log.Printf("Warning: failed to ensure topic %s exists: %v", topic, err)
		}

		if err := m.syncTopicFully(topic); err != nil {
			log.Printf("Full sync failed for topic %s: %v", topic, err)
			return err
		}
	}

	log.Println("Full sync completed successfully")
	return nil
}

func (m *KafkaMirror) syncTopicFully(topic string) error {
	log.Printf("Starting full sync for topic: %s", topic)

	m.activeStateMu.RLock()
	state := m.activeState
	m.activeStateMu.RUnlock()

	partitions, err := state.Client.Partitions(topic)
	if err != nil {
		return fmt.Errorf("failed to list partitions: %w", err)
	}

	g, ctx := errgroup.WithContext(m.ctx)

	for _, partition := range partitions {
		partition := partition
		g.Go(func() error {
			return m.syncPartition(ctx, topic, partition)
		})
	}

	return g.Wait()
}

func (m *KafkaMirror) syncPartition(ctx context.Context, topic string, partition int32) error {
	m.activeStateMu.RLock()
	state := m.activeState
	m.activeStateMu.RUnlock()

	consumerConfig := sarama.NewConfig()
	if state.Config.SecurityProtocol == "SASL_SSL" {
		consumerConfig.Net.SASL.Enable = true
		consumerConfig.Net.SASL.User = state.Config.Username
		consumerConfig.Net.SASL.Password = state.Config.Password
		consumerConfig.Net.SASL.Mechanism = sarama.SASLMechanism(state.Config.SASLMechanism)
		consumerConfig.Net.TLS.Enable = true
	}

	client, err := sarama.NewClient(state.BrokerList, consumerConfig)
	if err != nil {
		return err
	}
	defer client.Close()

	consumer, err := sarama.NewConsumerFromClient(client)
	if err != nil {
		return err
	}
	defer consumer.Close()

	partitionConsumer, err := consumer.ConsumePartition(topic, partition, sarama.OffsetOldest)
	if err != nil {
		return err
	}
	defer partitionConsumer.Close()

	highWaterMark, err := client.GetOffset(topic, partition, sarama.OffsetNewest)
	if err != nil {
		return err
	}

	log.Printf("Syncing partition %d of topic %s: offset 0 to %d", partition, topic, highWaterMark)

	msgCount := 0
	var totalUncompressed, totalCompressed int64

	for {
		select {
		case msg := <-partitionConsumer.Messages():
			m.metrics.IncMessagesConsumed(topic, partition, state.Name)

			if msg.Offset >= highWaterMark-1 {
				log.Printf("Completed sync for topic %s partition %d, messages: %d", topic, partition, msgCount)
				return nil
			}

			producerMsg, ok := m.interceptor.Intercept(msg)
			if !ok {
				m.metrics.IncMessagesDropped(topic)
				continue
			}

			uncompressedSize := int64(len(msg.Key) + len(msg.Value))

			startTime := time.Unix(0, msg.Timestamp.UnixNano())
			if _, _, err := m.producer.SendMessage(producerMsg); err != nil {
				log.Printf("Failed to send message: %v", err)
				continue
			}

			compressedSize := uncompressedSize
			totalUncompressed += uncompressedSize
			totalCompressed += compressedSize

			m.metrics.IncMessagesProduced(topic, partition)
			m.metrics.ObserveSyncLatency(topic, startTime)
			m.metrics.SetLastSyncTimestamp(topic)
			msgCount++

		case err := <-partitionConsumer.Errors():
			log.Printf("Partition consumer error: %v", err)
			return err

		case <-ctx.Done():
			if m.cfg.Compression.Enabled {
				m.metrics.UpdateCompressionStats(m.cfg.Compression.Codec, totalCompressed, totalUncompressed)
			}
			return ctx.Err()
		}
	}
}

func (m *KafkaMirror) doIncrementalSync() error {
	m.topicsMu.RLock()
	topics := make([]string, len(m.topics))
	copy(topics, m.topics)
	m.topicsMu.RUnlock()

	log.Println("Starting incremental sync...")
	log.Printf("Subscribing to topics: %v", topics)

	for _, topic := range topics {
		if err := m.ensureTopicExists(topic); err != nil {
			log.Printf("Warning: failed to ensure topic %s exists: %v", topic, err)
		}
	}

	handler := &consumerGroupHandler{
		mirror: m,
	}

	m.wg.Add(1)
	go func() {
		defer m.wg.Done()
		for {
			select {
			case <-m.ctx.Done():
				return
			default:
				m.topicsMu.RLock()
				currentTopics := make([]string, len(m.topics))
				copy(currentTopics, m.topics)
				m.topicsMu.RUnlock()

				if err := m.consumer.Consume(m.ctx, currentTopics, handler); err != nil {
					log.Printf("Consumer error: %v", err)
					time.Sleep(time.Second)
				}
			}
		}
	}()

	m.metrics.SetActiveConnections(1)
	log.Println("Incremental sync started successfully")

	<-m.ctx.Done()
	return nil
}

func (m *KafkaMirror) Stop() {
	log.Println("Stopping Kafka Mirror service...")

	m.metrics.StopLagCollector()

	if m.cancel != nil {
		m.cancel()
	}

	m.wg.Wait()

	if m.consumer != nil {
		m.consumer.Close()
	}
	if m.producer != nil {
		m.producer.Close()
	}
	if m.targetAdminClient != nil {
		m.targetAdminClient.Close()
	}
	if m.primaryState != nil {
		if m.primaryState.Admin != nil {
			m.primaryState.Admin.Close()
		}
		if m.primaryState.Client != nil {
			m.primaryState.Client.Close()
		}
	}
	if m.standbyState != nil {
		if m.standbyState.Admin != nil {
			m.standbyState.Admin.Close()
		}
		if m.standbyState.Client != nil {
			m.standbyState.Client.Close()
		}
	}

	log.Println("Kafka Mirror service stopped")
}

type consumerGroupHandler struct {
	mirror *KafkaMirror
}

func (h *consumerGroupHandler) Setup(session sarama.ConsumerGroupSession) error {
	return nil
}

func (h *consumerGroupHandler) Cleanup(session sarama.ConsumerGroupSession) error {
	return nil
}

func (h *consumerGroupHandler) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	h.mirror.activeStateMu.RLock()
	state := h.mirror.activeState
	h.mirror.activeStateMu.RUnlock()

	for msg := range claim.Messages() {
		h.mirror.metrics.IncMessagesConsumed(msg.Topic, msg.Partition, state.Name)

		producerMsg, ok := h.mirror.interceptor.Intercept(msg)
		if !ok {
			h.mirror.metrics.IncMessagesDropped(msg.Topic)
			session.MarkMessage(msg, "")
			continue
		}

		uncompressedSize := int64(len(msg.Key) + len(msg.Value))

		startTime := time.Unix(0, msg.Timestamp.UnixNano())
		_, _, err := h.mirror.producer.SendMessage(producerMsg)
		if err != nil {
			log.Printf("Failed to send message: %v", err)
			continue
		}

		compressedSize := uncompressedSize
		if h.mirror.cfg.Compression.Enabled {
			h.mirror.metrics.UpdateCompressionStats(h.mirror.cfg.Compression.Codec, compressedSize, uncompressedSize)
		}

		h.mirror.metrics.IncMessagesProduced(msg.Topic, msg.Partition)
		h.mirror.metrics.ObserveSyncLatency(msg.Topic, startTime)
		h.mirror.metrics.SetLastSyncTimestamp(msg.Topic)

		session.MarkMessage(msg, "")
	}

	return nil
}

func ptrString(s string) *string {
	return &s
}
