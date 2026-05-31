package generator

import (
	"authz-policy-recommender/backend/pkg/models"
	"testing"
	"time"
)

func TestGeneratePolicies(t *testing.T) {
	edges := []models.CallEdge{
		{
			Source:      models.Service{Name: "frontend", Namespace: "default"},
			Destination: models.Service{Name: "product-service", Namespace: "default"},
			Method:      "GET",
			Path:        "/products",
			Count:       10,
			LastSeen:    time.Now(),
		},
		{
			Source:      models.Service{Name: "frontend", Namespace: "default"},
			Destination: models.Service{Name: "product-service", Namespace: "default"},
			Method:      "POST",
			Path:        "/products",
			Count:       5,
			LastSeen:    time.Now(),
		},
		{
			Source:      models.Service{Name: "frontend", Namespace: "default"},
			Destination: models.Service{Name: "order-service", Namespace: "default"},
			Method:      "GET",
			Path:        "/orders/123",
			Count:       8,
			LastSeen:    time.Now(),
		},
	}

	pg := NewPolicyGenerator()
	policies := pg.GeneratePolicies(edges)

	if len(policies) != 2 {
		t.Fatalf("Expected 2 policies, got %d", len(policies))
	}

	productPolicy := policies[0]
	if productPolicy.Name != "allow-order-service" {
		t.Errorf("Expected policy name 'allow-order-service', got '%s'", productPolicy.Name)
	}
	if productPolicy.Action != "ALLOW" {
		t.Errorf("Expected action ALLOW, got %s", productPolicy.Action)
	}
	if len(productPolicy.Rules) != 1 {
		t.Fatalf("Expected 1 rule, got %d", len(productPolicy.Rules))
	}

	rule := productPolicy.Rules[0]
	if rule.From != "frontend" {
		t.Errorf("Expected from 'frontend', got '%s'", rule.From)
	}
	if rule.To != "order-service" {
		t.Errorf("Expected to 'order-service', got '%s'", rule.To)
	}
	if len(rule.Methods) != 1 || rule.Methods[0] != "GET" {
		t.Errorf("Expected methods [GET], got %v", rule.Methods)
	}
}

func TestNormalizePath(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"/products", "/products"},
		{"/products/123", "/products/{id}"},
		{"/orders/abc-123-def", "/orders/{id}"},
		{"/users/550e8400-e29b-41d4-a716-446655440000/profile", "/users/{id}/profile"},
		{"/", "/"},
		{"", ""},
	}

	for _, tt := range tests {
		result := normalizePath(tt.input)
		if result != tt.expected {
			t.Errorf("normalizePath(%s) = %s, expected %s", tt.input, result, tt.expected)
		}
	}
}

func TestGenerateIstioYAML(t *testing.T) {
	policy := models.AuthorizationPolicy{
		Name:      "allow-product-service",
		Namespace: "default",
		Action:    "ALLOW",
		Selector: map[string]string{
			"app": "product-service",
		},
		Rules: []models.Rule{
			{
				From:    "frontend",
				To:      "product-service",
				Methods: []string{"GET", "POST"},
				Paths:   []string{"/products", "/products/{id}"},
			},
		},
	}

	pg := NewPolicyGenerator()
	yaml, err := pg.GenerateIstioYAML(policy)
	if err != nil {
		t.Fatalf("Error generating YAML: %v", err)
	}

	if yaml == "" {
		t.Error("Generated YAML is empty")
	}

	expectedSubstrings := []string{
		"apiVersion: security.istio.io/v1beta1",
		"kind: AuthorizationPolicy",
		"name: allow-product-service",
		"namespace: default",
		"action: ALLOW",
		"principals:",
		"frontend",
		"GET",
		"POST",
		"/products",
	}

	for _, substr := range expectedSubstrings {
		if !contains(yaml, substr) {
			t.Errorf("Expected YAML to contain '%s', but it doesn't", substr)
		}
	}
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > 0 && containsHelper(s, substr))
}

func containsHelper(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

func TestOptimizePolicies(t *testing.T) {
	policies := []models.AuthorizationPolicy{
		{
			Name:      "allow-product-service",
			Namespace: "default",
			Action:    "ALLOW",
			Rules: []models.Rule{
				{
					From:    "frontend",
					To:      "product-service",
					Methods: []string{"GET"},
					Paths:   []string{"/products"},
				},
				{
					From:    "frontend",
					To:      "product-service",
					Methods: []string{"POST"},
					Paths:   []string{"/products"},
				},
			},
		},
	}

	pg := NewPolicyGenerator()
	optimized := pg.OptimizePolicies(policies)

	if len(optimized) != 1 {
		t.Fatalf("Expected 1 optimized policy, got %d", len(optimized))
	}

	if len(optimized[0].Rules) != 1 {
		t.Fatalf("Expected 1 merged rule, got %d", len(optimized[0].Rules))
	}

	mergedRule := optimized[0].Rules[0]
	if len(mergedRule.Methods) != 2 {
		t.Errorf("Expected 2 merged methods, got %d", len(mergedRule.Methods))
	}
}

func TestUnion(t *testing.T) {
	a := []string{"GET", "POST"}
	b := []string{"POST", "PUT"}
	result := union(a, b)

	expected := []string{"GET", "POST", "PUT"}
	if len(result) != len(expected) {
		t.Errorf("Expected %d elements, got %d", len(expected), len(result))
	}

	for i, v := range expected {
		if result[i] != v {
			t.Errorf("Expected %s at index %d, got %s", v, i, result[i])
		}
	}
}
