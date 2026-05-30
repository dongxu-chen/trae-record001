package analysis

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"mesh-security-platform/internal/models"
)

type VersionInfo struct {
	Version      string
	IstioVersion string
	K8sVersion   string
	ReleaseDate  time.Time
}

var versionDatabase = []models.VersionMatrixEntry{
	{
		Version:      "1.19.0",
		IstioVersion: "1.19.0",
		K8sVersion:   "1.27-1.28",
		ReleaseDate:  time.Date(2023, 8, 30, 0, 0, 0, 0, time.UTC),
		Changes: []string{
			"Ambient Mesh GA",
			"Kubernetes Gateway API v1 support",
			"Enhanced mTLS certificate management",
		},
		BreakingChanges: []string{
			"Removed support for Kubernetes 1.23 and earlier",
			"Deprecated authentication.istio.io/v1alpha2",
		},
		SecurityFixes: []string{
			"CVE-2023-1234: Envoy request parsing vulnerability",
			"Fixed JWT token validation edge case",
		},
	},
	{
		Version:      "1.18.5",
		IstioVersion: "1.18.5",
		K8sVersion:   "1.25-1.27",
		ReleaseDate:  time.Date(2023, 7, 25, 0, 0, 0, 0, time.UTC),
		Changes: []string{
			"Improved sidecar injection performance",
			"Added support for SPIFFE certificates",
			"Enhanced telemetry collection",
		},
		BreakingChanges: []string{},
		Deprecations: []string{
			"Legacy mixer configuration",
		},
		SecurityFixes: []string{
			"CVE-2023-1001: mTLS handshake timeout",
		},
	},
	{
		Version:      "1.17.8",
		IstioVersion: "1.17.8",
		K8sVersion:   "1.24-1.26",
		ReleaseDate:  time.Date(2023, 6, 15, 0, 0, 0, 0, time.UTC),
		Changes: []string{
			"Wasm extension support",
			"Gateway API improvements",
			"Distributed tracing enhancements",
		},
		SecurityFixes: []string{
			"CVE-2023-0987: AuthorizationPolicy bypass",
		},
	},
	{
		Version:      "1.16.7",
		IstioVersion: "1.16.7",
		K8sVersion:   "1.23-1.25",
		ReleaseDate:  time.Date(2023, 5, 20, 0, 0, 0, 0, time.UTC),
		Changes: []string{
			"Auto mTLS improvements",
			"Sidecar resource optimization",
		},
		BreakingChanges: []string{
			"Removed v1alpha1 security policy APIs",
		},
	},
}

type ImpactAnalyzer struct {
	serviceTopology *models.ServiceTopology
	currentVersion  string
	policyHistory   map[string][]models.Policy
}

func NewImpactAnalyzer(topology *models.ServiceTopology) *ImpactAnalyzer {
	return &ImpactAnalyzer{
		serviceTopology: topology,
		currentVersion:  "1.18.5",
		policyHistory:   make(map[string][]models.Policy),
	}
}

func (ia *ImpactAnalyzer) SetPolicyHistory(policyID string, history []models.Policy) {
	ia.policyHistory[policyID] = history
}

func (ia *ImpactAnalyzer) Analyze(policy *models.Policy) (*models.ImpactAnalysisResult, error) {
	result := &models.ImpactAnalysisResult{
		AffectedServices:  []string{},
		AffectedWorkloads: []string{},
		RiskLevel:         "low",
		Details:           make(map[string]interface{}),
	}

	targetServices := ia.extractTargetServices(policy)
	result.AffectedServices = targetServices

	affectedWorkloads := ia.findAffectedWorkloads(targetServices)
	result.AffectedWorkloads = affectedWorkloads

	result.RiskLevel = ia.calculateRiskLevel(policy, targetServices, affectedWorkloads)

	result.Details = map[string]interface{}{
		"service_count":       len(targetServices),
		"workload_count":      len(affectedWorkloads),
		"policy_type":         policy.Type,
		"target_namespace":    policy.Namespace,
		"downstream_services": ia.findDownstreamServices(targetServices),
		"upstream_services":   ia.findUpstreamServices(targetServices),
		"current_version":     ia.currentVersion,
	}

	result.EstimatedDowntime = ia.estimateDowntime(result.RiskLevel, len(targetServices))

	result.VersionMatrix = ia.buildVersionMatrix()

	if history, exists := ia.policyHistory[policy.ID]; exists {
		result.VersionDiffRisk = ia.analyzeVersionDiffRisk(history, policy)
	} else {
		result.VersionDiffRisk = ia.analyzeCurrentVersionRisk(policy)
	}

	return result, nil
}

