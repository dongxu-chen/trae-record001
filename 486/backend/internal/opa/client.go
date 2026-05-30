package opa

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"mesh-security-platform/internal/config"
	"mesh-security-platform/internal/models"
)

type Client struct {
	baseURL    string
	httpClient *http.Client
}

type QueryRequest struct {
	Input map[string]interface{} `json:"input"`
}

type QueryResponse struct {
	Result interface{} `json:"result"`
}

type PolicyEvaluation struct {
	DecisionID string                 `json:"decision_id"`
	Result     map[string]interface{} `json:"result"`
}

func NewClient(cfg *config.Config) *Client {
	return &Client{
		baseURL: cfg.OPA.URL,
		httpClient: &http.Client{
			Timeout: time.Duration(cfg.OPA.Timeout) * time.Second,
		},
	}
}

func (c *Client) EvaluatePolicy(ctx context.Context, policyPath string, input map[string]interface{}) (*models.PolicyEvaluationResult, error) {
	url := fmt.Sprintf("%s/v1/data/%s", c.baseURL, policyPath)

	reqBody := QueryRequest{
		Input: input,
	}

	bodyBytes, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(bodyBytes))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("OPA returned non-200 status: %d, body: %s", resp.StatusCode, body)
	}

	var result QueryResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	allowed := false
	if resultMap, ok := result.Result.(map[string]interface{}); ok {
		if allow, ok := resultMap["allow"].(bool); ok {
			allowed = allow
		}
	}

	return &models.PolicyEvaluationResult{
		Allowed:   allowed,
		Timestamp: time.Now(),
		Input:     input,
		Result:    map[string]interface{}{"raw": result.Result},
	}, nil
}

func (c *Client) CreatePolicy(ctx context.Context, policyID string, policyContent string) error {
	url := fmt.Sprintf("%s/v1/policies/%s", c.baseURL, policyID)

	req, err := http.NewRequestWithContext(ctx, "PUT", url, bytes.NewBufferString(policyContent))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", "text/plain")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("OPA returned non-200 status: %d, body: %s", resp.StatusCode, body)
	}

	return nil
}

func (c *Client) DeletePolicy(ctx context.Context, policyID string) error {
	url := fmt.Sprintf("%s/v1/policies/%s", c.baseURL, policyID)

	req, err := http.NewRequestWithContext(ctx, "DELETE", url, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNotFound {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("OPA returned non-200 status: %d, body: %s", resp.StatusCode, body)
	}

	return nil
}

func (c *Client) ListPolicies(ctx context.Context) ([]map[string]interface{}, error) {
	url := fmt.Sprintf("%s/v1/policies", c.baseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("OPA returned non-200 status: %d, body: %s", resp.StatusCode, body)
	}

	var result struct {
		Result []map[string]interface{} `json:"result"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return result.Result, nil
}

func GenerateOPAPolicy(policy *models.Policy) string {
	var regoPolicy string

	switch policy.Type {
	case models.PolicyTypeMTLS:
		regoPolicy = generateMTLSPolicy(policy)
	case models.PolicyTypeAuthorization:
		regoPolicy = generateAuthorizationPolicy(policy)
	case models.PolicyTypeRequestAuth:
		regoPolicy = generateRequestAuthPolicy(policy)
	default:
		regoPolicy = generateDefaultPolicy(policy)
	}

	return regoPolicy
}

func generateMTLSPolicy(policy *models.Policy) string {
	return fmt.Sprintf(`package mesh.security.mtls.%s

default allow = false

allow {
    input.request.mtls_enabled == true
    input.certificate.valid == true
}

deny[msg] {
    not input.request.mtls_enabled
    msg := "mTLS is required for this connection"
}
`, policy.Name)
}

func generateAuthorizationPolicy(policy *models.Policy) string {
	return fmt.Sprintf(`package mesh.security.authz.%s

default allow = false

allow {
    some rule
    input.principal == "allowed-user"
}
`, policy.Name)
}

func generateRequestAuthPolicy(policy *models.Policy) string {
	return fmt.Sprintf(`package mesh.security.requestauth.%s

default allow = false

allow {
    valid_jwt
}

valid_jwt {
    input.jwt.issuer == "trusted-issuer"
}
`, policy.Name)
}

func generateDefaultPolicy(policy *models.Policy) string {
	return fmt.Sprintf(`package mesh.security.%s

default allow = true
`, policy.Name)
}
