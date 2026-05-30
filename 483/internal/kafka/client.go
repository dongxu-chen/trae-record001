package kafka

import (
	"fmt"
	"time"

	"github.com/IBM/sarama"
	"kafka-lag-analyzer/internal/config"
)

type Client interface {
	ListConsumerGroups() ([]string, error)
	DescribeConsumerGroup(groupID string) (*ConsumerGroupInfo, error)
	GetTopicPartitions(topic string) ([]int32, error)
	GetPartitionOffset(topic string, partition int32, time int64) (int64, error)
	GetConsumerGroupOffsets(groupID string, topics []string) (*ConsumerGroupOffsets, error)
	GetPartitionLogSize(topic string, partition int32) (int64, error)
	GetTopicPartitionLogSizes(topic string) (map[int32]int64, error)
	Close() error
}

type PartitionInfo struct {
	Topic         string
	Partition     int32
	CurrentOffset int64
	EndOffset     int64
	Lag           int64
	Leader        int32
	Replicas      []int32
	Isr           []int32
}

type ConsumerGroupInfo struct {
	GroupID     string
	State       string
	Members     []GroupMember
	Protocol    string
	ProtocolType string
}

type GroupMember struct {
	ClientID         string
	ConsumerID       string
	Host             string
	Partitions       map[string][]int32
	SessionTimeout   time.Duration
	RebalanceTimeout time.Duration
}

type ConsumerGroupOffsets struct {
	GroupID    string
	Partitions map[string]map[int32]PartitionOffset
}

type PartitionOffset struct {
	Topic          string
	Partition      int32
	Offset         int64
	Metadata       string
	EndOffset      int64
	Lag            int64
	LogSize        int64
	AvgMessageSize float64
	LastCommitTime time.Time
}

type kafkaClient struct {
	adminClient sarama.ClusterAdmin
	client      sarama.Client
	cfg         *config.KafkaConfig
}

func NewClient(cfg *config.KafkaConfig) (Client, error) {
	config := sarama.NewConfig()
	config.Net.DialTimeout = cfg.Timeout
	config.Net.ReadTimeout = cfg.Timeout
	config.Net.WriteTimeout = cfg.Timeout
	config.Version = sarama.V2_8_0_0

	if cfg.Username != "" && cfg.Password != "" {
		config.Net.SASL.Enable = true
		config.Net.SASL.Mechanism = sarama.SASLTypePlaintext
		config.Net.SASL.User = cfg.Username
		config.Net.SASL.Password = cfg.Password
	}

	if cfg.TLSEnabled {
		config.Net.TLS.Enable = true
	}

	adminClient, err := sarama.NewClusterAdmin(cfg.Brokers, config)
	if err != nil {
		return nil, fmt.Errorf("failed to create admin client: %w", err)
	}

	client, err := sarama.NewClient(cfg.Brokers, config)
	if err != nil {
		adminClient.Close()
		return nil, fmt.Errorf("failed to create kafka client: %w", err)
	}

	return &kafkaClient{
		adminClient: adminClient,
		client:      client,
		cfg:         cfg,
	}, nil
}

func (k *kafkaClient) ListConsumerGroups() ([]string, error) {
	groups, err := k.adminClient.ListConsumerGroups()
	if err != nil {
		return nil, fmt.Errorf("failed to list consumer groups: %w", err)
	}

	groupIDs := make([]string, 0, len(groups))
	for groupID := range groups {
		if len(k.cfg.ConsumerGroups) == 0 {
			groupIDs = append(groupIDs, groupID)
		} else {
			for _, allowed := range k.cfg.ConsumerGroups {
				if groupID == allowed {
					groupIDs = append(groupIDs, groupID)
					break
				}
			}
		}
	}

	return groupIDs, nil
}