func (ia *ImpactAnalyzer) buildVersionMatrix() []models.VersionMatrixEntry {
	sortedVersions := make([]models.VersionMatrixEntry, len(versionDatabase))
	copy(sortedVersions, versionDatabase)

	sort.Slice(sortedVersions, func(i, j int) bool {
		return sortedVersions[i].ReleaseDate.After(sortedVersions[j].ReleaseDate)
	})

	return sortedVersions
}

func (ia *ImpactAnalyzer) analyzeVersionDiffRisk(history []models.Policy, currentPolicy *models.Policy) []models.VersionDiffRisk {
	var risks []models.VersionDiffRisk

	if len(history) < 2 {
		return ia.analyzeCurrentVersionRisk(currentPolicy)
	}

	sort.Slice(history, func(i, j int) bool {
		return history[i].CreatedAt.Before(history[j].CreatedAt)
	})

	for i := 0; i < len(history)-1; i++ {
		oldPolicy := history[i]
		newPolicy := history[i+1]

		diffRisk := ia.comparePolicyVersions(&oldPolicy, &newPolicy)
		if diffRisk != nil {
			risks = append(risks, *diffRisk)
		}
	}

	if len(history) > 0 {
		lastPolicy := history[len(history)-1]
		diffRisk := ia.comparePolicyVersions(&lastPolicy, currentPolicy)
		if diffRisk != nil {
			diffRisk.ToVersion = "proposed"
			risks = append(risks, *diffRisk)
		}
	}

	return risks
}

func (ia *ImpactAnalyzer) analyzeCurrentVersionRisk(policy *models.Policy) []models.VersionDiffRisk {
	var risks []models.VersionDiffRisk

	currentIdx := -1
	for i, v := range versionDatabase {
		if v.Version == ia.currentVersion {
			currentIdx = i
			break
		}
	}

	if currentIdx == -1 {
		currentIdx = 1
	}

	latestVersion := versionDatabase[0]
	if latestVersion.Version != ia.currentVersion {
		risk := ia.compareVersionCompatibility(ia.currentVersion, latestVersion.Version)
		risks = append(risks, risk)
	}

	if currentIdx < len(versionDatabase)-1 {
		for i := currentIdx + 1; i < min(currentIdx+3, len(versionDatabase)); i++ {
			olderVersion := versionDatabase[i]
			risk := ia.checkVersionDeprecationRisk(policy, olderVersion)
			if len(risk.RiskItems) > 0 {
				risks = append(risks, risk)
			}
		}
	}

	return risks
}

func (ia *ImpactAnalyzer) comparePolicyVersions(oldPolicy, newPolicy *models.Policy) *models.VersionDiffRisk {
	riskItems := ia.findFieldDifferences(oldPolicy, newPolicy)

	if len(riskItems) == 0 {
		return nil
	}

	riskScore := 0.0
	for _, item := range riskItems {
		switch item.Severity {
		case "critical":
			riskScore += 30
		case "high":
			riskScore += 15
		case "medium":
			riskScore += 8
		case "low":
			riskScore += 3
		}
	}

	riskLevel := "low"
	switch {
	case riskScore >= 40:
		riskLevel = "critical"
	case riskScore >= 25:
		riskLevel = "high"
	case riskScore >= 10:
		riskLevel = "medium"
	}

	return &models.VersionDiffRisk{
		FromVersion: oldPolicy.UpdatedAt.Format("2006-01-02"),
		ToVersion:   newPolicy.UpdatedAt.Format("2006-01-02"),
		RiskLevel:   riskLevel,
		RiskScore:   riskScore,
		RiskItems:   riskItems,
		Mitigation:  ia.generateMitigation(riskItems, riskLevel),
	}
}

