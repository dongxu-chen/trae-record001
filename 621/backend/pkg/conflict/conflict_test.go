package conflict

import (
	"authz-policy-recommender/backend/pkg/models"
	"testing"
)

func TestDetectShadowingConflicts(t *testing.T) {
	policies := []models.AuthorizationPolicy{
		{
			Name:      "deny-all",
			Namespace: "default",
			Action:    "DENY",
			Rules: []models.Rule{
				{
					From:    "*",
					To:      "product-service",
					Methods: []string{"*"},
				},
			},
		},
		{
			Name:      "allow-product-service",
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

	cd := NewConflictDetector()
	conflicts := cd.DetectConflicts(policies)

	hasShadowing := false
	for _, c := range conflicts {
		if c.Type == "SHADOWING" {
			hasShadowing = true
			break
		}
	}

	if !hasShadowing {
		t.Error("Expected shadowing conflict to be detected")
	}
}

func TestDetectOverlapConflicts(t *testing.T) {
	policies := []models.AuthorizationPolicy{
		{
			Name:      "policy-a",
			Namespace: "default",
			Action:    "ALLOW",
			Rules: []models.Rule{
				{
					From:    "frontend",
					To:      "product-service",
					Methods: []string{"GET", "POST"},
				},
			},
		},
		{
			Name:      "policy-b",
			Namespace: "default",
			Action:    "ALLOW",
			Rules: []models.Rule{
				{
					From:    "frontend",
					To:      "product-service",
					Methods: []string{"POST", "PUT"},
				},
			},
		},
	}

	cd := NewConflictDetector()
	conflicts := cd.DetectConflicts(policies)

	hasOverlap := false
	for _, c := range conflicts {
		if c.Type == "OVERLAP" {
			hasOverlap = true
			break
		}
	}

	if !hasOverlap {
		t.Error("Expected overlap conflict to be detected")
	}
}

func TestDetectContradictionConflicts(t *testing.T) {
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
		{
			Name:      "deny-frontend",
			Namespace: "default",
			Action:    "DENY",
			Rules: []models.Rule{
				{
					From:    "frontend",
					To:      "product-service",
					Methods: []string{"GET"},
				},
			},
		},
	}

	cd := NewConflictDetector()
	conflicts := cd.DetectConflicts(policies)

	hasContradiction := false
	for _, c := range conflicts {
		if c.Type == "CONTRADICTION" {
			hasContradiction = true
			break
		}
	}

	if !hasContradiction {
		t.Error("Expected contradiction conflict to be detected")
	}
}

func TestDetectOverlyBroadPolicies(t *testing.T) {
	policies := []models.AuthorizationPolicy{
		{
			Name:      "allow-all",
			Namespace: "default",
			Action:    "ALLOW",
			Rules: []models.Rule{
				{
					From:    "*",
					To:      "product-service",
					Methods: []string{"GET"},
				},
			},
		},
	}

	cd := NewConflictDetector()
	conflicts := cd.DetectConflicts(policies)

	hasOverlyBroad := false
	for _, c := range conflicts {
		if c.Type == "OVERLY_BROAD" {
			hasOverlyBroad = true
			break
		}
	}

	if !hasOverlyBroad {
		t.Error("Expected overly broad conflict to be detected")
	}
}

func TestIsRuleShadowed(t *testing.T) {
	cd := NewConflictDetector()

	tests := []struct {
		name     string
		ruleA    models.Rule
		ruleB    models.Rule
		expected bool
	}{
		{
			name: "wildcard shadows specific",
			ruleA: models.Rule{
				From:    "*",
				To:      "service",
				Methods: []string{"*"},
			},
			ruleB: models.Rule{
				From:    "frontend",
				To:      "service",
				Methods: []string{"GET"},
			},
			expected: true,
		},
		{
			name: "different destinations",
			ruleA: models.Rule{
				From:    "*",
				To:      "service-a",
				Methods: []string{"*"},
			},
			ruleB: models.Rule{
				From:    "*",
				To:      "service-b",
				Methods: []string{"*"},
			},
			expected: false,
		},
		{
			name: "no method overlap",
			ruleA: models.Rule{
				From:    "frontend",
				To:      "service",
				Methods: []string{"GET"},
			},
			ruleB: models.Rule{
				From:    "frontend",
				To:      "service",
				Methods: []string{"POST"},
			},
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := cd.isRuleShadowed(tt.ruleA, tt.ruleB)
			if result != tt.expected {
				t.Errorf("Expected %v, got %v", tt.expected, result)
			}
		})
	}
}

func TestFindRuleOverlap(t *testing.T) {
	cd := NewConflictDetector()

	ruleA := models.Rule{
		From:    "frontend",
		To:      "service",
		Methods: []string{"GET", "POST"},
	}
	ruleB := models.Rule{
		From:    "frontend",
		To:      "service",
		Methods: []string{"POST", "PUT"},
	}

	overlap := cd.findRuleOverlap(ruleA, ruleB)
	if len(overlap) != 1 || overlap[0] != "POST" {
		t.Errorf("Expected overlap [POST], got %v", overlap)
	}
}

func TestNoConflicts(t *testing.T) {
	policies := []models.AuthorizationPolicy{
		{
			Name:      "allow-frontend-to-product",
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
		{
			Name:      "allow-frontend-to-order",
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

	cd := NewConflictDetector()
	conflicts := cd.DetectConflicts(policies)

	if len(conflicts) != 0 {
		t.Errorf("Expected no conflicts, got %d: %v", len(conflicts), conflicts)
	}
}
