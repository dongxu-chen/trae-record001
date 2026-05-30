package rebalancer

import (
	"context"
	"fmt"
	"sort"
	"sync"
	"time"

	"github.com/sirupsen/logrus"

	kafkaclient "kafka-autoscaler/pkg/kafka"
)

type AssignmentStrategy string

const (
	StrategyRange         AssignmentStrategy = "range"
	StrategyRoundRobin    AssignmentStrategy = "roundrobin"
	StrategySticky        AssignmentStrategy = "sticky"
	StrategyUniform       AssignmentStrategy = "uniform"
	StrategyKeyRange      AssignmentStrategy = "key_range"
	StrategyKeyHash       AssignmentStrategy = "key_hash"
	StrategyKeySticky     AssignmentStrategy = "key_sticky"
)

type PartitionAssignment struct {
	Topic      string
	Partition  int32
	ConsumerID string
}

type RebalanceConfig struct {
	Strategy                AssignmentStrategy
	MaxConcurrentMoves      int
	MinPartitionCount       int
	RebalanceInterval       time.Duration
	EnableUnevenDetection   bool
	UnevenThresholdRatio    float64
	DryRun                  bool
	KeyHashPartitions       map[string][]int32
	KeyRangeBuckets         []KeyRangeBucket
	KeyPrefixDelimiter      string
}

type KeyRangeBucket struct {
	StartPrefix string
	EndPrefix   string
	ConsumerID  string
}

type KeyPartitionMapping struct {
	KeyPrefix   string
	Partition   int32
	ConsumerID  string
}

type Rebalancer struct {
	kafkaClient *kafkaclient.Client
	config      *RebalanceConfig
	logger      *logrus.Logger
	mu          sync.Mutex
	lastRun     time.Time
	ctx         context.Context
	cancel      context.CancelFunc
	wg          sync.WaitGroup
}

type PartitionInfo struct {
	Topic     string
	Partition int32
	Leader    int32
	Replicas  []int32
	Lag       int64
	Consumer  string
}

type BrokerLoad struct {
	BrokerID      int32
	PartitionCount int
	TotalLag      int64
}

func NewRebalancer(
	kafkaClient *kafkaclient.Client,
	config *RebalanceConfig,
	logger *logrus.Logger,
) *Rebalancer {
	ctx, cancel := context.WithCancel(context.Background())

	return &Rebalancer{
		kafkaClient: kafkaClient,
		config:      config,
		logger:      logger,
		ctx:         ctx,
		cancel:      cancel,
	}
}

func (r *Rebalancer) Start() {
	if r.config.DryRun {
		r.logger.Info("Rebalancer started in dry-run mode")
	} else {
		r.logger.Info("Rebalancer started")
	}

	r.wg.Add(1)
	go r.run()
}

func (r *Rebalancer) Stop() {
	r.logger.Info("Stopping rebalancer...")
	r.cancel()
	r.wg.Wait()
	r.logger.Info("Rebalancer stopped")
}

func (r *Rebalancer) run() {
	defer r.wg.Done()

	ticker := time.NewTicker(r.config.RebalanceInterval)
	defer ticker.Stop()

	for {
		select {
		case <-r.ctx.Done():
			return
		case <-ticker.C:
			r.CheckAndRebalance()
		}
	}
}

func (r *Rebalancer) CheckAndRebalance() error {
	r.mu.Lock()
	defer r.mu.Unlock()

	if time.Since(r.lastRun) < r.config.RebalanceInterval {
		return nil
	}
	r.lastRun = time.Now()

	consumerGroups, err := r.kafkaClient.ListConsumerGroups()
	if err != nil {
		return fmt.Errorf("failed to list consumer groups: %w", err)
	}

	for groupID := range consumerGroups {
		if err := r.rebalanceConsumerGroup(groupID); err != nil {
			r.logger.Errorf("Failed to rebalance consumer group %s: %v", groupID, err)
		}
	}

	return nil
}