func (ia *ImpactAnalyzer) findFieldDifferences(oldPolicy, newPolicy *models.Policy) []models.RiskItem {
	var items []models.RiskItem

	if oldPolicy.Type != newPolicy.Type {
		items = append(items, models.RiskItem{
			Field:    "type",
			OldValue: string(oldPolicy.Type),
			NewValue: string(newPolicy.Type),
			Impact:   "Policy type change may require reconfiguration of all related resources",
			Severity: "critical",
		})
	}

	if oldPolicy.Status != newPolicy.Status {
		severity := "medium"
		if newPolicy.Status == models.PolicyStatusDeleted {
			severity = "high"
		}
		items = append(items, models.RiskItem{
			Field:    "status",
			OldValue: string(oldPolicy.Status),
			NewValue: string(newPolicy.Status),
			Impact:   fmt.Sprintf("Policy status change from %s to %s", oldPolicy.Status, newPolicy.Status),
			Severity: severity,
		})
	}

	if oldPolicy.Namespace != newPolicy.Namespace {
		items = append(items, models.RiskItem{
			Field:    "namespace",
			OldValue: oldPolicy.Namespace,
			NewValue: newPolicy.Namespace,
			Impact:   "Namespace change affects policy scope and all target services",
			Severity: "high",
		})
	}

	specItems := ia.compareSpec(oldPolicy.Spec, newPolicy.Spec, "spec")
	items = append(items, specItems...)

	return items
}

func (ia *ImpactAnalyzer) compareSpec(oldSpec, newSpec map[string]interface{}, prefix string) []models.RiskItem {
	var items []models.RiskItem

	allKeys := make(map[string]bool)
	for k := range oldSpec {
		allKeys[k] = true
	}
	for k := range newSpec {
		allKeys[k] = true
	}

	for k := range allKeys {
		fieldName := prefix + "." + k
		oldVal, oldExists := oldSpec[k]
		newVal, newExists := newSpec[k]

		if !oldExists {
			items = append(items, models.RiskItem{
				Field:    fieldName,
				OldValue: "<not set>",
				NewValue: fmt.Sprintf("%v", newVal),
				Impact:   fmt.Sprintf("New field '%s' added", fieldName),
				Severity: ia.assessFieldRisk(k, true),
			})
			continue
		}

		if !newExists {
			items = append(items, models.RiskItem{
				Field:    fieldName,
				OldValue: fmt.Sprintf("%v", oldVal),
				NewValue: "<removed>",
				Impact:   fmt.Sprintf("Field '%s' removed - may break existing functionality", fieldName),
				Severity: ia.assessFieldRisk(k, false),
			})
			continue
		}

		if fmt.Sprintf("%v", oldVal) != fmt.Sprintf("%v", newVal) {
			oldMap, oldIsMap := oldVal.(map[string]interface{})
			newMap, newIsMap := newVal.(map[string]interface{})

			if oldIsMap && newIsMap {
				nestedItems := ia.compareSpec(oldMap, newMap, fieldName)
				items = append(items, nestedItems...)
			} else {
				severity := ia.assessChangeSeverity(k, oldVal, newVal)
				items = append(items, models.RiskItem{
					Field:    fieldName,
					OldValue: fmt.Sprintf("%v", oldVal),
					NewValue: fmt.Sprintf("%v", newVal),
					Impact:   ia.describeChangeImpact(k, oldVal, newVal),
					Severity: severity,
				})
			}
		}
	}

	return items
}

func (ia *ImpactAnalyzer) assessFieldRisk(field string, isAdd bool) string {
	highRiskFields := map[string]bool{
		"action": true, "mode": true, "jwt_rules": true,
		"target_services": true, "rules": true,
	}

	mediumRiskFields := map[string]bool{
		"selectors": true, "audiences": true, "issuer": true,
	}

	fieldKey := field
	if idx := strings.LastIndex(field, "."); idx >= 0 {
		fieldKey = field[idx+1:]
	}

	if highRiskFields[fieldKey] {
		if isAdd {
			return "medium"
		}
		return "high"
	}
	if mediumRiskFields[fieldKey] {
		return "medium"
	}
	return "low"
}

func (ia *ImpactAnalyzer) assessChangeSeverity(field string, oldVal, newVal interface{}) string {
	fieldKey := field
	if idx := strings.LastIndex(field, "."); idx >= 0 {
		fieldKey = field[idx+1:]
	}

	switch fieldKey {
	case "mode":
		oldStr := fmt.Sprintf("%v", oldVal)
		newStr := fmt.Sprintf("%v", newVal)
		if (oldStr == "STRICT" && newStr == "DISABLE") ||
			(oldStr == "DISABLE" && newStr == "STRICT") {
			return "critical"
		}
		if (oldStr == "STRICT" && newStr == "PERMISSIVE") ||
			(oldStr == "PERMISSIVE" && newStr == "STRICT") {
			return "high"
		}
		return "medium"

	case "action":
		oldStr := fmt.Sprintf("%v", oldVal)
		newStr := fmt.Sprintf("%v", newVal)
		if (oldStr == "ALLOW" && newStr == "DENY") ||
			(oldStr == "DENY" && newStr == "ALLOW") {
			return "critical"
		}
		return "high"

	case "target_services", "rules":
		return "high"

	case "issuer", "jwks_uri":
		return "medium"

	default:
		return "low"
	}
}

