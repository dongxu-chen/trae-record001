package reporter

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"gopkg.in/yaml.v3"

	"k8s-auditor/pkg/audit"
)

type Reporter struct {
	outputDir string
}

func New(outputDir string) *Reporter {
	return &Reporter{outputDir: outputDir}
}

func (r *Reporter) GenerateReport(report *audit.AuditReport) (string, string, error) {
	if err := os.MkdirAll(r.outputDir, 0755); err != nil {
		return "", "", fmt.Errorf("failed to create output directory: %w", err)
	}

	timestamp := report.Timestamp.Format("20060102-150405")

	jsonPath := filepath.Join(r.outputDir, fmt.Sprintf("audit-report-%s.json", timestamp))
	jsonData, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		return "", "", fmt.Errorf("failed to marshal JSON report: %w", err)
	}
	if err := os.WriteFile(jsonPath, jsonData, 0644); err != nil {
		return "", "", fmt.Errorf("failed to write JSON report: %w", err)
	}

	yamlPath := filepath.Join(r.outputDir, fmt.Sprintf("audit-report-%s.yaml", timestamp))
	yamlData, err := yaml.Marshal(report)
	if err != nil {
		return "", "", fmt.Errorf("failed to marshal YAML report: %w", err)
	}
	if err := os.WriteFile(yamlPath, yamlData, 0644); err != nil {
		return "", "", fmt.Errorf("failed to write YAML report: %w", err)
	}

	return jsonPath, yamlPath, nil
}