func (r *Rebalancer) rebalanceConsumerGroup(groupID string) error {
	lagData, err := r.kafkaClient.GetConsumerGroupLag(groupID)
	if err != nil {
		return err
	}

	if len(lagData) < r.config.MinPartitionCount {
		r.logger.Debugf("Consumer group %s has only %d partitions, skipping rebalance", groupID, len(lagData))
		return nil
	}

	partitions := make([]*PartitionInfo, 0, len(lagData))
	for _, lag := range lagData {
		partitions = append(partitions, &PartitionInfo{
			Topic:     lag.Topic,
			Partition: lag.Partition,
			Lag:       lag.Lag,
			Consumer:  lag.ConsumerID,
		})
	}

	if r.config.EnableUnevenDetection && !r.isUnbalanced(partitions) {
		r.logger.Debugf("Consumer group %s is balanced, skipping", groupID)
		return nil
	}

	consumerSet := make(map[string]bool)
	for _, p := range partitions {
		if p.Consumer != "" {
			consumerSet[p.Consumer] = true
		}
	}
	consumers := make([]string, 0, len(consumerSet))
	for c := range consumerSet {
		consumers = append(consumers, c)
	}

	if len(consumers) == 0 {
		r.logger.Debugf("No active consumers in group %s", groupID)
		return nil
	}

	var newAssignments []*PartitionAssignment
	switch r.config.Strategy {
	case StrategyRange:
		newAssignments = r.assignRange(partitions, consumers)
	case StrategyRoundRobin:
		newAssignments = r.assignRoundRobin(partitions, consumers)
	case StrategySticky:
		newAssignments = r.assignSticky(partitions, consumers)
	case StrategyUniform:
		newAssignments = r.assignUniform(partitions, consumers)
	case StrategyKeyRange:
		newAssignments = r.assignKeyRange(partitions, consumers)
	case StrategyKeyHash:
		newAssignments = r.assignKeyHash(partitions, consumers)
	case StrategyKeySticky:
		newAssignments = r.assignKeySticky(partitions, consumers)
	default:
		newAssignments = r.assignRoundRobin(partitions, consumers)
	}

	r.logRebalancePlan(groupID, partitions, newAssignments)

	if !r.config.DryRun {
		r.logger.Infof("Executing rebalance for consumer group %s", groupID)
	}

	return nil
}

func (r *Rebalancer) isUnbalanced(partitions []*PartitionInfo) bool {
	if len(partitions) < 2 {
		return false
	}

	consumerPartitions := make(map[string]int)
	consumerLag := make(map[string]int64)

	for _, p := range partitions {
		if p.Consumer != "" {
			consumerPartitions[p.Consumer]++
			consumerLag[p.Consumer] += p.Lag
		}
	}

	if len(consumerPartitions) < 2 {
		return false
	}

	var minPartitions, maxPartitions int
	first := true
	for _, count := range consumerPartitions {
		if first {
			minPartitions = count
			maxPartitions = count
			first = false
		} else {
			if count < minPartitions {
				minPartitions = count
			}
			if count > maxPartitions {
				maxPartitions = count
			}
		}
	}

	ratio := float64(maxPartitions) / float64(minPartitions)
	return ratio > r.config.UnevenThresholdRatio
}

func (r *Rebalancer) assignRange(partitions []*PartitionInfo, consumers []string) []*PartitionAssignment {
	sort.Slice(partitions, func(i, j int) bool {
		if partitions[i].Topic != partitions[j].Topic {
			return partitions[i].Topic < partitions[j].Topic
		}
		return partitions[i].Partition < partitions[j].Partition
	})

	assignments := make([]*PartitionAssignment, 0, len(partitions))
	partitionsPerConsumer := (len(partitions) + len(consumers) - 1) / len(consumers)

	for i, p := range partitions {
		consumerIndex := i / partitionsPerConsumer
		if consumerIndex >= len(consumers) {
			consumerIndex = len(consumers) - 1
		}
		assignments = append(assignments, &PartitionAssignment{
			Topic:      p.Topic,
			Partition:  p.Partition,
			ConsumerID: consumers[consumerIndex],
		})
	}

	return assignments
}

func (r *Rebalancer) assignRoundRobin(partitions []*PartitionInfo, consumers []string) []*PartitionAssignment {
	sort.Slice(partitions, func(i, j int) bool {
		if partitions[i].Topic != partitions[j].Topic {
			return partitions[i].Topic < partitions[j].Topic
		}
		return partitions[i].Partition < partitions[j].Partition
	})

	assignments := make([]*PartitionAssignment, 0, len(partitions))
	for i, p := range partitions {
		consumerIndex := i % len(consumers)
		assignments = append(assignments, &PartitionAssignment{
			Topic:      p.Topic,
			Partition:  p.Partition,
			ConsumerID: consumers[consumerIndex],
		})
	}

	return assignments
}