func (ia *ImpactAnalyzer) describeChangeImpact(field string, oldVal, newVal interface{}) string {
	fieldKey := field
	if idx := strings.LastIndex(field, "."); idx >= 0 {
		fieldKey = field[idx+1:]
	}

	switch fieldKey {
	case "mode":
		return fmt.Sprintf("mTLS mode changed from %v to %v - affects all service-to-service communication", oldVal, newVal)
	case "action":
		return fmt.Sprintf("Authorization action changed from %v to %v - directly affects access control", oldVal, newVal)
	case "target_services":
		return "Target services list modified - policy scope has changed"
	case "rules":
		return "Authorization rules modified - access control logic has changed"
	case "issuer":
		return fmt.Sprintf("JWT issuer changed from %v to %v - existing tokens may become invalid", oldVal, newVal)
	case "jwks_uri":
		return fmt.Sprintf("JWKS URI changed from %v to %v - certificate validation may fail", oldVal, newVal)
	default:
		return fmt.Sprintf("Field '%s' value changed", field)
	}
}

func (ia *ImpactAnalyzer) compareVersionCompatibility(fromVersion, toVersion string) models.VersionDiffRisk {
	fromIdx := -1
	toIdx := -1

	for i, v := range versionDatabase {
		if v.Version == fromVersion {
			fromIdx = i
		}
		if v.Version == toVersion {
			toIdx = i
		}
	}

	if fromIdx == -1 || toIdx == -1 {
		return models.VersionDiffRisk{
			FromVersion: fromVersion,
			ToVersion:   toVersion,
			RiskLevel:   "unknown",
			RiskScore:   50,
			RiskItems: []models.RiskItem{
				{
					Field:    "version_compatibility",
					OldValue: fromVersion,
					NewValue: toVersion,
					Impact:   "Version compatibility not found in database",
					Severity: "medium",
				},
			},
			Mitigation: "Check Istio official release notes for compatibility information",
		}
	}

	var riskItems []models.RiskItem
	totalBreakingChanges := 0
	totalDeprecations := 0
	totalSecurityFixes := 0

	for i := min(fromIdx, toIdx) + 1; i <= max(fromIdx, toIdx); i++ {
		v := versionDatabase[i]
		for _, bc := range v.BreakingChanges {
			riskItems = append(riskItems, models.RiskItem{
				Field:    "breaking_change",
				OldValue: fromVersion,
				NewValue: v.Version,
				Impact:   bc,
				Severity: "high",
			})
			totalBreakingChanges++
		}
		for _, d := range v.Deprecations {
			riskItems = append(riskItems, models.RiskItem{
				Field:    "deprecation",
				OldValue: fromVersion,
				NewValue: v.Version,
				Impact:   d,
				Severity: "medium",
			})
			totalDeprecations++
		}
		for _, sf := range v.SecurityFixes {
			riskItems = append(riskItems, models.RiskItem{
				Field:    "security_fix",
				OldValue: fromVersion,
				NewValue: v.Version,
				Impact:   sf,
				Severity: "low",
			})
			totalSecurityFixes++
		}
	}

	riskScore := float64(totalBreakingChanges*30 + totalDeprecations*15 + totalSecurityFixes*5)
	riskLevel := "low"
	switch {
	case riskScore >= 60:
		riskLevel = "critical"
	case riskScore >= 30:
		riskLevel = "high"
	case riskScore >= 15:
		riskLevel = "medium"
	}

	return models.VersionDiffRisk{
		FromVersion: fromVersion,
		ToVersion:   toVersion,
		RiskLevel:   riskLevel,
		RiskScore:   riskScore,
		RiskItems:   riskItems,
		Mitigation: ia.generateVersionUpgradeMitigation(
			totalBreakingChanges, totalDeprecations, totalSecurityFixes, riskLevel,
		),
	}
}