func (k *kafkaClient) DescribeConsumerGroup(groupID string) (*ConsumerGroupInfo, error) {
	describeResp, err := k.adminClient.DescribeConsumerGroups([]string{groupID})
	if err != nil {
		return nil, fmt.Errorf("failed to describe consumer group %s: %w", groupID, err)
	}

	if len(describeResp) == 0 {
		return nil, fmt.Errorf("consumer group %s not found", groupID)
	}

	desc := describeResp[0]
	members := make([]GroupMember, 0, len(desc.Members))

	for _, member := range desc.Members {
		memberAssignment, err := member.GetMemberAssignment()
		if err != nil {
			continue
		}

		partitions := make(map[string][]int32)
		for topic, parts := range memberAssignment.Topics {
			partitions[topic] = parts
		}

		members = append(members, GroupMember{
			ClientID:         member.ClientId,
			ConsumerID:       member.ClientHost,
			Host:             member.ClientHost,
			Partitions:       partitions,
			SessionTimeout:   time.Duration(desc.SessionTimeout) * time.Millisecond,
			RebalanceTimeout: time.Duration(desc.RebalanceTimeout) * time.Millisecond,
		})
	}

	return &ConsumerGroupInfo{
		GroupID:      desc.GroupId,
		State:        desc.State,
		Members:      members,
		Protocol:     desc.Protocol,
		ProtocolType: desc.ProtocolType,
	}, nil
}

func (k *kafkaClient) GetTopicPartitions(topic string) ([]int32, error) {
	partitions, err := k.client.Partitions(topic)
	if err != nil {
		return nil, fmt.Errorf("failed to get partitions for topic %s: %w", topic, err)
	}

	return partitions, nil
}

func (k *kafkaClient) GetPartitionOffset(topic string, partition int32, time int64) (int64, error) {
	offset, err := k.client.GetOffset(topic, partition, time)
	if err != nil {
		return 0, fmt.Errorf("failed to get offset for topic %s partition %d: %w", topic, partition, err)
	}

	return offset, nil
}

func (k *kafkaClient) GetConsumerGroupOffsets(groupID string, topics []string) (*ConsumerGroupOffsets, error) {
	offsetFetchResp, err := k.adminClient.ListConsumerGroupOffsets(groupID, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to list consumer group offsets for %s: %w", groupID, err)
	}

	offsets := &ConsumerGroupOffsets{
		GroupID:    groupID,
		Partitions: make(map[string]map[int32]PartitionOffset),
	}

	for topic, partitionMap := range offsetFetchResp.Blocks {
		if len(topics) > 0 {
			found := false
			for _, t := range topics {
				if t == topic {
					found = true
					break
				}
			}
			if !found {
				continue
			}
		}

		if _, ok := offsets.Partitions[topic]; !ok {
			offsets.Partitions[topic] = make(map[int32]PartitionOffset)
		}

		for partition, block := range partitionMap {
			endOffset, err := k.GetPartitionOffset(topic, partition, sarama.OffsetNewest)
			if err != nil {
				endOffset = -1
			}

			lag := int64(0)
			if endOffset >= 0 && block.Offset >= 0 {
				lag = endOffset - block.Offset
				if lag < 0 {
					lag = 0
				}
			}

			offsets.Partitions[topic][partition] = PartitionOffset{
				Topic:          topic,
				Partition:      partition,
				Offset:         block.Offset,
				Metadata:       block.Metadata,
				EndOffset:      endOffset,
				Lag:            lag,
				LastCommitTime: time.Now(),
			}
		}
	}

	return offsets, nil
}

func (k *kafkaClient) Close() error {
	if err := k.adminClient.Close(); err != nil {
		k.client.Close()
		return err
	}
	return k.client.Close()
}

func (k *kafkaClient) GetPartitionLogSize(topic string, partition int32) (int64, error) {
	replica, err := k.client.Leader(topic, partition)
	if err != nil {
		return 0, fmt.Errorf("failed to get leader for %s-%d: %w", topic, partition, err)
	}

	req := &sarama.DescribeLogDirsRequest{
		TopicPartitions: map[string][]int32{
			topic: {partition},
		},
	}

	resp, err := replica.DescribeLogDirs(req)
	if err != nil {
		return 0, fmt.Errorf("failed to describe log dirs: %w", err)
	}

	for _, dir := range resp.LogDirs {
		for tp, partitionMeta := range dir.Partitions {
			if tp.Topic == topic && tp.Partition == partition {
				return partitionMeta.Size, nil
			}
		}
	}

	return 0, nil
}

func (k *kafkaClient) GetTopicPartitionLogSizes(topic string) (map[int32]int64, error) {
	partitions, err := k.client.Partitions(topic)
	if err != nil {
		return nil, fmt.Errorf("failed to get partitions for %s: %w", topic, err)
	}

	sizes := make(map[int32]int64, len(partitions))
	for _, p := range partitions {
		size, err := k.GetPartitionLogSize(topic, p)
		if err != nil {
			sizes[p] = 0
			continue
		}
		sizes[p] = size
	}

	return sizes, nil
}