func (r *Reporter) GenerateTextReport(report *audit.AuditReport) string {
	var sb string.Builder

	sb.WriteString("========================================\n")
	sb.WriteString("  Kubernetes 资源审计报告\n")
	sb.WriteString("========================================\n\n")
	sb.WriteString(fmt.Sprintf("审计时间: %s\n", report.Timestamp.Format(time.RFC3339)))
	sb.WriteString(fmt.Sprintf("集群: %s\n", report.Cluster))
	sb.WriteString(fmt.Sprintf("扫描资源总数: %d\n\n", report.TotalResources))

	sb.WriteString("----------------------------------------\n")
	sb.WriteString("  命名空间配额使用情况\n")
	sb.WriteString("----------------------------------------\n\n")

	if len(report.NamespaceQuotaUsages) > 0 {
		sb.WriteString(fmt.Sprintf("%-20s %-15s %-15s %-15s %-15s %-10s %-10s\n",
			"NAMESPACE", "CPU_REQUESTS", "CPU_QUOTA", "CPU_USE%", "MEM_REQUESTS", "MEM_QUOTA", "MEM_USE%"))
		sb.WriteString(strings.Repeat("-", 110) + "\n")

		sort.Slice(report.NamespaceQuotaUsages, func(i, j int) bool {
			if report.NamespaceQuotaUsages[i].OverQuota != report.NamespaceQuotaUsages[j].OverQuota {
				return report.NamespaceQuotaUsages[i].OverQuota
			}
			return report.NamespaceQuotaUsages[i].Namespace < report.NamespaceQuotaUsages[j].Namespace
		})

		for _, usage := range report.NamespaceQuotaUsages {
			status := ""
			if usage.OverQuota {
				status = " ❌"
			}
			sb.WriteString(fmt.Sprintf("%-20s %-15s %-15s %-15.1f %-15s %-15s %.1f%%%s\n",
				usage.Namespace,
				usage.CPURequests,
				usage.CPUQuota,
				usage.CPUPercent,
				usage.MemRequests,
				usage.MemQuota,
				usage.MemoryPercent,
				status))
		}
	} else {
		sb.WriteString("  未检测到命名空间ResourceQuota配置\n")
	}
	sb.WriteString("\n")

	sb.WriteString("----------------------------------------\n")
	sb.WriteString("  违规统计\n")
	sb.WriteString("----------------------------------------\n\n")

	keys := make([]string, 0, len(report.Summary))
	for k := range report.Summary {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	for _, k := range keys {
		sb.WriteString(fmt.Sprintf("  %s: %d\n", k, report.Summary[k]))
	}
	sb.WriteString(fmt.Sprintf("  总计: %d\n\n", len(report.Violations)))

	if len(report.Violations) == 0 {
		sb.WriteString("✅ 未发现违规项，所有资源配置符合规范！\n")
		return sb.String()
	}

	sb.WriteString("----------------------------------------\n")
	sb.WriteString("  违规详情\n")
	sb.WriteString("----------------------------------------\n\n")

	severityOrder := map[audit.Severity]int{
		audit.SeverityCritical: 0,
		audit.SeverityHigh:     1,
		audit.SeverityMedium:   2,
		audit.SeverityLow:      3,
	}

	sort.Slice(report.Violations, func(i, j int) bool {
		return severityOrder[report.Violations[i].Severity] < severityOrder[report.Violations[j].Severity]
	})

	for i, v := range report.Violations {
		sb.WriteString(fmt.Sprintf("【%d】%s - %s/%s\n", i+1, v.ResourceType, v.Namespace, v.ResourceName))
		sb.WriteString(fmt.Sprintf("  严重程度: %s\n", getSeverityEmoji(v.Severity)+" "+string(v.Severity)))
		sb.WriteString(fmt.Sprintf("  规则类型: %s\n", v.RuleType))
		sb.WriteString(fmt.Sprintf("  问题描述: %s\n", v.Message))
		sb.WriteString(fmt.Sprintf("  修复建议: %s\n\n", v.Suggestion))
	}

	sb.WriteString("----------------------------------------\n")
	sb.WriteString("  修复建议汇总\n")
	sb.WriteString("----------------------------------------\n\n")

	suggestions := r.generateFixSuggestions(report.Violations)
	for _, s := range suggestions {
		sb.WriteString(fmt.Sprintf("• %s\n", s))
	}

	return sb.String()
}

func (r *Reporter) generateFixSuggestions(violations []audit.Violation) []string {
	seen := make(map[string]bool)
	var suggestions []string

	for _, v := range violations {
		key := v.RuleType + ":" + string(v.Severity)
		if !seen[key] {
			seen[key] = true

			switch v.RuleType {
			case "resource_quota":
				suggestions = append(suggestions,
					"为所有容器配置 resources.requests 和 resources.limits",
					"CPU 请求建议: 100m - 4, 内存请求建议: 64Mi - 8Gi",
					"CPU 限制建议: 200m - 8, 内存限制建议: 128Mi - 16Gi")
			case "labels":
				suggestions = append(suggestions,
					"确保所有资源包含必需标签: app, environment",
					"environment 标签值应为: dev, staging, 或 production")
			case "image_source":
				suggestions = append(suggestions,
					"避免使用 latest 标签，使用具体版本号",
					"只使用授权的镜像仓库中的镜像")
			case "image_private_registry_auth":
				suggestions = append(suggestions,
					"为私有镜像仓库创建 dockerconfigjson 类型的 Secret",
					"在 Pod spec 或 ServiceAccount 中配置 imagePullSecrets")
			case "namespace_quota":
				suggestions = append(suggestions,
					"优化超标命名空间的资源分配，减少不必要的资源请求",
					"联系集群管理员评估是否需要调整 ResourceQuota 限制")
			}
		}
	}

	return suggestions
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

func (r *Reporter) SaveTextReport(report *audit.AuditReport) (string, error) {
	if err := os.MkdirAll(r.outputDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create output directory: %w", err)
	}

	timestamp := report.Timestamp.Format("20060102-150405")
	textPath := filepath.Join(r.outputDir, fmt.Sprintf("audit-report-%s.txt", timestamp))

	content := r.GenerateTextReport(report)
	if err := os.WriteFile(textPath, []byte(content), 0644); err != nil {
		return "", fmt.Errorf("failed to write text report: %w", err)
	}

	return textPath, nil
}