func (r *Rebalancer) assignSticky(partitions []*PartitionInfo, consumers []string) []*PartitionAssignment {
	currentAssignments := make(map[string]string)
	for _, p := range partitions {
		if p.Consumer != "" {
			key := fmt.Sprintf("%s-%d", p.Topic, p.Partition)
			currentAssignments[key] = p.Consumer
		}
	}

	consumerLoad := make(map[string]int)
	for _, consumer := range consumers {
		consumerLoad[consumer] = 0
	}
	for _, consumer := range currentAssignments {
		consumerLoad[consumer]++
	}

	assignments := make([]*PartitionAssignment, 0, len(partitions))
	unassigned := make([]*PartitionInfo, 0)

	for _, p := range partitions {
		key := fmt.Sprintf("%s-%d", p.Topic, p.Partition)
		if consumer, ok := currentAssignments[key]; ok {
			assignments = append(assignments, &PartitionAssignment{
				Topic:      p.Topic,
				Partition:  p.Partition,
				ConsumerID: consumer,
			})
		} else {
			unassigned = append(unassigned, p)
		}
	}

	sort.Slice(unassigned, func(i, j int) bool {
		return unassigned[i].Lag > unassigned[j].Lag
	})

	for _, p := range unassigned {
		minLoad := -1
		selectedConsumer := ""
		for _, consumer := range consumers {
			load := consumerLoad[consumer]
			if minLoad == -1 || load < minLoad {
				minLoad = load
				selectedConsumer = consumer
			}
		}

		assignments = append(assignments, &PartitionAssignment{
			Topic:      p.Topic,
			Partition:  p.Partition,
			ConsumerID: selectedConsumer,
		})
		consumerLoad[selectedConsumer]++
	}

	return assignments
}

func (r *Rebalancer) assignUniform(partitions []*PartitionInfo, consumers []string) []*PartitionAssignment {
	consumerLag := make(map[string]int64)
	for _, consumer := range consumers {
		consumerLag[consumer] = 0
	}

	lagByConsumer := make(map[string][]*PartitionInfo)
	for _, consumer := range consumers {
		lagByConsumer[consumer] = make([]*PartitionInfo, 0)
	}

	for _, p := range partitions {
		if p.Consumer != "" {
			lagByConsumer[p.Consumer] = append(lagByConsumer[p.Consumer], p)
			consumerLag[p.Consumer] += p.Lag
		}
	}

	allPartitions := make([]*PartitionInfo, 0, len(partitions))
	for _, p := range partitions {
		allPartitions = append(allPartitions, p)
	}

	sort.Slice(allPartitions, func(i, j int) bool {
		return allPartitions[i].Lag > allPartitions[j].Lag
	})

	assignments := make([]*PartitionAssignment, 0, len(partitions))
	for _, p := range allPartitions {
		minLag := int64(-1)
		selectedConsumer := ""
		for _, consumer := range consumers {
			if minLag == -1 || consumerLag[consumer] < minLag {
				minLag = consumerLag[consumer]
				selectedConsumer = consumer
			}
		}

		assignments = append(assignments, &PartitionAssignment{
			Topic:      p.Topic,
			Partition:  p.Partition,
			ConsumerID: selectedConsumer,
		})
		consumerLag[selectedConsumer] += p.Lag
	}

	return assignments
}

func (r *Rebalancer) logRebalancePlan(groupID string, oldPartitions []*PartitionInfo, newAssignments []*PartitionAssignment) {
	oldAssignmentMap := make(map[string]string)
	for _, p := range oldPartitions {
		key := fmt.Sprintf("%s-%d", p.Topic, p.Partition)
		oldAssignmentMap[key] = p.Consumer
	}

	moves := 0
	for _, a := range newAssignments {
		key := fmt.Sprintf("%s-%d", a.Topic, a.Partition)
		if oldAssignmentMap[key] != a.ConsumerID {
			moves++
		}
	}

	consumerCounts := make(map[string]int)
	for _, a := range newAssignments {
		consumerCounts[a.ConsumerID]++
	}

	r.logger.Infof("Rebalance plan for consumer group %s:", groupID)
	r.logger.Infof("  Total partitions: %d", len(newAssignments))
	r.logger.Infof("  Partitions to move: %d", moves)
	r.logger.Infof("  New assignment distribution:")

	for consumer, count := range consumerCounts {
		r.logger.Infof("    - %s: %d partitions", consumer, count)
	}
}

