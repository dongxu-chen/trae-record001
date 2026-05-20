package quotachecker

import (
	"context"
	"fmt"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"

	"k8s-auditor/pkg/audit"
	"k8s-auditor/pkg/scanner"
)

type QuotaChecker struct {
	scanner *scanner.Scanner
}

func New(sc *scanner.Scanner) *QuotaChecker {
	return &QuotaChecker{scanner: sc}
}

func (qc *QuotaChecker) CheckNamespaceQuotas(ctx context.Context) ([]audit.NamespaceQuotaUsage, error) {
	namespaces, err := qc.scanner.GetNamespaces(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get namespaces: %w", err)
	}

	var usages []audit.NamespaceQuotaUsage

	for _, ns := range namespaces {
		usage, err := qc.checkNamespaceQuota(ctx, ns.Name)
		if err != nil {
			return nil, fmt.Errorf("failed to check quota for namespace %s: %w", ns.Name, err)
		}
		if usage != nil {
			usages = append(usages, *usage)
		}
	}

	return usages, nil
}

func (qc *QuotaChecker) checkNamespaceQuota(ctx context.Context, namespace string) (*audit.NamespaceQuotaUsage, error) {
	quotas, err := qc.scanner.GetResourceQuotas(ctx, namespace)
	if err != nil {
		return nil, err
	}

	if len(quotas) == 0 {
		return nil, nil
	}

	pods, err := qc.scanner.GetPodsInNamespace(ctx, namespace)
	if err != nil {
		return nil, err
	}

	var totalCPURequest, totalCPULimit, totalMemRequest, totalMemLimit resource.Quantity
	for _, pod := range pods {
		if pod.Status.Phase == corev1.PodSucceeded || pod.Status.Phase == corev1.PodFailed {
			continue
		}
		for _, container := range pod.Spec.Containers {
			totalCPURequest.Add(*container.Resources.Requests.Cpu())
			totalCPULimit.Add(*container.Resources.Limits.Cpu())
			totalMemRequest.Add(*container.Resources.Requests.Memory())
			totalMemLimit.Add(*container.Resources.Limits.Memory())
		}
	}

	var cpuQuota, memQuota resource.Quantity
	for _, quota := range quotas {
		if cpu, ok := quota.Spec.Hard[corev1.ResourceRequestsCPU]; ok {
			cpuQuota.Add(cpu)
		}
		if cpuLimit, ok := quota.Spec.Hard[corev1.ResourceLimitsCPU]; ok {
			cpuQuota.Add(cpuLimit)
		}
		if mem, ok := quota.Spec.Hard[corev1.ResourceRequestsMemory]; ok {
			memQuota.Add(mem)
		}
		if memLimit, ok := quota.Spec.Hard[corev1.ResourceLimitsMemory]; ok {
			memQuota.Add(memLimit)
		}
	}

	usage := &audit.NamespaceQuotaUsage{
		Namespace:   namespace,
		CPURequests: totalCPURequest.String(),
		CPULimits:   totalCPULimit.String(),
		MemRequests: totalMemRequest.String(),
		MemLimits:   totalMemLimit.String(),
		CPUQuota:    cpuQuota.String(),
		MemQuota:    memQuota.String(),
	}

	if !cpuQuota.IsZero() {
		usage.CPUPercent = calculatePercent(totalCPURequest, cpuQuota)
	}
	if !memQuota.IsZero() {
		usage.MemoryPercent = calculatePercent(totalMemRequest, memQuota)
	}

	usage.OverQuota = usage.CPUPercent >= 100 || usage.MemoryPercent >= 100

	return usage, nil
}

func calculatePercent(used, limit resource.Quantity) float64 {
	if limit.IsZero() {
		return 0
	}

	usedMilli := used.MilliValue()
	limitMilli := limit.MilliValue()

	if limitMilli == 0 {
		return 0
	}

	return float64(usedMilli) / float64(limitMilli) * 100
}
