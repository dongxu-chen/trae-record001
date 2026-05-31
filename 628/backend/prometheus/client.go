package prometheus

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"

	"anomaly-detector/model"
)

type Client struct {
	baseURL    string
	httpClient *http.Client
}

func NewClient(baseURL string) *Client {
	return &Client{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

type queryResponse struct {
	Status string `json:"status"`
	Data   struct {
		ResultType string `json:"resultType"`
		Result     []struct {
			Metric map[string]string `json:"metric"`
			Values [][2]interface{}  `json:"values"`
			Value  [2]interface{}    `json:"value"`
		} `json:"result"`
	} `json:"data"`
}

func (c *Client) QueryRange(ctx context.Context, query string, start, end time.Time, step time.Duration) ([]model.TimeSeries, error) {
	u, err := url.Parse(c.baseURL + "/api/v1/query_range")
	if err != nil {
		return nil, err
	}

	q := u.Query()
	q.Set("query", query)
	q.Set("start", strconv.FormatFloat(float64(start.Unix()), 'f', 0, 64))
	q.Set("end", strconv.FormatFloat(float64(end.Unix()), 'f', 0, 64))
	q.Set("step", step.String())
	u.RawQuery = q.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("prometheus returned status %d: %s", resp.StatusCode, string(body))
	}

	var qResp queryResponse
	if err := json.NewDecoder(resp.Body).Decode(&qResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	var series []model.TimeSeries
	for _, r := range qResp.Data.Result {
		ts := model.TimeSeries{
			Labels: r.Metric,
		}
		if name, ok := r.Metric["__name__"]; ok {
			ts.Name = name
		}

		for _, v := range r.Values {
			tsFloat, ok1 := v[0].(float64)
			valStr, ok2 := v[1].(string)
			if !ok1 || !ok2 {
				continue
			}
			val, err := strconv.ParseFloat(valStr, 64)
			if err != nil {
				continue
			}
			ts.Points = append(ts.Points, model.TimeSeriesPoint{
				Timestamp: time.Unix(int64(tsFloat), 0),
				Value:     val,
			})
		}

		if len(r.Value) == 2 {
			tsFloat, ok1 := r.Value[0].(float64)
			valStr, ok2 := r.Value[1].(string)
			if ok1 && ok2 {
				val, err := strconv.ParseFloat(valStr, 64)
				if err == nil {
					ts.Points = append(ts.Points, model.TimeSeriesPoint{
						Timestamp: time.Unix(int64(tsFloat), 0),
						Value:     val,
					})
				}
			}
		}

		series = append(series, ts)
	}

	return series, nil
}

func (c *Client) Query(ctx context.Context, query string) ([]model.TimeSeries, error) {
	u, err := url.Parse(c.baseURL + "/api/v1/query")
	if err != nil {
		return nil, err
	}

	q := u.Query()
	q.Set("query", query)
	u.RawQuery = q.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("prometheus returned status %d: %s", resp.StatusCode, string(body))
	}

	var qResp queryResponse
	if err := json.NewDecoder(resp.Body).Decode(&qResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	var series []model.TimeSeries
	for _, r := range qResp.Data.Result {
		ts := model.TimeSeries{
			Labels: r.Metric,
		}
		if name, ok := r.Metric["__name__"]; ok {
			ts.Name = name
		}

		if len(r.Value) == 2 {
			tsFloat, ok1 := r.Value[0].(float64)
			valStr, ok2 := r.Value[1].(string)
			if ok1 && ok2 {
				val, err := strconv.ParseFloat(valStr, 64)
				if err == nil {
					ts.Points = append(ts.Points, model.TimeSeriesPoint{
						Timestamp: time.Unix(int64(tsFloat), 0),
						Value:     val,
					})
				}
			}
		}

		series = append(series, ts)
	}

	return series, nil
}
