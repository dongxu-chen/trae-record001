package kafka

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/IBM/sarama"
	"github.com/sirupsen/logrus"
)

type Client struct {
	admin     sarama.ClusterAdmin
	client    sarama.Client
	brokers   []string
	config    *sarama.Config
	logger    *logrus.Logger
	mu        sync.RWMutex
}

type ConsumerGroupLag struct {
	GroupID        string
	Topic          string
	Partition      int32
	CurrentOffset  int64
	EndOffset      int64
	Lag            int64
	ConsumerID     string
	ClientHost     string
}

type TopicPartitionInfo struct {
	Topic     string
	Partition int32
	Leader    int32
	Replicas  []int32
	ISR       []int32
}

func NewClient(brokers []string, logger *logrus.Logger) (*Client, error) {
	config := sarama.NewConfig()
	config.Version = sarama.V2_8_0_0
	config.Admin.Timeout = 30 * time.Second
	config.Metadata.Retry.Max = 3
	config.Metadata.Retry.Backoff = 500 * time.Millisecond

	client, err := sarama.NewClient(brokers, config)
	if err != nil {
		return nil, fmt.Errorf("failed to create kafka client: %w", err)
	}

	admin, err := sarama.NewClusterAdmin(brokers, config)
	if err != nil {
		client.Close()
		return nil, fmt.Errorf("failed to create kafka admin: %w", err)
	}

	return &Client{
		admin:   admin,
		client:  client,
		brokers: brokers,
		config:  config,
		logger:  logger,
	}, nil
}

func (c *Client) Close() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.admin != nil {
		c.admin.Close()
	}
	if c.client != nil {
		c.client.Close()
	}
	return nil
}

func (c *Client) GetConsumerGroupLag(groupID string) ([]*ConsumerGroupLag, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	groupDesc, err := c.admin.DescribeConsumerGroups([]string{groupID})
	if err != nil {
		return nil, fmt.Errorf("failed to describe consumer group: %w", err)
	}

	if len(groupDesc) == 0 {
		return nil, fmt.Errorf("consumer group %s not found", groupID)
	}

	group := groupDesc[0]
	if group.Err != sarama.ErrNoError {
		return nil, fmt.Errorf("consumer group error: %s", group.Err)
	}

	offsets, err := c.admin.ListConsumerGroupOffsets(groupID, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to list consumer group offsets: %w", err)
	}

	var result []*ConsumerGroupLag

	for topic, partitions := range offsets.Blocks {
		partitionOffsets, err := c.getTopicEndOffsets(topic)
		if err != nil {
			c.logger.Warnf("Failed to get end offsets for topic %s: %v", topic, err)
			continue
		}

		for partition, block := range partitions {
			endOffset, ok := partitionOffsets[partition]
			if !ok {
				continue
			}

			lag := endOffset - block.Offset
			if block.Offset == -1 {
				lag = 0
			}

			consumerID := ""
			clientHost := ""
			for _, member := range group.Members {
				assignments, err := member.GetMemberAssignment()
				if err != nil {
					continue
				}
				if topicPartitions, ok := assignments.Topics[topic]; ok {
					for _, p := range topicPartitions {
						if p == partition {
							consumerID = member.ClientID
							clientHost = member.ClientHost
							break
						}
					}
				}
			}

			result = append(result, &ConsumerGroupLag{
				GroupID:       groupID,
				Topic:         topic,
				Partition:     partition,
				CurrentOffset: block.Offset,
				EndOffset:     endOffset,
				Lag:           lag,
				ConsumerID:    consumerID,
				ClientHost:    clientHost,
			})
		}
	}

	return result, nil
}

func (c *Client) getTopicEndOffsets(topic string) (map[int32]int64, error) {
	partitions, err := c.client.Partitions(topic)
	if err != nil {
		return nil, err
	}

	result := make(map[int32]int64)
	for _, partition := range partitions {
		offset, err := c.client.GetOffset(topic, partition, sarama.OffsetNewest)
		if err != nil {
			return nil, err
		}
		result[partition] = offset
	}

	return result, nil
}

func (c *Client) GetTotalLag(groupID string) (int64, error) {
	lags, err := c.GetConsumerGroupLag(groupID)
	if err != nil {
		return 0, err
	}

	var totalLag int64
	for _, lag := range lags {
		totalLag += lag.Lag
	}

	return totalLag, nil
}

