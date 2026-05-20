package rbacchecker

import (
	"context"
	"fmt"
	"strings"

	rbacv1 "k8s.io/api/rbac/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	"k8s-auditor/pkg/audit"
	"k8s-auditor/pkg/scanner"
)

type RBACViolation struct {
	Type        string
	Severity    audit.Severity
	Namespace   string
	Name        string
	Message     string
	Suggestion  string
}

type RBACReport struct {
	Violations        []RBACViolation
	UnusedServiceAccounts []string
	OverlyPermissiveRoles []string
	ClusterRolesWithWildcards []string
}

type RBACChecker struct {
	scanner *scanner.Scanner
}

var sensitiveResources = map[string]bool{
	"secrets":                     true,
	"pods/exec":                   true,
	"pods/attach":                 true,
	"nodes":                       true,
	"persistentvolumes":           true,
	"clusterroles":                true,
	"clusterrolebindings":         true,
	"roles":                       true,
	"rolebindings":                true,
	"serviceaccounts":             true,
}

var sensitiveVerbs = map[string]bool{
	"create": true,
	"update": true,
	"patch":  true,
	"delete": true,
	"*":      true,
}

func New(sc *scanner.Scanner) *RBACChecker {
	return &RBACChecker{scanner: sc}
}

func (rc *RBACChecker) Check(ctx context.Context) (*RBACReport, error) {
	client := rc.scanner.GetClientset()
	report := &RBACReport{}

	clusterRoles, err := client.RbacV1().ClusterRoles().List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list clusterroles: %w", err)
	}

	for _, cr := range clusterRoles.Items {
		violations := rc.checkRoleRules(cr.Rules, "ClusterRole", "", cr.Name)
		report.Violations = append(report.Violations, violations...)

		if rc.hasWildcardPermissions(cr.Rules) {
			report.ClusterRolesWithWildcards = append(report.ClusterRolesWithWildcards, cr.Name)
			report.Violations = append(report.Violations, RBACViolation{
				Type:       "wildcard_permissions",
				Severity:   audit.SeverityCritical,
				Namespace:  "",
				Name:       cr.Name,
				Message:    fmt.Sprintf("ClusterRole '%s' 包含通配符权限", cr.Name),
				Suggestion: "审查并收紧权限，只授予必要的资源和操作权限",
			})
		}
	}

	roles, err := client.RbacV1().Roles("").List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list roles: %w", err)
	}

	for _, role := range roles.Items {
		violations := rc.checkRoleRules(role.Rules, "Role", role.Namespace, role.Name)
		report.Violations = append(report.Violations, violations...)
	}

	clusterRoleBindings, err := client.RbacV1().ClusterRoleBindings().List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list clusterrolebindings: %w", err)
	}

	for _, crb := range clusterRoleBindings.Items {
		if rc.isPrivilegedBinding(crb.Subjects, crb.RoleRef.Name) {
			report.Violations = append(report.Violations, RBACViolation{
				Type:       "privileged_binding",
				Severity:   audit.SeverityCritical,
				Namespace:  "",
				Name:       crb.Name,
				Message:    fmt.Sprintf("ClusterRoleBinding '%s' 将高权限角色授予普通用户或服务账户", crb.Name),
				Suggestion: "审查该绑定，确保只有授权主体能获得高权限",
			})
		}
	}

	unusedSAs, err := rc.findUnusedServiceAccounts(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to find unused service accounts: %w", err)
	}
	report.UnusedServiceAccounts = unusedSAs

	for _, sa := range unusedSAs {
		parts := strings.SplitN(sa, "/", 2)
		namespace := ""
		name := sa
		if len(parts) == 2 {
			namespace = parts[0]
			name = parts[1]
		}
		report.Violations = append(report.Violations, RBACViolation{
			Type:       "unused_service_account",
			Severity:   audit.SeverityLow,
			Namespace:  namespace,
			Name:       name,
			Message:    fmt.Sprintf("ServiceAccount '%s' 在命名空间 '%s' 中未被任何Pod使用", name, namespace),
			Suggestion: "删除未使用的ServiceAccount以减少攻击面",
		})
	}

	return report, nil
}

func (rc *RBACChecker) checkRoleRules(rules []rbacv1.PolicyRule, roleType, namespace, name string) []RBACViolation {
	var violations []RBACViolation

	for _, rule := range rules {
		for _, verb := range rule.Verbs {
			if verb == "*" {
				violations = append(violations, RBACViolation{
					Type:       "overly_permissive",
					Severity:   audit.SeverityHigh,
					Namespace:  namespace,
					Name:       name,
					Message:    fmt.Sprintf("%s '%s' 包含通配符verb '*'，权限过大", roleType, name),
					Suggestion: "明确指定需要的verb，避免使用通配符",
				})
			}
		}

		for _, resource := range rule.Resources {
			if resource == "*" {
				violations = append(violations, RBACViolation{
					Type:       "overly_permissive",
					Severity:   audit.SeverityHigh,
					Namespace:  namespace,
					Name:       name,
					Message:    fmt.Sprintf("%s '%s' 包含通配符resource '*'，可访问所有资源", roleType, name),
					Suggestion: "明确指定需要的资源类型，避免使用通配符",
				})
			}

			if sensitiveResources[resource] {
				hasSensitiveVerb := false
				for _, verb := range rule.Verbs {
					if sensitiveVerbs[verb] {
						hasSensitiveVerb = true
						break
					}
				}
				if hasSensitiveVerb {
					violations = append(violations, RBACViolation{
						Type:       "sensitive_resource_access",
						Severity:   audit.SeverityHigh,
						Namespace:  namespace,
						Name:       name,
						Message:    fmt.Sprintf("%s '%s' 对敏感资源 '%s' 拥有写权限", roleType, name, resource),
						Suggestion: fmt.Sprintf("审查对 '%s' 资源的访问权限，确保只有必要的主体才能访问", resource),
					})
				}
			}
		}

		for _, apiGroup := range rule.APIGroups {
			if apiGroup == "*" {
				violations = append(violations, RBACViolation{
					Type:       "overly_permissive",
					Severity:   audit.SeverityMedium,
					Namespace:  namespace,
					Name:       name,
					Message:    fmt.Sprintf("%s '%s' 包含通配符apiGroup '*'，可访问所有API组", roleType, name),
					Suggestion: "明确指定需要的API组，避免使用通配符",
				})
			}
		}
	}

	return violations
}

