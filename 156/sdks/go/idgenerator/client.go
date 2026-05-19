package idgenerator

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type Client struct {
	BaseURL    string
	HTTPClient *http.Client
}

type IDResponse struct {
	Success      bool   `json:"success"`
	ID           string `json:"id"`
	WorkerID     int    `json:"workerId"`
	BizType      string `json:"bizType"`
	FormattedID  string `json:"formattedId"`
	ShortID      string `json:"shortId"`
	HumanReadable string `json:"humanReadable"`
	Error        string `json:"error"`
}

type BatchResponse struct {
	Success bool     `json:"success"`
	Count   int      `json:"count"`
	IDs     []string `json:"ids"`
	Error   string   `json:"error"`
}

type ParseResponse struct {
	Success bool `json:"success"`
	Data    struct {
		Snowflake struct {
			ID        string `json:"id"`
			Timestamp int64  `json:"timestamp"`
			Date      string `json:"date"`
			WorkerID  int    `json:"workerId"`
			Sequence  int    `json:"sequence"`
		} `json:"snowflake"`
		Formatted struct {
			Prefix    string `json:"prefix"`
			Timestamp int64  `json:"timestamp"`
			ID        string `json:"id"`
			Checksum  string `json:"checksum"`
			Valid     bool   `json:"valid"`
		} `json:"formatted"`
	} `json:"data"`
	Error string `json:"error"`
}

type SegmentStatusResponse struct {
	Success bool `json:"success"`
	Data    map[string]struct {
		BizType string `json:"bizType"`
		Current struct {
			Start    string `json:"start"`
			End      string `json:"end"`
			Remaining int   `json:"remaining"`
		} `json:"current"`
		Next struct {
			Start string `json:"start"`
			End   string `json:"end"`
		} `json:"next"`
		IsLoadingNext bool `json:"isLoadingNext"`
	} `json:"data"`
	Error string `json:"error"`
}

type WorkerCapacityResponse struct {
	Success bool `json:"success"`
	Data    struct {
		Current   int `json:"current"`
		Max       int `json:"max"`
		Remaining int `json:"remaining"`
	} `json:"data"`
	Error string `json:"error"`
}

type BenchmarkResponse struct {
	Success bool `json:"success"`
	Benchmark struct {
		Type               string `json:"type"`
		Count              int    `json:"count"`
		ElapsedMs          float64 `json:"elapsedMs"`
		ThroughputPerSecond int    `json:"throughputPerSecond"`
		AvgNsPerId         int    `json:"avgNsPerId"`
	} `json:"benchmark"`
	Error string `json:"error"`
}

func NewClient(baseURL string) *Client {
	return &Client{
		BaseURL: baseURL,
		HTTPClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

func (c *Client) NextID(bizType string, format bool) (*IDResponse, error) {
	url := fmt.Sprintf("%s/api/id/next", c.BaseURL)
	if bizType != "" || format {
		url += "?"
		if bizType != "" {
			url += fmt.Sprintf("bizType=%s", bizType)
		}
		if format {
			if bizType != "" {
				url += "&"
			}
			url += "format=1"
		}
	}

	resp, err := c.HTTPClient.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result IDResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	if !result.Success {
		return nil, fmt.Errorf(result.Error)
	}

	return &result, nil
}

func (c *Client) NextSegmentID(bizType string, format bool, step int) (*IDResponse, error) {
	url := fmt.Sprintf("%s/api/id/segment/next", c.BaseURL)
	params := []string{}
	if bizType != "" {
		params = append(params, fmt.Sprintf("bizType=%s", bizType))
	}
	if format {
		params = append(params, "format=1")
	}
	if step > 0 {
		params = append(params, fmt.Sprintf("step=%d", step))
	}
	if len(params) > 0 {
		url += "?" + joinParams(params)
	}

	resp, err := c.HTTPClient.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result IDResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	if !result.Success {
		return nil, fmt.Errorf(result.Error)
	}

	return &result, nil
}

func (c *Client) Batch(count int, bizType string, format bool) (*BatchResponse, error) {
	url := fmt.Sprintf("%s/api/id/batch/%d", c.BaseURL, count)
	params := []string{}
	if bizType != "" {
		params = append(params, fmt.Sprintf("bizType=%s", bizType))
	}
	if format {
		params = append(params, "format=1")
	}
	if len(params) > 0 {
		url += "?" + joinParams(params)
	}

	resp, err := c.HTTPClient.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result BatchResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	if !result.Success {
		return nil, fmt.Errorf(result.Error)
	}

	return &result, nil
}

func (c *Client) Parse(id string) (*ParseResponse, error) {
	url := fmt.Sprintf("%s/api/id/parse/%s", c.BaseURL, id)

	resp, err := c.HTTPClient.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result ParseResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	if !result.Success {
		return nil, fmt.Errorf(result.Error)
	}

	return &result, nil
}

func (c *Client) GetSegmentStatus(bizType string) (*SegmentStatusResponse, error) {
	url := fmt.Sprintf("%s/api/id/segment/status", c.BaseURL)
	if bizType != "" {
		url += fmt.Sprintf("?bizType=%s", bizType)
	}

	resp, err := c.HTTPClient.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result SegmentStatusResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	if !result.Success {
		return nil, fmt.Errorf(result.Error)
	}

	return &result, nil
}

func (c *Client) GetWorkerCapacity() (*WorkerCapacityResponse, error) {
	url := fmt.Sprintf("%s/api/id/worker/capacity", c.BaseURL)

	resp, err := c.HTTPClient.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result WorkerCapacityResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	if !result.Success {
		return nil, fmt.Errorf(result.Error)
	}

	return &result, nil
}

func (c *Client) ExpandWorkerCapacity(targetCount int) (*WorkerCapacityResponse, error) {
	url := fmt.Sprintf("%s/api/id/worker/expand", c.BaseURL)
	
	payload := map[string]int{"targetCount": targetCount}
	jsonPayload, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}

	resp, err := c.HTTPClient.Post(url, "application/json", bytes.NewBuffer(jsonPayload))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result WorkerCapacityResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	if !result.Success {
		return nil, fmt.Errorf(result.Error)
	}

	return &result, nil
}

func (c *Client) Benchmark(count int, idType string) (*BenchmarkResponse, error) {
	url := fmt.Sprintf("%s/api/id/benchmark/%d", c.BaseURL, count)
	if idType != "" {
		url += fmt.Sprintf("?type=%s", idType)
	}

	resp, err := c.HTTPClient.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result BenchmarkResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	if !result.Success {
		return nil, fmt.Errorf(result.Error)
	}

	return &result, nil
}

func joinParams(params []string) string {
	if len(params) == 0 {
		return ""
	}
	result := params[0]
	for i := 1; i < len(params); i++ {
		result += "&" + params[i]
	}
	return result
}