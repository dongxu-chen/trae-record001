package pulsar

import (
	"context"
	"fmt"
	"time"

	"github.com/apache/pulsar-client-go/pulsar"
	"pulsar-backlog-manager/pkg/config"
)

type Client struct {
	client    pulsar.Client
	adminURL  string
	consumers map[string]pulsar.Consumer
	producers map[string]pulsar.Producer
}

type TopicStats struct {
	TopicName          string
	MsgBacklog         int64
	MsgRateIn          float64
	MsgRateOut         float64
	AvgMsgSize         float64
	StorageSize        int64
	ProducerCount      int
	SubscriptionCount  int
}

type ConsumerInfo struct {
	Name      string
	Topic     string
	Backlog   int64
}

func NewClient(cfg config.PulsarConfig) (*Client, error) {
	options := pulsar.ClientOptions{
		URL: cfg.URL,
	}
	if cfg.Token != "" {
		options.Authentication = pulsar.NewAuthenticationToken(cfg.Token)
	}
	if cfg.TrustCertsFile != "" {
		options.TLSTrustCertsFilePath = cfg.TrustCertsFile
	}

	client, err := pulsar.NewClient(options)
	if err != nil {
		return nil, fmt.Errorf("failed to create Pulsar client: %w", err)
	}

	return &Client{
		client:    client,
		adminURL:  cfg.AdminURL,
		consumers: make(map[string]pulsar.Consumer),
		producers: make(map[string]pulsar.Producer),
	}, nil
}

func (c *Client) Close() {
	for _, consumer := range c.consumers {
		consumer.Close()
	}
	for _, producer := range c.producers {
		producer.Close()
	}
	c.client.Close()
}

func (c *Client) GetTopicStats(topic string) (*TopicStats, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	reader, err := c.client.CreateReader(pulsar.ReaderOptions{
		Topic:          topic,
		StartMessageID: pulsar.EarliestMessageID(),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create reader: %w", err)
	}
	defer reader.Close()

	stats := &TopicStats{
		TopicName: topic,
	}

	partitions, err := c.client.TopicPartitions(topic)
	if err == nil {
		stats.SubscriptionCount = len(partitions)
	}

	return stats, nil
}

func (c *Client) CreateConsumer(topic, subscription, consumerName string) (pulsar.Consumer, error) {
	key := fmt.Sprintf("%s-%s-%s", topic, subscription, consumerName)
	if consumer, exists := c.consumers[key]; exists {
		return consumer, nil
	}

	consumer, err := c.client.Subscribe(pulsar.ConsumerOptions{
		Topic:               topic,
		SubscriptionName:    subscription,
		Name:                consumerName,
		Type:                pulsar.Shared,
		EnableRetry:         true,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create consumer: %w", err)
	}

	c.consumers[key] = consumer
	return consumer, nil
}

func (c *Client) RemoveConsumer(topic, subscription, consumerName string) {
	key := fmt.Sprintf("%s-%s-%s", topic, subscription, consumerName)
	if consumer, exists := c.consumers[key]; exists {
		consumer.Close()
		delete(c.consumers, key)
	}
}

func (c *Client) GetConsumerCount(topic, subscription string) int {
	count := 0
	prefix := fmt.Sprintf("%s-%s-", topic, subscription)
	for key := range c.consumers {
		if len(key) >= len(prefix) && key[:len(prefix)] == prefix {
			count++
		}
	}
	return count
}

func (c *Client) CreateProducer(topic string, maxPublishRate float64) (pulsar.Producer, error) {
	if producer, exists := c.producers[topic]; exists {
		return producer, nil
	}

	options := pulsar.ProducerOptions{
		Topic:           topic,
		DisableBatching: false,
	}
	if maxPublishRate > 0 {
		options.BatchingMaxPublishDelay = time.Duration(1000/maxPublishRate) * time.Millisecond
	}

	producer, err := c.client.CreateProducer(options)
	if err != nil {
		return nil, fmt.Errorf("failed to create producer: %w", err)
	}

	c.producers[topic] = producer
	return producer, nil
}

func (c *Client) GetAllTopics() ([]string, error) {
	return []string{}, nil
}

func (c *Client) GetNativeClient() pulsar.Client {
	return c.client
}