func (c *Client) GetTopicPartitions(topic string) ([]TopicPartitionInfo, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	partitions, err := c.client.Partitions(topic)
	if err != nil {
		return nil, fmt.Errorf("failed to get partitions for topic %s: %w", topic, err)
	}

	var result []TopicPartitionInfo
	for _, partition := range partitions {
		leader, err := c.client.Leader(topic, partition)
		if err != nil {
			return nil, err
		}

		replicas, err := c.client.Replicas(topic, partition)
		if err != nil {
			return nil, err
		}

		isr, err := c.client.InSyncReplicas(topic, partition)
		if err != nil {
			return nil, err
		}

		result = append(result, TopicPartitionInfo{
			Topic:     topic,
			Partition: partition,
			Leader:    int32(leader.ID()),
			Replicas:  int32Slice(replicas),
			ISR:       int32Slice(isr),
		})
	}

	return result, nil
}

func int32Slice(brokers []*sarama.Broker) []int32 {
	result := make([]int32, len(brokers))
	for i, b := range brokers {
		result[i] = int32(b.ID())
	}
	return result
}

func (c *Client) GetConsumerGroupMembers(groupID string) (int, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	groups, err := c.admin.DescribeConsumerGroups([]string{groupID})
	if err != nil {
		return 0, err
	}

	if len(groups) == 0 {
		return 0, nil
	}

	return len(groups[0].Members), nil
}

func (c *Client) ListConsumerGroups() (map[string]string, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	return c.admin.ListConsumerGroups()
}

func (c *Client) CreateTopic(topic string, partitions int32, replicationFactor int16) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	detail := &sarama.TopicDetail{
		NumPartitions:     partitions,
		ReplicationFactor: replicationFactor,
	}

	return c.admin.CreateTopic(topic, detail, false)
}

func (c *Client) DeleteTopic(topic string) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	return c.admin.DeleteTopic(topic)
}

func (c *Client) DescribeTopics(topics []string) ([]*sarama.TopicMetadata, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	return c.admin.DescribeTopics(topics)
}

type PartitionReassignment struct {
	Topic     string
	Partition int32
	Replicas  []int32
}

func (c *Client) ReassignPartitions(reassignments []*PartitionReassignment) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	topicMap := make(map[string][]int32)
	for _, r := range reassignments {
		topicMap[r.Topic] = append(topicMap[r.Topic], r.Partition)
	}

	_, err := c.admin.AlterPartitionReassignments(topicMap)
	return err
}

func (c *Client) GetPartitionReassignments(topics []string) (*sarama.PartitionReplicaReassignmentsResponse, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	topicMap := make(map[string][]int32)
	for _, topic := range topics {
		topicMap[topic] = nil
	}

	return c.admin.ListPartitionReassignments(topicMap)
}

func (c *Client) AlterPartitionReassignments(topic string, partition int32, replicas []int32) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	topicMap := make(map[string][]*sarama.PartitionReassignment)
	topicMap[topic] = []*sarama.PartitionReassignment{
		{
			Partition: partition,
			Replicas:  replicas,
		},
	}

	_, err := c.admin.AlterPartitionAssignments(topicMap)
	return err
}

func (c *Client) GetConsumerGroupState(groupID string) (string, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	groups, err := c.admin.DescribeConsumerGroups([]string{groupID})
	if err != nil {
		return "", err
	}

	if len(groups) == 0 {
		return "Unknown", nil
	}

	return groups[0].State, nil
}

func (c *Client) ResetConsumerGroupOffsets(groupID string, topic string, partitions []int32, offset int64) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	offsetManager, err := sarama.NewOffsetManagerFromClient(groupID, c.client)
	if err != nil {
		return err
	}
	defer offsetManager.Close()

	for _, partition := range partitions {
		partitionManager, err := offsetManager.ManagePartition(topic, partition)
		if err != nil {
			return err
		}
		partitionManager.MarkOffset(offset, "")
		partitionManager.Close()
	}

	return offsetManager.Commit()
}

func (c *Client) GetBrokerList() []string {
	return c.brokers
}

func (c *Client) HealthCheck(ctx context.Context) error {
	c.mu.RLock()
	defer c.mu.RUnlock()

	_, err := c.admin.DescribeCluster()
	return err
}
