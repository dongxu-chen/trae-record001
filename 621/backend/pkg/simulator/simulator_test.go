package simulator

import (
	"authz-policy-recommender/backend/pkg/models"
	"testing"
)

func TestSimulateAllow(t *testing.T) {
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
			},
		},
	}

	ps := NewPolicySimulator()
	req := models.SimulationRequest{
		Policies: policies,
		Source:   "frontend",
		Dest:     "product-service",
		Method:   "GET",
		Path:     "/products",
	}

	result := ps.Simulate(req)
	if !result.Allowed {
		t.Error("Expected request to be allowed")
	}
	if result.MatchedPolicy != "allow-product-service" {
		t.Errorf("Expected matched policy 'allow-product-service', got '%s'", result.MatchedPolicy)
	}
}

func TestSimulateDeny(t *testing.T) {
	policies := []models.AuthorizationPolicy{
		{
			Name:      "deny-all",
			Namespace: "default",
			Action:    "DENY",
			Rules: []models.Rule{
				{
					From:    "*",
					To:      "*",
					Methods: []string{"*"},
				},
			},
		},
	}

	ps := NewPolicySimulator()
	req := models.SimulationRequest{
		Policies: policies,
		Source:   "frontend",
		Dest:     "product-service",
		Method:   "GET",
		Path:     "/products",
	}

	result := ps.Simulate(req)
	if result.Allowed {
		t.Error("Expected request to be denied")
	}
}

func TestSimulateNoMatch(t *testing.T) {
	policies := []models.AuthorizationPolicy{
		{
			Name:      "allow-order-service",
			Namespace: "default",
			Action:    "ALLOW",
			Rules: []models.Rule{
				{
					From:    "frontend",
					To:      "order-service",
					Methods: []string{"POST"},
				},
			},
		},
	}

	ps := NewPolicySimulator()
	req := models.SimulationRequest{
		Policies: policies,
		Source:   "frontend",
		Dest:     "product-service",
		Method:   "GET",
		Path:     "/products",
	}

	result := ps.Simulate(req)
	if result.Allowed {
		t.Error("Expected request to be denied (no match)")
	}
	if result.Reason != "No matching policy found (default deny)" {
		t.Errorf("Expected default deny reason, got '%s'", result.Reason)
	}
}

func TestRuleMatches(t *testing.T) {
	ps := NewPolicySimulator()

	rule := models.Rule{
		From:    "frontend",
		To:      "product-service",
		Methods: []string{"GET", "POST"},
		Paths:   []string{"/products", "/products/{id}"},
	}

	tests := []struct {
		name     string
		req      models.SimulationRequest
		expected bool
	}{
		{
			name: "exact match",
			req: models.SimulationRequest{
				Source: "frontend",
				Dest:   "product-service",
				Method: "GET",
				Path:   "/products",
			},
			expected: true,
		},
		{
			name: "path with id",
			req: models.SimulationRequest{
				Source: "frontend",
				Dest:   "product-service",
				Method: "GET",
				Path:   "/products/123",
			},
			expected: true,
		},
		{
			name: "wrong source",
			req: models.SimulationRequest{
				Source: "other-service",
				Dest:   "product-service",
				Method: "GET",
				Path:   "/products",
			},
			expected: false,
		},
		{
			name: "wrong method",
			req: models.SimulationRequest{
				Source: "frontend",
				Dest:   "product-service",
				Method: "DELETE",
				Path:   "/products",
			},
			expected: false,
		},
		{
			name: "wrong path",
			req: models.SimulationRequest{
				Source: "frontend",
				Dest:   "product-service",
				Method: "GET",
				Path:   "/other",
			},
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := ps.ruleMatches(rule, tt.req)
			if result != tt.expected {
				t.Errorf("Expected %v, got %v", tt.expected, result)
			}
		})
	}
}

func TestPathMatches(t *testing.T) {
	ps := NewPolicySimulator()

	tests := []struct {
		pattern  string
		path     string
		expected bool
	}{
		{"/products", "/products", true},
		{"/products/{id}", "/products/123", true},
		{"/products/{id}", "/products/abc", true},
		{"/users/{id}/profile", "/users/123/profile", true},
		{"/products", "/products/123", false},
		{"/products/{id}", "/products", false},
		{"/products/{id}", "/orders/123", false},
		{"/*", "/anything", true},
	}

	for _, tt := range tests {
		t.Run(tt.pattern+" vs "+tt.path, func(t *testing.T) {
			result := ps.pathMatches(tt.pattern, tt.path)
			if result != tt.expected {
				t.Errorf("Expected %v for pattern '%s' and path '%s'", tt.expected, tt.pattern, tt.path)
			}
		})
	}
}

func TestSimulateBatch(t *testing.T) {
	policies := []models.AuthorizationPolicy{
		{
			Name:      "allow-frontend",
			Namespace: "default",
			Action:    "ALLOW",
			Rules: []models.Rule{
				{
					From:    "frontend",
					To:      "product-service",
					Methods: []string{"GET"},
				},
			},
		},
	}

	calls := []models.CallEdge{
		{
			Source:      models.Service{Name: "frontend"},
			Destination: models.Service{Name: "product-service"},
			Method:      "GET",
			Path:        "/products",
		},
		{
			Source:      models.Service{Name: "frontend"},
			Destination: models.Service{Name: "order-service"},
			Method:      "POST",
			Path:        "/orders",
		},
	}

	ps := NewPolicySimulator()
	result := ps.SimulateBatch(BatchSimulationRequest{
		Policies: policies,
		Calls:    calls,
	})

	if result.Total != 2 {
		t.Errorf("Expected total 2, got %d", result.Total)
	}
	if result.Allowed != 1 {
		t.Errorf("Expected 1 allowed, got %d", result.Allowed)
	}
	if result.Denied != 1 {
		t.Errorf("Expected 1 denied, got %d", result.Denied)
	}
}

func TestGenerateCoverageReport(t *testing.T) {
	policies := []models.AuthorizationPolicy{
		{
			Name:      "allow-frontend",
			Namespace: "default",
			Action:    "ALLOW",
			Rules: []models.Rule{
				{
					From:    "frontend",
					To:      "product-service",
					Methods: []string{"GET"},
				},
			},
		},
	}

	calls := []models.CallEdge{
		{
			Source:      models.Service{Name: "frontend"},
			Destination: models.Service{Name: "product-service"},
			Method:      "GET",
			Path:        "/products",
		},
		{
			Source:      models.Service{Name: "frontend"},
			Destination: models.Service{Name: "order-service"},
			Method:      "POST",
			Path:        "/orders",
		},
	}

	ps := NewPolicySimulator()
	report := ps.GenerateCoverageReport(policies, calls)

	expectedCoverage := 50
	if report["coveragePercent"] != expectedCoverage {
		t.Errorf("Expected %d%% coverage, got %v%%", expectedCoverage, report["coveragePercent"])
	}
}
