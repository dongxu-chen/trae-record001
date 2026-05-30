package recommendation

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"sort"
	"time"

	"mesh-security-platform/internal/models"
)

type Recommender struct {
	existingPolicies []models.Policy
	serviceMetrics   map[string]ServiceMetrics
}

type ServiceMetrics struct {
	ServiceName         string
	UnencryptedTraffic  float64
	UnauthorizedRequests float64
	InvalidJWTCount     int
	RequestCount        int
	ErrorRate           float64
	LatencyP95          float64
	IsCriticalService   bool
	ServiceTier         string
}

func NewRecommender(policies []models.Policy, metrics map[string]ServiceMetrics) *Recommender {
	return &Recommender{
		existingPolicies: policies,
		serviceMetrics:   metrics,
	}
}

func (r *Recommender) GenerateRecommendations() []models.PolicyRecommendation {
	var recommendations []models.PolicyRecommendation

	recommendations = append(recommendations, r.generateMTLSRecommendations()...)
	recommendations = append(recommendations, r.generateAuthorizationRecommendations()...)
	recommendations = append(recommendations, r.generateRequestAuthRecommendations()...)
	recommendations = append(recommendations, r.generateBestPracticeRecommendations()...)

	for i := range recommendations {
		r.calculateRiskScore(&recommendations[i])
	}

	sort.Slice(recommendations, func(i, j int) bool {
		scoreI := recommendations[i].RiskScore + float64(recommendations[i].PriorityRank)
		scoreJ := recommendations[j].RiskScore + float64(recommendations[j].PriorityRank)
		return scoreI > scoreJ
	})

	for i := range recommendations {
		recommendations[i].PriorityRank = i + 1
	}

	return recommendations
}

func (r *Recommender) calculateRiskScore(rec *models.PolicyRecommendation) {
	riskScore := 0.0

	if rec.Confidence >= 0.9 {
		riskScore += 30
	} else if rec.Confidence >= 0.7 {
		riskScore += 20
	} else if rec.Confidence >= 0.5 {
		riskScore += 10
	} else {
		riskScore += 5
	}

	switch rec.Type {
	case models.PolicyTypeMTLS:
		riskScore += r.calculateMTLSRiskScore(rec)
	case models.PolicyTypeAuthorization:
		riskScore += r.calculateAuthorizationRiskScore(rec)
	case models.PolicyTypeRequestAuth:
		riskScore += r.calculateRequestAuthRiskScore(rec)
	}

	affectedServices := rec.AffectedServices
	if len(affectedServices) > 0 {
		criticalCount := 0
		tier1Count := 0
		tier2Count := 0

		for _, svc := range affectedServices {
			if metrics, exists := r.serviceMetrics[svc]; exists {
				if metrics.IsCriticalService {
					criticalCount++
				}
				if metrics.ServiceTier == "tier1" {
					tier1Count++
				} else if metrics.ServiceTier == "tier2" {
					tier2Count++
				}
			}
		}

		riskScore += float64(criticalCount) * 15
		riskScore += float64(tier1Count) * 10
		riskScore += float64(tier2Count) * 5
	}

	switch {
	case riskScore >= 80:
		rec.RiskLevel = "critical"
		rec.PriorityRank = 1
	case riskScore >= 60:
		rec.RiskLevel = "high"
		rec.PriorityRank = 2
	case riskScore >= 35:
		rec.RiskLevel = "medium"
		rec.PriorityRank = 3
	default:
		rec.RiskLevel = "low"
		rec.PriorityRank = 4
	}

	rec.RiskScore = riskScore
	rec.SecurityImpact = r.describeSecurityImpact(rec.RiskLevel, rec.Type)
	rec.BusinessImpact = r.describeBusinessImpact(rec)
}