func (r *Rebalancer) GetBrokerLoad(topic string) ([]*BrokerLoad, error) {
	partitions, err := r.kafkaClient.GetTopicPartitions(topic)
	if err != nil {
		return nil, err
	}

	brokerLoad := make(map[int32]*BrokerLoad)
	for _, p := range partitions {
		if _, ok := brokerLoad[p.Leader]; !ok {
			brokerLoad[p.Leader] = &BrokerLoad{BrokerID: p.Leader}
		}
		brokerLoad[p.Leader].PartitionCount++
	}

	result := make([]*BrokerLoad, 0, len(brokerLoad))
	for _, load := range brokerLoad {
		result = append(result, load)
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].BrokerID < result[j].BrokerID
	})

	return result, nil
}

func (r *Rebalancer) RebalanceTopicPartitions(topic string) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	partitions, err := r.kafkaClient.GetTopicPartitions(topic)
	if err != nil {
		return err
	}

	brokerIDs := make([]int32, 0)
	brokerSet := make(map[int32]bool)
	for _, p := range partitions {
		for _, replica := range p.Replicas {
			if !brokerSet[replica] {
				brokerSet[replica] = true
				brokerIDs = append(brokerIDs, replica)
			}
		}
	}

	sort.Slice(brokerIDs, func(i, j int) bool {
		return brokerIDs[i] < brokerIDs[j]
	})

	if len(brokerIDs) < 2 {
		r.logger.Infof("Topic %s has less than 2 brokers, skipping rebalance", topic)
		return nil
	}

	brokerPartitionCount := make(map[int32]int)
	for _, p := range partitions {
		brokerPartitionCount[p.Leader]++
	}

	r.logger.Infof("Current partition distribution for topic %s:", topic)
	for _, brokerID := range brokerIDs {
		r.logger.Infof("  Broker %d: %d partitions", brokerID, brokerPartitionCount[brokerID])
	}

	return nil
}

func (r *Rebalancer) assignKeyRange(partitions []*PartitionInfo, consumers []string) []*PartitionAssignment {
	topicPartitions := make(map[string][]*PartitionInfo)
	for _, p := range partitions {
		topicPartitions[p.Topic] = append(topicPartitions[p.Topic], p)
	}

	assignments := make([]*PartitionAssignment, 0, len(partitions))
	delimiter := r.config.KeyPrefixDelimiter
	if delimiter == "" {
		delimiter = ":"
	}

	for topic, topicParts := range topicPartitions {
		sort.Slice(topicParts, func(i, j int) bool {
			return topicParts[i].Partition < topicParts[j].Partition
		})

		prefixGroups := r.groupPartitionsByKeyPrefix(topicParts, delimiter)

		consumerIndex := 0
		for _, group := range prefixGroups {
			if consumerIndex >= len(consumers) {
				consumerIndex = 0
			}
			consumer := consumers[consumerIndex]

			for _, p := range group {
				assignments = append(assignments, &PartitionAssignment{
					Topic:      p.Topic,
					Partition:  p.Partition,
					ConsumerID: consumer,
				})
			}
			consumerIndex++
		}

		r.logger.Infof("Topic %s: grouped into %d key prefix groups, assigned to %d consumers",
			topic, len(prefixGroups), len(consumers))
	}

	return assignments
}

func (r *Rebalancer) groupPartitionsByKeyPrefix(partitions []*PartitionInfo, delimiter string) [][]*PartitionInfo {
	groups := make(map[string][]*PartitionInfo)

	for _, p := range partitions {
		prefix := r.extractKeyPrefix(p.Partition, delimiter)
		groups[prefix] = append(groups[prefix], p)
	}

	sortedPrefixes := make([]string, 0, len(groups))
	for prefix := range groups {
		sortedPrefixes = append(sortedPrefixes, prefix)
	}
	sort.Strings(sortedPrefixes)

	result := make([][]*PartitionInfo, 0, len(groups))
	for _, prefix := range sortedPrefixes {
		result = append(result, groups[prefix])
	}

	return result
}

func (r *Rebalancer) extractKeyPrefix(partition int32, delimiter string) string {
	partitionStr := fmt.Sprintf("%d", partition)
	return partitionStr
}

