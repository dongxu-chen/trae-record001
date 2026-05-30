package rabbitmq

import (
	"bytes"
	"crypto/tls"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

type Client struct {
	baseURL    string
	username   string
	password   string
	httpClient *http.Client
}

type Node struct {
	Name          string `json:"name"`
	Running       bool   `json:"running"`
	DiskFree      int64  `json:"disk_free"`
	MemUsed       int64  `json:"mem_used"`
	MemLimit      int64  `json:"mem_limit"`
	Uptime        int64  `json:"uptime"`
	ErlangVersion string `json:"erlang_version"`
}

type Queue struct {
	Name                string       `json:"name"`
	Vhost               string       `json:"vhost"`
	Node                string       `json:"node"`
	State               string       `json:"state"`
	Messages            int64        `json:"messages"`
	MessagesReady       int64        `json:"messages_ready"`
	MessagesUnack       int64        `json:"messages_unacknowledged"`
	Consumers           int64        `json:"consumers"`
	ConsumerUtilisation float64      `json:"consumer_utilisation"`
	Memory              int64        `json:"memory"`
	Policy              string       `json:"policy"`
	MessageStats        MessageStats `json:"message_stats"`
}

type MessageStats struct {
	PublishDetails RateDetails `json:"publish_details"`
	DeliverDetails RateDetails `json:"deliver_details"`
	AckDetails     RateDetails `json:"ack_details"`
}

type RateDetails struct {
	Rate float64 `json:"rate"`
}

type Policy struct {
	Name       string                 `json:"name"`
	Vhost      string                 `json:"vhost"`
	Pattern    string                 `json:"pattern"`
	Definition map[string]interface{} `json:"definition"`
	Priority   int                    `json:"priority"`
	ApplyTo    string                 `json:"apply-to"`
}

type Consumer struct {
	Queue      QueueRef `json:"queue"`
	Channel    ChannelRef `json:"channel"`
	ConsumerTag string   `json:"consumer_tag"`
	Exclusive  bool     `json:"exclusive"`
	AckRequired bool    `json:"ack_required"`
	PrefetchCount int   `json:"prefetch_count"`
}

type QueueRef struct {
	Name  string `json:"name"`
	Vhost string `json:"vhost"`
}

type ChannelRef struct {
	Name  string `json:"name"`
	Node  string `json:"node"`
}

type ClientConfig struct {
	BaseURL  string
	Username string
	Password string
	Timeout  time.Duration
}

func NewClient(config ClientConfig) *Client {
	baseURL := strings.TrimSuffix(config.BaseURL, "/")
	return &Client{
		baseURL:  baseURL,
		username: config.Username,
		password: config.Password,
		httpClient: &http.Client{
			Timeout: config.Timeout,
			Transport: &http.Transport{
				TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
			},
		},
	}
}

func (c *Client) basicAuth() string {
	auth := c.username + ":" + c.password
	return "Basic " + base64.StdEncoding.EncodeToString([]byte(auth))
}

func (c *Client) doRequest(method, path string, body interface{}, result interface{}) error {
	url := c.baseURL + path

	var reqBody io.Reader
	if body != nil {
		jsonBody, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("marshal body failed: %w", err)
		}
		reqBody = bytes.NewBuffer(jsonBody)
	}

	req, err := http.NewRequest(method, url, reqBody)
	if err != nil {
		return fmt.Errorf("create request failed: %w", err)
	}

	req.Header.Set("Authorization", c.basicAuth())
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		respBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("API error: %s, body: %s", resp.Status, string(respBody))
	}

	if result != nil {
		if err := json.NewDecoder(resp.Body).Decode(result); err != nil {
			return fmt.Errorf("decode response failed: %w", err)
		}
	}

	return nil
}

func (c *Client) GetNodes() ([]Node, error) {
	var nodes []Node
	err := c.doRequest("GET", "/api/nodes", nil, &nodes)
	return nodes, err
}

func (c *Client) GetQueues() ([]Queue, error) {
	var queues []Queue
	err := c.doRequest("GET", "/api/queues", nil, &queues)
	return queues, err
}

func (c *Client) GetQueuesByVhost(vhost string) ([]Queue, error) {
	encodedVhost := encodeVhost(vhost)
	var queues []Queue
	err := c.doRequest("GET", "/api/queues/"+encodedVhost, nil, &queues)
	return queues, err
}

func (c *Client) GetQueue(vhost, queueName string) (*Queue, error) {
	encodedVhost := encodeVhost(vhost)
	var queue Queue
	err := c.doRequest("GET", fmt.Sprintf("/api/queues/%s/%s", encodedVhost, queueName), nil, &queue)
	if err != nil {
		return nil, err
	}
	return &queue, nil
}

func (c *Client) GetPolicies(vhost string) ([]Policy, error) {
	encodedVhost := encodeVhost(vhost)
	var policies []Policy
	err := c.doRequest("GET", "/api/policies/"+encodedVhost, nil, &policies)
	return policies, err
}