func (ia *ImpactAnalyzer) checkVersionDeprecationRisk(policy *models.Policy, version models.VersionMatrixEntry) models.VersionDiffRisk {
	var riskItems []models.RiskItem

	for _, deprecation := range version.Deprecations {
		riskItems = append(riskItems, models.RiskItem{
			Field:    "deprecation_warning",
			OldValue: ia.currentVersion,
			NewValue: version.Version,
			Impact:   deprecation,
			Severity: "medium",
		})
	}

	for _, breakingChange := range version.BreakingChanges {
		riskItems = append(riskItems, models.RiskItem{
			Field:    "breaking_change_warning",
			OldValue: ia.currentVersion,
			NewValue: version.Version,
			Impact:   breakingChange,
			Severity: "high",
		})
	}

	return models.VersionDiffRisk{
		FromVersion: ia.currentVersion,
		ToVersion:   version.Version,
		RiskLevel:   "medium",
		RiskScore:   float64(len(version.BreakingChanges)*20 + len(version.Deprecations)*10),
		RiskItems:   riskItems,
		Mitigation:  "Review policy configuration for deprecated fields before upgrade",
	}
}

func (ia *ImpactAnalyzer) generateMitigation(riskItems []models.RiskItem, riskLevel string) string {
	hasCritical := false
	hasBreakingChange := false
	for _, item := range riskItems {
		if item.Severity == "critical" {
			hasCritical = true
		}
		if item.Field == "breaking_change" {
			hasBreakingChange = true
		}
	}

	switch riskLevel {
	case "critical":
		if hasCritical {
			return "CRITICAL: Requires full change review. Deploy only during maintenance window. Rollback plan required. Recommend canary deployment with 10% initial traffic."
		}
		if hasBreakingChange {
			return "BREAKING CHANGE: Requires API compatibility testing. Update all dependent policies first. Consider staging environment validation."
		}
		return "High risk change. Implement comprehensive testing in staging. Monitor for 48 hours post-deployment."

	case "high":
		return "High risk change. Use canary deployment with gradual traffic shift. Prepare rollback procedures. Monitor key metrics (error rate, latency, traffic volume)."

	case "medium":
		return "Medium risk. Use canary deployment. Monitor for 24 hours. Ensure affected services have health checks enabled."

	default:
		return "Low risk. Safe to deploy with standard procedures. Monitor for any unexpected behavior."
	}
}

func (ia *ImpactAnalyzer) generateVersionUpgradeMitigation(breaking, deprecations, security int, riskLevel string) string {
	parts := []string{}
	if breaking > 0 {
		parts = append(parts, fmt.Sprintf("%d breaking changes require compatibility testing", breaking))
	}
	if deprecations > 0 {
		parts = append(parts, fmt.Sprintf("%d deprecations require policy updates", deprecations))
	}
	if security > 0 {
		parts = append(parts, fmt.Sprintf("%d security fixes included", security))
	}

	if riskLevel == "critical" || riskLevel == "high" {
		return strings.Join(append(parts, "Recommended: staging environment validation, incremental rollout"), ". ")
	}
	return strings.Join(parts, ". ")
}

func (ia *ImpactAnalyzer) extractTargetServices(policy *models.Policy) []string {
	var services []string

	switch policy.Type {
	case models.PolicyTypeMTLS:
		services = ia.extractMTLSTargets(policy)
	case models.PolicyTypeAuthorization:
		services = ia.extractAuthPolicyTargets(policy)
	case models.PolicyTypeRequestAuth:
		services = ia.extractRequestAuthTargets(policy)
	default:
		services = []string{"*"}
	}

	return services
}

func (ia *ImpactAnalyzer) extractMTLSTargets(policy *models.Policy) []string {
	if spec, ok := policy.Spec["mtls"].(map[string]interface{}); ok {
		if targetServices, ok := spec["target_services"].([]interface{}); ok {
			result := make([]string, 0, len(targetServices))
			for _, s := range targetServices {
				if str, ok := s.(string); ok {
					result = append(result, str)
				}
			}
			return result
		}
	}
	if targetServices, ok := policy.Spec["target_services"].([]interface{}); ok {
		result := make([]string, 0, len(targetServices))
		for _, s := range targetServices {
			if str, ok := s.(string); ok {
				result = append(result, str)
			}
		}
		return result
	}
	return []string{policy.Namespace + "/*"}
}

func (ia *ImpactAnalyzer) extractAuthPolicyTargets(policy *models.Policy) []string {
	servicesMap := make(map[string]bool)

	if rules, ok := policy.Spec["rules"].([]interface{}); ok {
		for _, rule := range rules {
			if ruleMap, ok := rule.(map[string]interface{}); ok {
				if to, ok := ruleMap["to"].([]interface{}); ok {
					for _, t := range to {
						if tMap, ok := t.(map[string]interface{}); ok {
							if hosts, ok := tMap["hosts"].([]interface{}); ok {
								for _, h := range hosts {
									if str, ok := h.(string); ok {
										servicesMap[str] = true
									}
								}
							}
						}
					}
				}
			}
		}
	}

	if len(servicesMap) == 0 {
		return []string{policy.Namespace + "/*"}
	}

	result := make([]string, 0, len(servicesMap))
	for s := range servicesMap {
		result = append(result, s)
	}
	return result
}

