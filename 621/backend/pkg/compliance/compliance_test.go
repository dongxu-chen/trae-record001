package compliance

import (
	"authz-policy-recommender/backend/pkg/models"
	"testing"
)

func TestCheckDenyAll(t *testing.T) {
	cc := NewComplianceChecker()
	rule := cc.rules[0]

	t.Run("has deny-all policy", func(t *testing.T) {
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

		result := cc.checkDenyAll(rule, policies)
		if !result.Passed {
			t.Error("Expected check to pass when deny-all exists")
		}
	})

	t.Run("no deny-all policy", func(t *testing.T) {
		policies := []models.AuthorizationPolicy{
			{
				Name:      "allow-some",
				Namespace: "default",
				Action:    "ALLOW",
				Rules: []models.Rule{
					{
						From:    "frontend",
						To:      "service",
						Methods: []string{"GET"},
					},
				},
			},
		}

		result := cc.checkDenyAll(rule, policies)
		if result.Passed {
			t.Error("Expected check to fail when deny-all is missing")
		}
		if len(result.Violations) != 1 {
			t.Errorf("Expected 1 violation, got %d", len(result.Violations))
		}
	})
}

func TestCheckNoWildcardSources(t *testing.T) {
	cc := NewComplianceChecker()
	rule := cc.rules[1]

	t.Run("no wildcard sources", func(t *testing.T) {
		policies := []models.AuthorizationPolicy{
			{
				Name:      "allow-frontend",
				Namespace: "default",
				Action:    "ALLOW",
				Rules: []models.Rule{
					{
						From:    "frontend",
						To:      "service",
						Methods: []string{"GET"},
					},
				},
			},
		}

		result := cc.checkNoWildcardSources(rule, policies)
		if !result.Passed {
			t.Error("Expected check to pass with no wildcard sources")
		}
	})

	t.Run("has wildcard source", func(t *testing.T) {
		policies := []models.AuthorizationPolicy{
			{
				Name:      "allow-all",
				Namespace: "default",
				Action:    "ALLOW",
				Rules: []models.Rule{
					{
						From:    "*",
						To:      "service",
						Methods: []string{"GET"},
					},
				},
			},
		}

		result := cc.checkNoWildcardSources(rule, policies)
		if result.Passed {
			t.Error("Expected check to fail with wildcard source")
		}
		if len(result.Violations) != 1 {
			t.Errorf("Expected 1 violation, got %d", len(result.Violations))
		}
	})
}

func TestCheckNoWildcardMethods(t *testing.T) {
	cc := NewComplianceChecker()
	rule := cc.rules[2]

	t.Run("no wildcard methods", func(t *testing.T) {
		policies := []models.AuthorizationPolicy{
			{
				Name:      "allow-frontend",
				Namespace: "default",
				Action:    "ALLOW",
				Rules: []models.Rule{
					{
						From:    "frontend",
						To:      "service",
						Methods: []string{"GET", "POST"},
					},
				},
			},
		}

		result := cc.checkNoWildcardMethods(rule, policies)
		if !result.Passed {
			t.Error("Expected check to pass with specific methods")
		}
	})

	t.Run("has wildcard method", func(t *testing.T) {
		policies := []models.AuthorizationPolicy{
			{
				Name:      "allow-all-methods",
				Namespace: "default",
				Action:    "ALLOW",
				Rules: []models.Rule{
					{
						From:    "frontend",
						To:      "service",
						Methods: []string{"*"},
					},
				},
			},
		}

		result := cc.checkNoWildcardMethods(rule, policies)
		if result.Passed {
			t.Error("Expected check to fail with wildcard method")
		}
	})
}

func TestCheckPathRestrictions(t *testing.T) {
	cc := NewComplianceChecker()
	rule := cc.rules[3]

	t.Run("has path restrictions", func(t *testing.T) {
		policies := []models.AuthorizationPolicy{
			{
				Name:      "allow-frontend",
				Namespace: "default",
				Action:    "ALLOW",
				Rules: []models.Rule{
					{
						From:    "frontend",
						To:      "service",
						Methods: []string{"GET"},
						Paths:   []string{"/api/products"},
					},
				},
			},
		}

		result := cc.checkPathRestrictions(rule, policies)
		if !result.Passed {
			t.Error("Expected check to pass with path restrictions")
		}
	})

	t.Run("no path restrictions", func(t *testing.T) {
		policies := []models.AuthorizationPolicy{
			{
				Name:      "allow-all-paths",
				Namespace: "default",
				Action:    "ALLOW",
				Rules: []models.Rule{
					{
						From:    "frontend",
						To:      "service",
						Methods: []string{"GET"},
					},
				},
			},
		}

		result := cc.checkPathRestrictions(rule, policies)
		if result.Passed {
			t.Error("Expected check to fail without path restrictions")
		}
	})
}

func TestCheckNoEmptySelector(t *testing.T) {
	cc := NewComplianceChecker()
	rule := cc.rules[4]

	t.Run("has selector", func(t *testing.T) {
		policies := []models.AuthorizationPolicy{
			{
				Name:      "allow-product",
				Namespace: "default",
				Action:    "ALLOW",
				Selector: map[string]string{
					"app": "product-service",
				},
				Rules: []models.Rule{
					{
						From:    "frontend",
						To:      "product-service",
						Methods: []string{"GET"},
					},
				},
			},
		}

		result := cc.checkNoEmptySelector(rule, policies)
		if !result.Passed {
			t.Error("Expected check to pass with selector")
		}
	})

	t.Run("no selector", func(t *testing.T) {
		policies := []models.AuthorizationPolicy{
			{
				Name:      "allow-all",
				Namespace: "default",
				Action:    "ALLOW",
				Rules: []models.Rule{
					{
						From:    "frontend",
						To:      "service",
						Methods: []string{"GET"},
					},
				},
			},
		}

		result := cc.checkNoEmptySelector(rule, policies)
		if result.Passed {
			t.Error("Expected check to fail without selector")
		}
	})
}

func TestCheckComplianceOverall(t *testing.T) {
	cc := NewComplianceChecker()

	goodPolicies := []models.AuthorizationPolicy{
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
		{
			Name:      "allow-frontend-to-product",
			Namespace: "default",
			Action:    "ALLOW",
			Selector: map[string]string{
				"app": "product-service",
			},
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

	graph := &models.ServiceGraph{
		Services: []models.Service{
			{Name: "frontend", Namespace: "default"},
			{Name: "product-service", Namespace: "default"},
		},
		Edges: []models.CallEdge{
			{
				Source:      models.Service{Name: "frontend"},
				Destination: models.Service{Name: "product-service"},
				Method:      "GET",
				Path:        "/products",
			},
		},
	}

	report := cc.CheckCompliance(goodPolicies, graph)

	if report.OverallScore < 70 {
		t.Errorf("Expected higher compliance score, got %d", report.OverallScore)
	}

	totalChecks := len(cc.rules)
	if len(report.Results) != totalChecks {
		t.Errorf("Expected %d results, got %d", totalChecks, len(report.Results))
	}

	passedCount := 0
	for _, r := range report.Results {
		if r.Passed {
			passedCount++
		}
	}

	t.Logf("Passed %d/%d checks with score %d%%", passedCount, totalChecks, report.OverallScore)
}
