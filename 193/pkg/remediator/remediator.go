package remediator

import (
	"context"
	"fmt"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"

	"k8s-auditor/pkg/audit"
	"k8s-auditor/pkg/scanner"
)

type RemediationAction struct {
	ID           string
	RuleType     string
	ResourceType string
	Namespace    string
	ResourceName string
	Action       string
	Description  string
	Executed     bool
	Success      bool
	Error        string
	Timestamp    time.Time
}

type Remediator struct {
	scanner *scanner.Scanner
	dryRun  bool
	actions []RemediationAction
}

func New(sc *scanner.Scanner, dryRun bool) *Remediator {
	return &Remediator{
		scanner: sc,
		dryRun:  dryRun,
		actions: make([]RemediationAction, 0),
	}
}

func (r *Remediator) Remediate(ctx context.Context, violations []audit.Violation) ([]RemediationAction, error) {
	for _, v := range violations {
		action, err := r.remediateViolation(ctx, v)
		if err != nil {
			r.actions = append(r.actions, RemediationAction{
				RuleType:     v.RuleType,
				ResourceType: v.ResourceType,
				Namespace:    v.Namespace,
				ResourceName: v.ResourceName,
				Action:       "remediate",
				Description:  fmt.Sprintf("Failed to remediate: %s", v.Message),
				Executed:     true,
				Success:      false,
				Error:        err.Error(),
				Timestamp:    time.Now(),
			})
			continue
		}
		if action != nil {
			r.actions = append(r.actions, *action)
		}
	}

	return r.actions, nil
}

func (r *Remediator) remediateViolation(ctx context.Context, v audit.Violation) (*RemediationAction, error) {
	switch v.RuleType {
	case "labels":
		return r.remediateLabels(ctx, v)
	default:
		return nil, nil
	}
}