func (r *Recommender) calculateMTLSRiskScore(rec *models.PolicyRecommendation) float64 {
	score := 0.0

	mode, _ := rec.Spec["mode"].(string)
	if mode == "STRICT" {
		score += 35
	} else if mode == "PERMISSIVE" {
		score += 20
	} else {
		score += 10
	}

	targetServices, _ := rec.Spec["target_services"].([]string)
	if len(targetServices) == 0 {
		score += 25
	} else {
		for _, svc := range targetServices {
			if metrics, exists := r.serviceMetrics[svc]; exists {
				if metrics.UnencryptedTraffic > 0.5 {
					score += 25
				} else if metrics.UnencryptedTraffic > 0.2 {
					score += 15
				} else if metrics.UnencryptedTraffic > 0.1 {
					score += 8
				}

				if metrics.RequestCount > 10000 {
					score += 15
				} else if metrics.RequestCount > 1000 {
					score += 8
				}
			}
		}
	}

	return score
}

func (r *Recommender) calculateAuthorizationRiskScore(rec *models.PolicyRecommendation) float64 {
	score := 0.0

	action, _ := rec.Spec["action"].(string)
	if action == "DENY" {
		score += 25
	} else if action == "ALLOW" {
		score += 15
	} else if action == "AUDIT" {
		score += 10
	}

	rules, _ := rec.Spec["rules"].([]interface{})
	if len(rules) == 0 && action == "DENY" {
		score += 30
	}

	targetServices, _ := rec.Spec["target_services"].([]string)
	for _, svc := range targetServices {
		if metrics, exists := r.serviceMetrics[svc]; exists {
			if metrics.UnauthorizedRequests > 0.1 {
				score += 25
			} else if metrics.UnauthorizedRequests > 0.05 {
				score += 15
			}

			if metrics.ErrorRate > 0.05 {
				score += 10
			}
		}
	}

	return score
}

func (r *Recommender) calculateRequestAuthRiskScore(rec *models.PolicyRecommendation) float64 {
	score := 0.0

	for _, svc := range rec.AffectedServices {
		if metrics, exists := r.serviceMetrics[svc]; exists {
			if metrics.InvalidJWTCount > 100 {
				score += 30
			} else if metrics.InvalidJWTCount > 10 {
				score += 20
			} else if metrics.InvalidJWTCount > 0 {
				score += 10
			}

			if metrics.RequestCount > 10000 {
				score += 15
			}
		}
	}

	selectors, _ := rec.Spec["selectors"].(map[string]interface{})
	if len(selectors) == 0 {
		score += 20
	}

	jwtRules, _ := rec.Spec["jwt_rules"].([]interface{})
	if len(jwtRules) > 0 {
		score += 10
	}

	return score
}

func (r *Recommender) describeSecurityImpact(riskLevel string, policyType models.PolicyType) string {
	baseImpact := map[string]string{
		"critical": "Critical security improvement that addresses high-severity vulnerabilities.",
		"high":     "Significant security improvement with broad protection coverage.",
		"medium":   "Moderate security improvement addressing specific attack vectors.",
		"low":      "Incremental security hardening with minimal risk.",
	}

	typeSpecific := map[models.PolicyType]string{
		models.PolicyTypeMTLS:         " Implements encryption for service-to-service communication.",
		models.PolicyTypeAuthorization: " Strengthens access control and reduces attack surface.",
		models.PolicyTypeRequestAuth:   " Enforces strong authentication for incoming requests.",
	}

	return baseImpact[riskLevel] + typeSpecific[policyType]
}

func (r *Recommender) describeBusinessImpact(rec *models.PolicyRecommendation) string {
	if len(rec.AffectedServices) == 0 {
		return "Applies globally to all services in the mesh."
	}

	highTraffic := false
	criticalSvc := false

	for _, svc := range rec.AffectedServices {
		if metrics, exists := r.serviceMetrics[svc]; exists {
			if metrics.RequestCount > 1000 {
				highTraffic = true
			}
			if metrics.IsCriticalService {
				criticalSvc = true
			}
		}
	}

	if criticalSvc && highTraffic {
		return "High business impact - affects critical services with significant traffic volume."
	}
	if criticalSvc {
		return "High business impact - affects critical business services."
	}
	if highTraffic {
		return "Medium business impact - affects high-traffic services."
	}

	return "Low to medium business impact - targeted service protection."
}