func (rc *RBACChecker) hasWildcardPermissions(rules []rbacv1.PolicyRule) bool {
	for _, rule := range rules {
		for _, verb := range rule.Verbs {
			if verb == "*" {
				return true
			}
		}
		for _, resource := range rule.Resources {
			if resource == "*" {
				return true
			}
		}
	}
	return false
}

func (rc *RBACChecker) isPrivilegedBinding(subjects []rbacv1.Subject, roleName string) bool {
	privilegedRoles := map[string]bool{
		"cluster-admin": true,
		"admin":         true,
		"edit":          true,
	}

	if !privilegedRoles[roleName] {
		return false
	}

	for _, subject := range subjects {
		if subject.Kind == "Group" && subject.Name == "system:authenticated" {
			return true
		}
		if subject.Kind == "User" && !strings.HasPrefix(subject.Name, "system:") {
			return true
		}
	}

	return false
}

func (rc *RBACChecker) findUnusedServiceAccounts(ctx context.Context) ([]string, error) {
	client := rc.scanner.GetClientset()

	namespaces, err := rc.scanner.GetNamespaces(ctx)
	if err != nil {
		return nil, err
	}

	usedSAs := make(map[string]bool)

	for _, ns := range namespaces {
		pods, err := rc.scanner.GetPodsInNamespace(ctx, ns.Name)
		if err != nil {
			continue
		}
		for _, pod := range pods {
			saName := pod.Spec.ServiceAccountName
			if saName == "" {
				saName = "default"
			}
			key := fmt.Sprintf("%s/%s", ns.Name, saName)
			usedSAs[key] = true
		}
	}

	var unusedSAs []string
	for _, ns := range namespaces {
		sas, err := client.CoreV1().ServiceAccounts(ns.Name).List(ctx, metav1.ListOptions{})
		if err != nil {
			continue
		}
		for _, sa := range sas.Items {
			if sa.Name == "default" {
				continue
			}
			key := fmt.Sprintf("%s/%s", ns.Name, sa.Name)
			if !usedSAs[key] {
				unusedSAs = append(unusedSAs, key)
			}
		}
	}

	return unusedSAs, nil
}

func (rc *RBACChecker) GenerateReport(report *RBACReport) string {
	if len(report.Violations) == 0 {
		return "✅ RBAC权限审计通过，未发现风险\n"
	}

	var result string
	result += "========================================\n"
	result += "  RBAC权限审计报告\n"
	result += "========================================\n\n"

	criticalCount := 0
	highCount := 0
	mediumCount := 0
	lowCount := 0

	for _, v := range report.Violations {
		switch v.Severity {
		case audit.SeverityCritical:
			criticalCount++
		case audit.SeverityHigh:
			highCount++
		case audit.SeverityMedium:
			mediumCount++
		case audit.SeverityLow:
			lowCount++
		}
	}

	result += fmt.Sprintf("违规统计: 🔴 Critical: %d, 🟠 High: %d, 🟡 Medium: %d, 🟢 Low: %d\n\n",
		criticalCount, highCount, mediumCount, lowCount)

	if len(report.UnusedServiceAccounts) > 0 {
		result += fmt.Sprintf("未使用的ServiceAccount: %d个\n", len(report.UnusedServiceAccounts))
	}
	if len(report.ClusterRolesWithWildcards) > 0 {
		result += fmt.Sprintf("含通配符权限的ClusterRole: %d个\n\n", len(report.ClusterRolesWithWildcards))
	}

	result += "----------------------------------------\n"
	result += "  违规详情\n"
	result += "----------------------------------------\n\n"

	for i, v := range report.Violations {
		loc := v.Name
		if v.Namespace != "" {
			loc = fmt.Sprintf("%s/%s", v.Namespace, v.Name)
		}
		result += fmt.Sprintf("【%d】%s - %s\n", i+1, v.Type, loc)
		result += fmt.Sprintf("  严重程度: %s %s\n", getSeverityEmoji(v.Severity), string(v.Severity))
		result += fmt.Sprintf("  问题描述: %s\n", v.Message)
		result += fmt.Sprintf("  修复建议: %s\n\n", v.Suggestion)
	}

	return result
}

func (rc *RBACChecker) ConvertToAuditViolations(report *RBACReport) []audit.Violation {
	var violations []audit.Violation
	for _, v := range report.Violations {
		violations = append(violations, audit.Violation{
			ResourceType: v.Type,
			Namespace:    v.Namespace,
			ResourceName: v.Name,
			RuleType:     "rbac_" + v.Type,
			Severity:     v.Severity,
			Message:      v.Message,
			Suggestion:   v.Suggestion,
		})
	}
	return violations
}

func getSeverityEmoji(s audit.Severity) string {
	switch s {
	case audit.SeverityCritical:
		return "🔴"
	case audit.SeverityHigh:
		return "🟠"
	case audit.SeverityMedium:
		return "🟡"
	case audit.SeverityLow:
		return "🟢"
	default:
		return "⚪"
	}
}