func (r *Remediator) remediateLabels(ctx context.Context, v audit.Violation) (*RemediationAction, error) {
	gvrMap := map[string]schema.GroupVersionResource{
		"pods":                   {Group: "", Version: "v1", Resource: "pods"},
		"services":               {Group: "", Version: "v1", Resource: "services"},
		"configmaps":             {Group: "", Version: "v1", Resource: "configmaps"},
		"secrets":                {Group: "", Version: "v1", Resource: "secrets"},
		"deployments":            {Group: "apps", Version: "v1", Resource: "deployments"},
		"statefulsets":           {Group: "apps", Version: "v1", Resource: "statefulsets"},
		"daemonsets":             {Group: "apps", Version: "v1", Resource: "daemonsets"},
		"ingresses":              {Group: "networking.k8s.io", Version: "v1", Resource: "ingresses"},
		"persistentvolumeclaims": {Group: "", Version: "v1", Resource: "persistentvolumeclaims"},
	}

	gvr, ok := gvrMap[v.ResourceType]
	if !ok {
		return nil, fmt.Errorf("unsupported resource type: %s", v.ResourceType)
	}

	client := r.scanner.GetClientset()

	labelsToAdd := map[string]string{
		"app":         v.ResourceName,
		"environment": "unknown",
	}

	action := &RemediationAction{
		RuleType:     v.RuleType,
		ResourceType: v.ResourceType,
		Namespace:    v.Namespace,
		ResourceName: v.ResourceName,
		Action:       "add_labels",
		Description:  fmt.Sprintf("添加标签: %v", labelsToAdd),
		Timestamp:    time.Now(),
	}

	if r.dryRun {
		action.Executed = false
		action.Success = true
		return action, nil
	}

	switch v.ResourceType {
	case "pods":
		pod, err := client.CoreV1().Pods(v.Namespace).Get(ctx, v.ResourceName, metav1.GetOptions{})
		if err != nil {
			return nil, err
		}
		if pod.Labels == nil {
			pod.Labels = make(map[string]string)
		}
		for k, val := range labelsToAdd {
			if _, exists := pod.Labels[k]; !exists {
				pod.Labels[k] = val
			}
		}
		_, err = client.CoreV1().Pods(v.Namespace).Update(ctx, pod, metav1.UpdateOptions{})
		if err != nil {
			return nil, err
		}
	case "services":
		svc, err := client.CoreV1().Services(v.Namespace).Get(ctx, v.ResourceName, metav1.GetOptions{})
		if err != nil {
			return nil, err
		}
		if svc.Labels == nil {
			svc.Labels = make(map[string]string)
		}
		for k, val := range labelsToAdd {
			if _, exists := svc.Labels[k]; !exists {
				svc.Labels[k] = val
			}
		}
		_, err = client.CoreV1().Services(v.Namespace).Update(ctx, svc, metav1.UpdateOptions{})
		if err != nil {
			return nil, err
		}
	case "configmaps":
		cm, err := client.CoreV1().ConfigMaps(v.Namespace).Get(ctx, v.ResourceName, metav1.GetOptions{})
		if err != nil {
			return nil, err
		}
		if cm.Labels == nil {
			cm.Labels = make(map[string]string)
		}
		for k, val := range labelsToAdd {
			if _, exists := cm.Labels[k]; !exists {
				cm.Labels[k] = val
			}
		}
		_, err = client.CoreV1().ConfigMaps(v.Namespace).Update(ctx, cm, metav1.UpdateOptions{})
		if err != nil {
			return nil, err
		}
	case "deployments":
		dep, err := client.AppsV1().Deployments(v.Namespace).Get(ctx, v.ResourceName, metav1.GetOptions{})
		if err != nil {
			return nil, err
		}
		if dep.Labels == nil {
			dep.Labels = make(map[string]string)
		}
		for k, val := range labelsToAdd {
			if _, exists := dep.Labels[k]; !exists {
				dep.Labels[k] = val
			}
		}
		_, err = client.AppsV1().Deployments(v.Namespace).Update(ctx, dep, metav1.UpdateOptions{})
		if err != nil {
			return nil, err
		}
	case "statefulsets":
		sts, err := client.AppsV1().StatefulSets(v.Namespace).Get(ctx, v.ResourceName, metav1.GetOptions{})
		if err != nil {
			return nil, err
		}
		if sts.Labels == nil {
			sts.Labels = make(map[string]string)
		}
		for k, val := range labelsToAdd {
			if _, exists := sts.Labels[k]; !exists {
				sts.Labels[k] = val
			}
		}
		_, err = client.AppsV1().StatefulSets(v.Namespace).Update(ctx, sts, metav1.UpdateOptions{})
		if err != nil {
			return nil, err
		}
	case "daemonsets":
		ds, err := client.AppsV1().DaemonSets(v.Namespace).Get(ctx, v.ResourceName, metav1.GetOptions{})
		if err != nil {
			return nil, err
		}
		if ds.Labels == nil {
			ds.Labels = make(map[string]string)
		}
		for k, val := range labelsToAdd {
			if _, exists := ds.Labels[k]; !exists {
				ds.Labels[k] = val
			}
		}
		_, err = client.AppsV1().DaemonSets(v.Namespace).Update(ctx, ds, metav1.UpdateOptions{})
		if err != nil {
			return nil, err
		}
	default:
		return nil, fmt.Errorf("auto-remediation not supported for resource type: %s", v.ResourceType)
	}

	action.Executed = true
	action.Success = true
	return action, nil
}

func (r *Remediator) GetActions() []RemediationAction {
	return r.actions
}

func (r *Remediator) GenerateReport() string {
	if len(r.actions) == 0 {
		return "未执行任何修复操作"
	}

	var report string
	report += "========================================\n"
	report += "  自动修复执行报告\n"
	report += "========================================\n\n"

	successCount := 0
	failedCount := 0
	skippedCount := 0

	for _, a := range r.actions {
		if !a.Executed {
			skippedCount++
		} else if a.Success {
			successCount++
		} else {
			failedCount++
		}
	}

	report += fmt.Sprintf("执行统计: 成功 %d, 失败 %d, 跳过 %d\n\n", successCount, failedCount, skippedCount)

	for i, a := range r.actions {
		status := "✓ 成功"
		if !a.Executed {
			status = "⊘ 跳过 (Dry Run)"
		} else if !a.Success {
			status = "✗ 失败"
		}

		report += fmt.Sprintf("【%d】%s\n", i+1, status)
		report += fmt.Sprintf("  资源: %s/%s/%s\n", a.ResourceType, a.Namespace, a.ResourceName)
		report += fmt.Sprintf("  操作: %s\n", a.Action)
		report += fmt.Sprintf("  描述: %s\n", a.Description)
		if a.Error != "" {
			report += fmt.Sprintf("  错误: %s\n", a.Error)
		}
		report += fmt.Sprintf("  时间: %s\n\n", a.Timestamp.Format(time.RFC3339))
	}

	return report
}