func (r *Recommender) generateMTLSRecommendations() []models.PolicyRecommendation {
	var recommendations []models.PolicyRecommendation

	hasGlobalMTLS := r.hasGlobalPolicy(models.PolicyTypeMTLS)
	if !hasGlobalMTLS {
		rec := models.PolicyRecommendation{
			ID:          generateID("mtls-global"),
			Type:        models.PolicyTypeMTLS,
			Name:        "global-mtls-policy",
			Description: "Enable STRICT mTLS for all services in the mesh",
			Reason:      "mTLS provides service-to-service encryption and authentication. No global policy detected.",
			Confidence:  0.95,
			Spec: map[string]interface{}{
				"mode": "STRICT",
			},
			AffectedServices: r.getAllServiceNames(),
			GeneratedAt:      time.Now(),
		}
		recommendations = append(recommendations, rec)
	}

	for svc, metrics := range r.serviceMetrics {
		if metrics.UnencryptedTraffic > 0.1 && !r.hasServicePolicy(svc, models.PolicyTypeMTLS) {
			rec := models.PolicyRecommendation{
				ID:          generateID("mtls-" + svc),
				Type:        models.PolicyTypeMTLS,
				Name:        fmt.Sprintf("mtls-policy-%s", svc),
				Description: fmt.Sprintf("Enable mTLS for service %s", svc),
				Reason:      fmt.Sprintf("Service %s has %.1f%% unencrypted traffic", svc, metrics.UnencryptedTraffic*100),
				Confidence:  0.85,
				Spec: map[string]interface{}{
					"mode":            "STRICT",
					"target_services": []string{svc},
				},
				AffectedServices: []string{svc},
				GeneratedAt:      time.Now(),
			}
			recommendations = append(recommendations, rec)
		}

		if metrics.UnencryptedTraffic > 0.01 && metrics.UnencryptedTraffic <= 0.1 && !r.hasServicePolicy(svc, models.PolicyTypeMTLS) {
			rec := models.PolicyRecommendation{
				ID:          generateID("mtls-permissive-" + svc),
				Type:        models.PolicyTypeMTLS,
				Name:        fmt.Sprintf("mtls-permissive-%s", svc),
				Description: fmt.Sprintf("Enable PERMISSIVE mTLS for service %s as transition step", svc),
				Reason:      fmt.Sprintf("Service %s has %.1f%% unencrypted traffic, start with PERMISSIVE mode", svc, metrics.UnencryptedTraffic*100),
				Confidence:  0.75,
				Spec: map[string]interface{}{
					"mode":            "PERMISSIVE",
					"target_services": []string{svc},
				},
				AffectedServices: []string{svc},
				GeneratedAt:      time.Now(),
			}
			recommendations = append(recommendations, rec)
		}
	}

	return recommendations
}