func (r *Rebalancer) assignKeyHash(partitions []*PartitionInfo, consumers []string) []*PartitionAssignment {
	topicPartitions := make(map[string][]*PartitionInfo)
	for _, p := range partitions {
		topicPartitions[p.Topic] = append(topicPartitions[p.Topic], p)
	}

	assignments := make([]*PartitionAssignment, 0, len(partitions))
	consumerCount := int32(len(consumers))

	for _, topicParts := range topicPartitions {
		for _, p := range topicParts {
			hash := r.consistentHash(p.Partition, consumerCount)
			consumer := consumers[hash]

			assignments = append(assignments, &PartitionAssignment{
				Topic:      p.Topic,
				Partition:  p.Partition,
				ConsumerID: consumer,
			})
		}
	}

	return assignments
}

func (r *Rebalancer) consistentHash(partition int32, bucketCount int32) int32 {
	hashValue := uint32(partition) * 2654435761
	return int32(hashValue % uint32(bucketCount))
}

func (r *Rebalancer) assignKeySticky(partitions []*PartitionInfo, consumers []string) []*PartitionAssignment {
	currentAssignments := make(map[string]string)
	keyConsumerMap := make(map[string]string)

	for _, p := range partitions {
		if p.Consumer != "" {
			key := fmt.Sprintf("%s-%d", p.Topic, p.Partition)
			currentAssignments[key] = p.Consumer

			partitionStr := fmt.Sprintf("%d", p.Partition)
			keyConsumerMap[partitionStr] = p.Consumer
		}
	}

	consumerLoad := make(map[string]int)
	for _, consumer := range consumers {
		consumerLoad[consumer] = 0
	}
	for _, consumer := range currentAssignments {
		consumerLoad[consumer]++
	}

	assignments := make([]*PartitionAssignment, 0, len(partitions))
	unassigned := make([]*PartitionInfo, 0)

	for _, p := range partitions {
		key := fmt.Sprintf("%s-%d", p.Topic, p.Partition)
		partitionStr := fmt.Sprintf("%d", p.Partition)

		if consumer, ok := currentAssignments[key]; ok {
			assignments = append(assignments, &PartitionAssignment{
				Topic:      p.Topic,
				Partition:  p.Partition,
				ConsumerID: consumer,
			})
		} else if consumer, ok := keyConsumerMap[partitionStr]; ok {
			assignments = append(assignments, &PartitionAssignment{
				Topic:      p.Topic,
				Partition:  p.Partition,
				ConsumerID: consumer,
			})
			consumerLoad[consumer]++
		} else {
			unassigned = append(unassigned, p)
		}
	}

	sort.Slice(unassigned, func(i, j int) bool {
		return unassigned[i].Lag > unassigned[j].Lag
	})

	for _, p := range unassigned {
		minLoad := -1
		selectedConsumer := ""
		for _, consumer := range consumers {
			load := consumerLoad[consumer]
			if minLoad == -1 || load < minLoad {
				minLoad = load
				selectedConsumer = consumer
			}
		}

		partitionStr := fmt.Sprintf("%d", p.Partition)
		keyConsumerMap[partitionStr] = selectedConsumer

		assignments = append(assignments, &PartitionAssignment{
			Topic:      p.Topic,
			Partition:  p.Partition,
			ConsumerID: selectedConsumer,
		})
		consumerLoad[selectedConsumer]++
	}

	r.logger.Infof("Key-sticky assignment: preserved %d existing mappings, assigned %d new partitions",
		len(currentAssignments), len(unassigned))

	return assignments
}

func (r *Rebalancer) GetKeyPartitionMappings(topic string, partitions []int32) []*KeyPartitionMapping {
	mappings := make([]*KeyPartitionMapping, 0, len(partitions))
	delimiter := r.config.KeyPrefixDelimiter
	if delimiter == "" {
		delimiter = ":"
	}

	for _, partition := range partitions {
		prefix := r.extractKeyPrefix(partition, delimiter)
		mappings = append(mappings, &KeyPartitionMapping{
			KeyPrefix: prefix,
			Partition: partition,
		})
	}

	return mappings
}

func (r *Rebalancer) GetStatus() map[string]interface{} {
	r.mu.Lock()
	defer r.mu.Unlock()

	return map[string]interface{}{
		"strategy":               r.config.Strategy,
		"rebalance_interval":     r.config.RebalanceInterval.String(),
		"last_run":               r.lastRun,
		"dry_run":                r.config.DryRun,
		"enable_uneven_detection": r.config.EnableUnevenDetection,
		"uneven_threshold_ratio": r.config.UnevenThresholdRatio,
		"key_prefix_delimiter":   r.config.KeyPrefixDelimiter,
	}
}