func (c *Client) SetPolicy(vhost, policyName string, policy Policy) error {
	encodedVhost := encodeVhost(vhost)
	path := fmt.Sprintf("/api/policies/%s/%s", encodedVhost, policyName)
	return c.doRequest("PUT", path, policy, nil)
}

func (c *Client) DeletePolicy(vhost, policyName string) error {
	encodedVhost := encodeVhost(vhost)
	path := fmt.Sprintf("/api/policies/%s/%s", encodedVhost, policyName)
	return c.doRequest("DELETE", path, nil, nil)
}

func (c *Client) GetConsumers(vhost string) ([]Consumer, error) {
	encodedVhost := encodeVhost(vhost)
	var consumers []Consumer
	err := c.doRequest("GET", "/api/consumers/"+encodedVhost, nil, &consumers)
	return consumers, err
}

func (c *Client) GetConsumersByQueue(vhost, queueName string) ([]Consumer, error) {
	consumers, err := c.GetConsumers(vhost)
	if err != nil {
		return nil, err
	}

	var result []Consumer
	for _, consumer := range consumers {
		if consumer.Queue.Name == queueName {
			result = append(result, consumer)
		}
	}
	return result, nil
}

func (c *Client) GetQueueConsumersCount(vhost, queueName string) (int64, error) {
	queue, err := c.GetQueue(vhost, queueName)
	if err != nil {
		return 0, err
	}
	return queue.Consumers, nil
}

func (c *Client) SetConsumerLimit(vhost, queueName string, limit int) error {
	policyName := fmt.Sprintf("consumer-limit-%s", queueName)
	policy := Policy{
		Name:    policyName,
		Vhost:   vhost,
		Pattern: fmt.Sprintf("^%s$", queueName),
		Definition: map[string]interface{}{
			"max-length":         limit,
			"consumer-timeout":   3600000,
		},
		Priority: 50,
		ApplyTo:  "queues",
	}

	if limit == 0 {
		policy.Definition["consumer-prefetch-count"] = 0
		policy.Definition["consumer-priority"] = -100
	}

	return c.SetPolicy(vhost, policyName, policy)
}

func (c *Client) RemoveConsumerLimit(vhost, queueName string) error {
	policyName := fmt.Sprintf("consumer-limit-%s", queueName)
	return c.DeletePolicy(vhost, policyName)
}

func (c *Client) PauseQueueConsumers(vhost, queueName string) error {
	policyName := fmt.Sprintf("pause-consumers-%s", queueName)
	policy := Policy{
		Name:    policyName,
		Vhost:   vhost,
		Pattern: fmt.Sprintf("^%s$", queueName),
		Definition: map[string]interface{}{
			"consumer-priority": -255,
			"queue-mode":        "lazy",
		},
		Priority: 150,
		ApplyTo:  "queues",
	}
	return c.SetPolicy(vhost, policyName, policy)
}

func (c *Client) ResumeQueueConsumers(vhost, queueName string) error {
	policyName := fmt.Sprintf("pause-consumers-%s", queueName)
	return c.DeletePolicy(vhost, policyName)
}

func (c *Client) SetQueueMasterLocation(vhost, queueName, targetNode string) error {
	policyName := fmt.Sprintf("migrate-%s", queueName)
	policy := Policy{
		Name:    policyName,
		Vhost:   vhost,
		Pattern: fmt.Sprintf("^%s$", queueName),
		Definition: map[string]interface{}{
			"ha-mode":      "nodes",
			"ha-params":    []string{targetNode},
			"ha-sync-mode": "automatic",
		},
		Priority: 200,
		ApplyTo:  "queues",
	}
	return c.SetPolicy(vhost, policyName, policy)
}

func (c *Client) RemoveQueueMasterLocationPolicy(vhost, queueName string) error {
	policyName := fmt.Sprintf("migrate-%s", queueName)
	return c.DeletePolicy(vhost, policyName)
}

func (c *Client) GetOverview() (map[string]interface{}, error) {
	var overview map[string]interface{}
	err := c.doRequest("GET", "/api/overview", nil, &overview)
	return overview, err
}

func (c *Client) WaitForQueueSync(vhost, queueName string, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		queue, err := c.GetQueue(vhost, queueName)
		if err != nil {
			return err
		}

		if queue.State == "running" && queue.MessagesReady == 0 {
			return nil
		}

		time.Sleep(500 * time.Millisecond)
	}
	return fmt.Errorf("timeout waiting for queue sync")
}

func (c *Client) IsQueueOnNode(vhost, queueName, nodeName string) (bool, error) {
	queue, err := c.GetQueue(vhost, queueName)
	if err != nil {
		return false, err
	}
	return queue.Node == nodeName, nil
}

func encodeVhost(vhost string) string {
	if vhost == "/" {
		return "%2F"
	}
	return vhost
}