func (r *Recommender) generateAuthorizationRecommendations() []models.PolicyRecommendation {
	var recommendations []models.PolicyRecommendation

	hasDefaultDeny := r.hasDefaultDenyPolicy()
	if !hasDefaultDeny {
		rec := models.PolicyRecommendation{
			ID:          generateID("authz-default-deny"),
			Type:        models.PolicyTypeAuthorization,
			Name:        "default-deny-all",
			Description: "Default deny-all authorization policy",
			Reason:      "Following principle of least privilege - deny all traffic by default",
			Confidence:  0.90,
			Spec: map[string]interface{}{
				"action": "DENY",
				"rules":  []interface{}{},
			},
			AffectedServices: r.getAllServiceNames(),
			GeneratedAt:      time.Now(),
		}
		recommendations = append(recommendations, rec)
	}

	for svc, metrics := range r.serviceMetrics {
		if metrics.UnauthorizedRequests > 0.05 {
			rec := models.PolicyRecommendation{
				ID:          generateID("authz-audit-" + svc),
				Type:        models.PolicyTypeAuthorization,
				Name:        fmt.Sprintf("audit-policy-%s", svc),
				Description: fmt.Sprintf("Review authorization for service %s", svc),
				Reason:      fmt.Sprintf("Service %s has %.1f%% unauthorized requests", svc, metrics.UnauthorizedRequests*100),
				Confidence:  0.75,
				Spec: map[string]interface{}{
					"action":          "AUDIT",
					"target_services": []string{svc},
				},
				AffectedServices: []string{svc},
				GeneratedAt:      time.Now(),
			}
			recommendations = append(recommendations, rec)
		}

		if metrics.UnauthorizedRequests > 0.01 && !r.hasServicePolicy(svc, models.PolicyTypeAuthorization) {
			rec := models.PolicyRecommendation{
				ID:          generateID("authz-allow-" + svc),
				Type:        models.PolicyTypeAuthorization,
				Name:        fmt.Sprintf("allow-policy-%s", svc),
				Description: fmt.Sprintf("Restrict access to service %s", svc),
				Reason:      fmt.Sprintf("Service %s has %.1f%% unauthorized requests and no specific authorization policy", svc, metrics.UnauthorizedRequests*100),
				Confidence:  0.70,
				Spec: map[string]interface{}{
					"action":          "ALLOW",
					"target_services": []string{svc},
					"rules": []interface{}{
						map[string]interface{}{
							"from": []interface{}{
								map[string]interface{}{
									"principals": []string{"cluster.local/ns/*/sa/*"},
								},
							},
						},
					},
				},
				AffectedServices: []string{svc},
				GeneratedAt:      time.Now(),
			}
			recommendations = append(recommendations, rec)
		}
	}

	return recommendations
}

func (r *Recommender) generateRequestAuthRecommendations() []models.PolicyRecommendation {
	var recommendations []models.PolicyRecommendation

	for svc, metrics := range r.serviceMetrics {
		if metrics.InvalidJWTCount > 0 && !r.hasServicePolicy(svc, models.PolicyTypeRequestAuth) {
			severity := "medium"
			if metrics.InvalidJWTCount > 100 {
				severity = "high"
			}

			rec := models.PolicyRecommendation{
				ID:          generateID("jwt-" + svc),
				Type:        models.PolicyTypeRequestAuth,
				Name:        fmt.Sprintf("jwt-auth-%s", svc),
				Description: fmt.Sprintf("JWT authentication for service %s", svc),
				Reason:      fmt.Sprintf("Detected %d invalid JWT requests to service %s - %s severity", metrics.InvalidJWTCount, svc, severity),
				Confidence:  0.80,
				Spec: map[string]interface{}{
					"selectors": map[string]interface{}{
						"app": svc,
					},
					"jwt_rules": []interface{}{
						map[string]interface{}{
							"issuer":    "https://issuer.example.com",
							"audiences": []string{svc},
						},
					},
				},
				AffectedServices: []string{svc},
				GeneratedAt:      time.Now(),
			}
			recommendations = append(recommendations, rec)
		}

		if metrics.RequestCount > 5000 && !r.hasServicePolicy(svc, models.PolicyTypeRequestAuth) {
			rec := models.PolicyRecommendation{
				ID:          generateID("jwt-recommend-" + svc),
				Type:        models.PolicyTypeRequestAuth,
				Name:        fmt.Sprintf("jwt-auth-recommendation-%s", svc),
				Description: fmt.Sprintf("Consider JWT authentication for high-traffic service %s", svc),
				Reason:      fmt.Sprintf("Service %s handles %d requests per minute without request authentication", svc, metrics.RequestCount),
				Confidence:  0.65,
				Spec: map[string]interface{}{
					"selectors": map[string]interface{}{
						"app": svc,
					},
					"jwt_rules": []interface{}{
						map[string]interface{}{
							"issuer":    "https://issuer.example.com",
							"audiences": []string{svc},
						},
					},
				},
				AffectedServices: []string{svc},
				GeneratedAt:      time.Now(),
			}
			recommendations = append(recommendations, rec)
		}
	}

	return recommendations
}

