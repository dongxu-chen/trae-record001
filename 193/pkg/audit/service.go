package audit

import (
	"context"
	"fmt"
	"time"

	"k8s-auditor/pkg/config"
	"k8s-auditor/pkg/quotachecker"
	"k8s-auditor/pkg/rules"
	"k8s-auditor/pkg/scanner"
)

type Auditor struct {
	scanner       *scanner.Scanner
	checkers      []rules.RuleChecker
	imageChecker  *rules.ImageSourceChecker
	quotaChecker  *quotachecker.QuotaChecker
	cfg           *config.Config
}

func New(scanner *scanner.Scanner, cfg *config.Config) *Auditor {
	var checkers []rules.RuleChecker
	var imageChecker *rules.ImageSourceChecker

	if cfg.Rules.ResourceQuota.Enabled {
		checkers = append(checkers, rules.NewResourceQuotaChecker(cfg.Rules.ResourceQuota))
	}
	if cfg.Rules.Labels.Enabled {
		checkers = append(checkers, rules.NewLabelsChecker(cfg.Rules.Labels))
	}
	if cfg.Rules.ImageSource.Enabled {
		imageChecker = rules.NewImageSourceChecker(cfg.Rules.ImageSource)
		checkers = append(checkers, imageChecker)
	}

	return &Auditor{
		scanner:      scanner,
		checkers:     checkers,
		imageChecker: imageChecker,
		quotaChecker: quotachecker.New(scanner),
		cfg:          cfg,
	}
}

func (a *Auditor) Run(ctx context.Context) (*AuditReport, error) {
	resources, err := a.scanner.ScanAll(ctx, a.cfg.Audit.Resources)
	if err != nil {
		return nil, fmt.Errorf("failed to scan resources: %w", err)
	}

	if a.imageChecker != nil && a.cfg.Rules.ImageSource.CheckPrivateRegistryAuth {
		authorizedRegistries := make(map[string]bool)

		namespaces, err := a.scanner.GetNamespaces(ctx)
		if err == nil {
			for _, ns := range namespaces {
				reg1, err := a.scanner.GetImagePullSecrets(ctx, ns.Name)
				if err == nil {
					for r := range reg1 {
						authorizedRegistries[r] = true
					}
				}
				reg2, err := a.scanner.GetServiceAccountImagePullSecrets(ctx, ns.Name)
				if err == nil {
					for r := range reg2 {
						authorizedRegistries[r] = true
					}
				}
			}
		}

		a.imageChecker.SetAuthorizedRegistries(authorizedRegistries)
	}

	var violations []Violation
	for _, resource := range resources {
		for _, checker := range a.checkers {
			vs := checker.Check(resource)
			violations = append(violations, vs...)
		}
	}

	summary := make(map[string]int)
	for _, v := range violations {
		summary[string(v.Severity)]++
		ruleKey := v.RuleType + ":" + string(v.Severity)
		summary[ruleKey]++
	}

	namespaceQuotaUsages, err := a.quotaChecker.CheckNamespaceQuotas(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to check namespace quotas: %w", err)
	}

	for _, usage := range namespaceQuotaUsages {
		if usage.OverQuota {
			summary["namespace_over_quota"]++
			violations = append(violations, Violation{
				ResourceType: "namespace",
				Namespace:    usage.Namespace,
				ResourceName: usage.Namespace,
				RuleType:     "namespace_quota",
				Severity:     SeverityHigh,
				Message:      fmt.Sprintf("命名空间资源配额超标: CPU使用率 %.1f%%, 内存使用率 %.1f%%", usage.CPUPercent, usage.MemoryPercent),
				Suggestion:   "减少该命名空间下Pod的资源请求，或联系管理员调整ResourceQuota配置",
			})
		}
	}

	cluster := getClusterName(a.scanner)

	return &AuditReport{
		Timestamp:           time.Now(),
		Cluster:             cluster,
		TotalResources:      len(resources),
		Violations:          violations,
		Summary:             summary,
		NamespaceQuotaUsages: namespaceQuotaUsages,
	}, nil
}

func getClusterName(s *scanner.Scanner) string {
	client := s.GetClientset()
	version, err := client.Discovery().ServerVersion()
	if err != nil {
		return "unknown"
	}
	return version.String()
}
