package query

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/prometheus/prometheus/promql/parser"
)

type Service struct {
	thanosEndpoint string
	client         *http.Client
}

func NewService(thanosEndpoint string) *Service {
	return &Service{
		thanosEndpoint: thanosEndpoint,
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

type QueryResult struct {
	Status string `json:"status"`
	Data   Data   `json:"data"`
	Error  string `json:"error,omitempty"`
}

type Data struct {
	ResultType string          `json:"resultType"`
	Result     json.RawMessage `json:"result"`
}

type VectorResult []VectorSample

type VectorSample struct {
	Metric map[string]string `json:"metric"`
	Value  []interface{}     `json:"value"`
}

type MatrixResult []MatrixSeries

type MatrixSeries struct {
	Metric map[string]string `json:"metric"`
	Values [][]interface{}   `json:"values"`
}

func (s *Service) Query(ctx context.Context, query, timeStr string) (*QueryResult, error) {
	params := url.Values{}
	params.Set("query", query)
	if timeStr != "" {
		params.Set("time", timeStr)
	}

	url := fmt.Sprintf("%s/api/v1/query?%s", s.thanosEndpoint, params.Encode())

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to execute query: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var result QueryResult
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return &result, nil
}

func (s *Service) QueryRange(ctx context.Context, query, start, end, step string) (*QueryResult, error) {
	params := url.Values{}
	params.Set("query", query)
	params.Set("start", start)
	params.Set("end", end)
	params.Set("step", step)

	url := fmt.Sprintf("%s/api/v1/query_range?%s", s.thanosEndpoint, params.Encode())

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to execute query: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var result QueryResult
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return &result, nil
}

type ParseResult struct {
	Valid    bool   `json:"valid"`
	Type     string `json:"type,omitempty"`
	Error    string `json:"error,omitempty"`
	ExprTree string `json:"expr_tree,omitempty"`
}

func (s *Service) ParseQuery(query string) (*ParseResult, error) {
	expr, err := parser.ParseExpr(query)
	if err != nil {
		return &ParseResult{
			Valid: false,
			Error: err.Error(),
		}, nil
	}

	return &ParseResult{
		Valid:    true,
		Type:     expr.Type().String(),
		ExprTree: expr.String(),
	}, nil
}

type SeriesResult struct {
	Status string              `json:"status"`
	Data   []map[string]string `json:"data"`
	Error  string              `json:"error,omitempty"`
}

func (s *Service) Series(ctx context.Context, match []string) (*SeriesResult, error) {
	params := url.Values{}
	for _, m := range match {
		params.Add("match[]", m)
	}

	url := fmt.Sprintf("%s/api/v1/series?%s", s.thanosEndpoint, params.Encode())

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var result SeriesResult
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return &result, nil
}

type LabelsResult struct {
	Status string   `json:"status"`
	Data   []string `json:"data"`
	Error  string   `json:"error,omitempty"`
}

func (s *Service) Labels(ctx context.Context) (*LabelsResult, error) {
	url := fmt.Sprintf("%s/api/v1/labels", s.thanosEndpoint)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var result LabelsResult
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return &result, nil
}

type LabelValuesResult struct {
	Status []string `json:"status"`
	Data   []string `json:"data"`
	Error  string   `json:"error,omitempty"`
}

func (s *Service) LabelValues(ctx context.Context, label string) (*LabelValuesResult, error) {
	url := fmt.Sprintf("%s/api/v1/label/%s/values", s.thanosEndpoint, label)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var result LabelValuesResult
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return &result, nil
}