func (r *Recommender) generateBestPracticeRecommendations() []models.PolicyRecommendation {
	var recommendations []models.PolicyRecommendation

	if len(r.existingPolicies) == 0 {
		rec := models.PolicyRecommendation{
			ID:          generateID("security-baseline"),
			Type:        models.PolicyTypeMTLS,
			Name:        "security-baseline-policy",
			Description: "Establish security baseline with mTLS PERMISSIVE mode",
			Reason:      "Start with PERMISSIVE mode to gradually transition to STRICT mTLS across all services",
			Confidence:  0.92,
			Spec: map[string]interface{}{
				"mode": "PERMISSIVE",
			},
			AffectedServices: r.getAllServiceNames(),
			GeneratedAt:      time.Now(),
		}
		recommendations = append(recommendations, rec)
	}

	for svc, metrics := range r.serviceMetrics {
		if metrics.LatencyP95 > 500 && !r.hasServicePolicy(svc, models.PolicyTypeAuthorization) {
			rec := models.PolicyRecommendation{
				ID:          generateID("rate-limit-" + svc),
				Type:        models.PolicyTypeAuthorization,
				Name:        fmt.Sprintf("rate-limit-%s", svc),
				Description: fmt.Sprintf("Consider rate limiting for service %s", svc),
				Reason:      fmt.Sprintf("Service %s has high p95 latency (%.0fms) - rate limiting may help prevent abuse", svc, metrics.LatencyP95),
				Confidence:  0.55,
				Spec: map[string]interface{}{
					"action":          "AUDIT",
					"target_services": []string{svc},
				},
				AffectedServices: []string{svc},
				GeneratedAt:      time.Now(),
			}
			recommendations = append(recommendations, rec)
		}
	}

	return recommendations
}

func (r *Recommender) getAllServiceNames() []string {
	names := make([]string, 0, len(r.serviceMetrics))
	for name := range r.serviceMetrics {
		names = append(names, name)
	}
	return names
}

func (r *Recommender) hasGlobalPolicy(policyType models.PolicyType) bool {
	for _, p := range r.existingPolicies {
		if p.Type == policyType && p.Namespace == "istio-system" {
			return true
		}
	}
	return false
}

func (r *Recommender) hasServicePolicy(serviceName string, policyType models.PolicyType) bool {
	for _, p := range r.existingPolicies {
		if p.Type != policyType {
			continue
		}

		if targets, ok := p.Spec["target_services"].([]interface{}); ok {
			for _, t := range targets {
				if t == serviceName {
					return true
				}
			}
		}

		if selectors, ok := p.Spec["selectors"].(map[string]interface{}); ok {
			if selectors["app"] == serviceName {
				return true
			}
		}
	}
	return false
}

func (r *Recommender) hasDefaultDenyPolicy() bool {
	for _, p := range r.existingPolicies {
		if p.Type == models.PolicyTypeAuthorization {
			if action, ok := p.Spec["action"].(string); ok && action == "DENY" {
				if rules, ok := p.Spec["rules"].([]interface{}); ok && len(rules) == 0 {
					return true
				}
			}
		}
	}
	return false
}

func generateID(prefix string) string {
	h := sha256.New()
	h.Write([]byte(prefix + time.Now().String()))
	return prefix + "-" + hex.EncodeToString(h.Sum(nil))[:8]
}
