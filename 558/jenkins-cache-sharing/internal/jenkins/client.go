package jenkins

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"path"
	"time"

	"github.com/jenkins-cache-sharing/internal/config"
	"github.com/jenkins-cache-sharing/internal/model"
)

type Client struct {
	baseURL    string
	username   string
	apiToken   string
	httpClient *http.Client
}

func NewClient(cfg config.JenkinsConfig) *Client {
	return &Client{
		baseURL:  cfg.URL,
		username: cfg.Username,
		apiToken: cfg.APIToken,
		httpClient: &http.Client{
			Timeout: cfg.Timeout,
		},
	}
}

func (c *Client) doRequest(ctx context.Context, method, apiPath string, body io.Reader) ([]byte, error) {
	u, err := url.Parse(c.baseURL)
	if err != nil {
		return nil, fmt.Errorf("invalid jenkins url: %w", err)
	}
	u.Path = path.Join(u.Path, apiPath)

	req, err := http.NewRequestWithContext(ctx, method, u.String(), body)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.SetBasicAuth(c.username, c.apiToken)
	req.Header.Set("Accept", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		respBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("jenkins api error %d: %s", resp.StatusCode, string(respBody))
	}

	return io.ReadAll(resp.Body)
}

func (c *Client) GetBuild(ctx context.Context, jobName string, buildNumber int) (*model.JenkinsBuild, error) {
	apiPath := fmt.Sprintf("/job/%s/%d/api/json", url.PathEscape(jobName), buildNumber)
	data, err := c.doRequest(ctx, http.MethodGet, apiPath, nil)
	if err != nil {
		return nil, err
	}

	var raw struct {
		Number     int    `json:"number"`
		Result     string `json:"result"`
		Actions    []struct {
			Parameters []struct {
				Name  string `json:"name"`
				Value string `json:"value"`
			} `json:"parameters"`
		} `json:"actions"`
		Artifacts []struct {
			FileName     string `json:"fileName"`
			RelativePath string `json:"relativePath"`
		} `json:"artifacts"`
		Timestamp int64 `json:"timestamp"`
		Duration  int64 `json:"duration"`
	}

	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("failed to parse build response: %w", err)
	}

	build := &model.JenkinsBuild{
		JobName:     jobName,
		BuildNumber: raw.Number,
		Result:      raw.Result,
		Parameters:  make(map[string]string),
		Timestamp:   raw.Timestamp,
		Duration:    raw.Duration,
	}

	for _, action := range raw.Actions {
		for _, param := range action.Parameters {
			build.Parameters[param.Name] = param.Value
		}
	}

	for _, artifact := range raw.Artifacts {
		build.Artifacts = append(build.Artifacts, model.JenkinsArtifact{
			FileName:     artifact.FileName,
			RelativePath: artifact.RelativePath,
		})
	}

	return build, nil
}

func (c *Client) GetLatestBuild(ctx context.Context, jobName string) (*model.JenkinsBuild, error) {
	apiPath := fmt.Sprintf("/job/%s/lastBuild/api/json", url.PathEscape(jobName))
	data, err := c.doRequest(ctx, http.MethodGet, apiPath, nil)
	if err != nil {
		return nil, err
	}

	var raw struct {
		Number int `json:"number"`
	}
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("failed to parse last build: %w", err)
	}

	return c.GetBuild(ctx, jobName, raw.Number)
}

func (c *Client) GetDownstreamJobs(ctx context.Context, jobName string) ([]string, error) {
	apiPath := fmt.Sprintf("/job/%s/api/json?tree=downstreamProjects[name]", url.PathEscape(jobName))
	data, err := c.doRequest(ctx, http.MethodGet, apiPath, nil)
	if err != nil {
		return nil, err
	}

	var raw struct {
		DownstreamProjects []struct {
			Name string `json:"name"`
		} `json:"downstreamProjects"`
	}

	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("failed to parse downstream jobs: %w", err)
	}

	var jobs []string
	for _, proj := range raw.DownstreamProjects {
		jobs = append(jobs, proj.Name)
	}

	return jobs, nil
}

func (c *Client) TriggerBuild(ctx context.Context, jobName string, parameters map[string]string) (int, error) {
	apiPath := fmt.Sprintf("/job/%s/build", url.PathEscape(jobName))
	if len(parameters) > 0 {
		apiPath = fmt.Sprintf("/job/%s/buildWithParameters", url.PathEscape(jobName))
	}

	u, err := url.Parse(c.baseURL)
	if err != nil {
		return 0, fmt.Errorf("invalid jenkins url: %w", err)
	}
	u.Path = path.Join(u.Path, apiPath)

	if len(parameters) > 0 {
		q := u.Query()
		for k, v := range parameters {
			q.Set(k, v)
		}
		u.RawQuery = q.Encode()
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, u.String(), nil)
	if err != nil {
		return 0, fmt.Errorf("failed to create request: %w", err)
	}

	req.SetBasicAuth(c.username, c.apiToken)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return 0, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return 0, fmt.Errorf("jenkins build trigger failed with status %d", resp.StatusCode)
	}

	location := resp.Header.Get("Location")
	if location != "" {
		queueURL, err := url.Parse(location)
		if err == nil {
			queueItem := path.Base(queueURL.Path)
			var queueNum int
			fmt.Sscanf(queueItem, "%d", &queueNum)
			return queueNum, nil
		}
	}

	return 0, nil
}

func (c *Client) ListJobs(ctx context.Context) ([]string, error) {
	apiPath := "/api/json?tree=jobs[name]"
	data, err := c.doRequest(ctx, http.MethodGet, apiPath, nil)
	if err != nil {
		return nil, err
	}

	var raw struct {
		Jobs []struct {
			Name string `json:"name"`
		} `json:"jobs"`
	}

	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("failed to parse jobs: %w", err)
	}

	var jobs []string
	for _, job := range raw.Jobs {
		jobs = append(jobs, job.Name)
	}

	return jobs, nil
}

func (c *Client) TestConnection(ctx context.Context) error {
	apiPath := "/api/json"
	_, err := c.doRequest(ctx, http.MethodGet, apiPath, nil)
	return err
}