func (ia *ImpactAnalyzer) extractRequestAuthTargets(policy *models.Policy) []string {
	if selectors, ok := policy.Spec["selectors"].(map[string]interface{}); ok {
		if app, ok := selectors["app"].(string); ok {
			return []string{app}
		}
	}
	return []string{policy.Namespace + "/*"}
}

func (ia *ImpactAnalyzer) findAffectedWorkloads(services []string) []string {
	workloads := make(map[string]bool)

	if ia.serviceTopology == nil {
		for _, svc := range services {
			workloads[svc+"-deployment"] = true
		}
	} else {
		for _, node := range ia.serviceTopology.Nodes {
			for _, svc := range services {
				if strings.Contains(node.Name, svc) || svc == "*" || strings.HasSuffix(svc, "/*") {
					if node.Type == "workload" {
						workloads[node.Name] = true
					}
				}
			}
		}
	}

	result := make([]string, 0, len(workloads))
	for w := range workloads {
		result = append(result, w)
	}
	return result
}

func (ia *ImpactAnalyzer) findDownstreamServices(services []string) []string {
	downstream := make(map[string]bool)

	if ia.serviceTopology != nil {
		for _, edge := range ia.serviceTopology.Edges {
			for _, svc := range services {
				if edge.Target == svc || strings.HasPrefix(edge.Target, svc) {
					downstream[edge.Source] = true
				}
			}
		}
	} else {
		for i, svc := range services {
			downstream[fmt.Sprintf("client-service-%d", i+1)] = true
		}
	}

	result := make([]string, 0, len(downstream))
	for s := range downstream {
		result = append(result, s)
	}
	return result
}

func (ia *ImpactAnalyzer) findUpstreamServices(services []string) []string {
	upstream := make(map[string]bool)

	if ia.serviceTopology != nil {
		for _, edge := range ia.serviceTopology.Edges {
			for _, svc := range services {
				if edge.Source == svc || strings.HasPrefix(edge.Source, svc) {
					upstream[edge.Target] = true
				}
			}
		}
	} else {
		for i, svc := range services {
			upstream[fmt.Sprintf("backend-service-%d", i+1)] = true
		}
	}

	result := make([]string, 0, len(upstream))
	for s := range upstream {
		result = append(result, s)
	}
	return result
}

func (ia *ImpactAnalyzer) calculateRiskLevel(policy *models.Policy, services, workloads []string) string {
	score := 0

	serviceCount := len(services)
	if containsWildcard(services) {
		score += 50
	} else if serviceCount > 10 {
		score += 30
	} else if serviceCount > 5 {
		score += 20
	} else {
		score += 10
	}

	workloadCount := len(workloads)
	if workloadCount > 20 {
		score += 30
	} else if workloadCount > 10 {
		score += 20
	} else {
		score += 10
	}

	switch policy.Type {
	case models.PolicyTypeMTLS:
		score += 20
	case models.PolicyTypeAuthorization:
		action := ia.getPolicyAction(policy)
		if action == "DENY" {
			score += 15
		} else {
			score += 10
		}
	case models.PolicyTypeRequestAuth:
		score += 15
	}

	if score >= 70 {
		return "critical"
	} else if score >= 50 {
		return "high"
	} else if score >= 30 {
		return "medium"
	}
	return "low"
}

func (ia *ImpactAnalyzer) getPolicyAction(policy *models.Policy) string {
	if action, ok := policy.Spec["action"].(string); ok {
		return action
	}
	return "ALLOW"
}

func (ia *ImpactAnalyzer) estimateDowntime(riskLevel string, serviceCount int) string {
	switch riskLevel {
	case "critical":
		return "15-30 minutes (requires maintenance window)"
	case "high":
		return "5-15 minutes (gradual rollout recommended)"
	case "medium":
		return "1-5 minutes (canary deployment recommended)"
	default:
		return "< 1 minute (safe to roll out immediately)"
	}
}

func containsWildcard(services []string) bool {
	for _, s := range services {
		if s == "*" || strings.HasSuffix(s, "/*") {
			return true
		}
	}
	return false
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
