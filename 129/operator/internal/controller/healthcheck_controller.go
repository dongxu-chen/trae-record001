/*
Copyright 2024.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package controller

import (
	"context"
	"fmt"
	"time"

	"go.uber.org/zap"
	corev1 "k8s.io/api/core/v1"
	policyv1 "k8s.io/api/policy/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/builder"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/handler"
	"sigs.k8s.io/controller-runtime/pkg/log"
	"sigs.k8s.io/controller-runtime/pkg/predicate"
	"sigs.k8s.io/controller-runtime/pkg/source"

	healthv1 "github.com/k8s-health-checker/operator/api/v1"
	"github.com/k8s-health-checker/operator/internal/metrics"
	"github.com/k8s-health-checker/operator/internal/remediation"
)

// HealthCheckReconciler reconciles a HealthCheck object
type HealthCheckReconciler struct {
	client.Client
	Scheme    *runtime.Scheme
	Logger    *zap.Logger
	Metrics   *metrics.HealthCheckMetrics
	Remediator *remediation.Remediator
}

// +kubebuilder:rbac:groups=health.k8s.health.checker.io,resources=healthchecks,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=health.k8s.health.checker.io,resources=healthchecks/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=health.k8s.health.checker.io,resources=healthchecks/finalizers,verbs=update
// +kubebuilder:rbac:groups="",resources=pods,verbs=get;list;watch;delete
// +kubebuilder:rbac:groups="",resources=nodes,verbs=get;list;watch;update;patch
// +kubebuilder:rbac:groups=policy,resources=poddisruptionbudgets,verbs=get;list;watch
// +kubebuilder:rbac:groups=policy,resources=poddisruptionbudgets/eviction,verbs=create

func (r *HealthCheckReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	_ = log.FromContext(ctx)
	startTime := time.Now()

	// 获取 HealthCheck CR
	healthCheck := &healthv1.HealthCheck{}
	if err := r.Get(ctx, req.NamespacedName, healthCheck); err != nil {
		if errors.IsNotFound(err) {
			return ctrl.Result{}, nil
		}
		r.Logger.Error("Failed to get HealthCheck", zap.Error(err))
		return ctrl.Result{}, err
	}

	// 更新状态为 Running
	if healthCheck.Status.Phase != "Running" {
		healthCheck.Status.Phase = "Running"
		if err := r.Status().Update(ctx, healthCheck); err != nil {
			r.Logger.Error("Failed to update status to Running", zap.Error(err))
			return ctrl.Result{}, err
		}
	}

	r.Logger.Info("Starting health check",
		zap.String("namespace", healthCheck.Namespace),
		zap.String("name", healthCheck.Name))

	// 执行健康检查
	result, err := r.performHealthCheck(ctx, healthCheck)
	if err != nil {
		healthCheck.Status.Phase = "Failed"
		healthCheck.Status.Errors = append(healthCheck.Status.Errors, err.Error())
		if statusErr := r.Status().Update(ctx, healthCheck); statusErr != nil {
			r.Logger.Error("Failed to update status to Failed", zap.Error(statusErr))
		}
		return ctrl.Result{}, err
	}

	// 更新状态
	healthCheck.Status = result.Status
	healthCheck.Status.LastCheckTime = metav1.Now()
	healthCheck.Status.Phase = "Completed"
	healthCheck.Status.Summary.DurationSeconds = int(time.Since(startTime).Seconds())

	if err := r.Status().Update(ctx, healthCheck); err != nil {
		r.Logger.Error("Failed to update final status", zap.Error(err))
		return ctrl.Result{}, err
	}

	// 更新 Prometheus 指标
	r.updateMetrics(healthCheck)

	// 计算下一次调度时间
	interval := time.Duration(healthCheck.Spec.IntervalMinutes) * time.Minute
	if interval == 0 {
		interval = 5 * time.Minute // 默认 5 分钟
	}

	r.Logger.Info("Health check completed",
		zap.String("namespace", healthCheck.Namespace),
		zap.String("name", healthCheck.Name),
		zap.Int("duration", healthCheck.Status.Summary.DurationSeconds),
		zap.Int("unhealthyPods", healthCheck.Status.Summary.UnhealthyPodCount),
		zap.Int("unhealthyNodes", healthCheck.Status.Summary.UnhealthyNodeCount))

	return ctrl.Result{RequeueAfter: interval}, nil
}

func (r *HealthCheckReconciler) performHealthCheck(ctx context.Context, healthCheck *healthv1.HealthCheck) (*healthv1.HealthCheck, error) {
	var unhealthyPods []healthv1.PodHealthStatus
	var unhealthyNodes []healthv1.NodeHealthStatus
	var quotaRecs []healthv1.QuotaRecommendation
	var imageIssues []healthv1.ImageSecurityIssue
	var restarted []healthv1.RestartedContainerStatus
	var warnings []string
	var totalPodsChecked, totalNodesChecked int

	// 检查 Pod
	if healthCheck.Spec.PodCheck.Enabled {
		pods, err := r.getPodsToCheck(ctx, healthCheck)
		if err != nil {
			warnings = append(warnings, fmt.Sprintf("Failed to list pods: %v", err))
		} else {
			totalPodsChecked = len(pods)
			for _, pod := range pods {
				// 检查 Pod 健康状态
				if status := r.checkPodHealth(&pod); status != nil {
					unhealthyPods = append(unhealthyPods, *status)
				}
				// 检查资源配额
				if recs := r.analyzeResourceQuota(&pod); recs != nil {
					quotaRecs = append(quotaRecs, *recs)
				}
				// 检查镜像安全
				if issues := r.checkImageSecurity(&pod); issues != nil {
					imageIssues = append(imageIssues, issues...)
				}
			}
		}
	}

	// 检查 Node
	if healthCheck.Spec.NodeCheck.Enabled {
		nodes, err := r.getNodesToCheck(ctx, healthCheck)
		if err != nil {
			warnings = append(warnings, fmt.Sprintf("Failed to list nodes: %v", err))
		} else {
			totalNodesChecked = len(nodes)
			for _, node := range nodes {
				if status := r.checkNodeHealth(&node, healthCheck.Spec.NodeCheck.UnschedulableAsUnhealthy); status != nil {
					unhealthyNodes = append(unhealthyNodes, *status)
				}
			}
		}
	}

	// 自动修复
	if healthCheck.Spec.AutoRemediation.Enabled {
		restarted = r.performAutoRemediation(ctx, healthCheck, unhealthyPods, unhealthyNodes)
	}

	healthCheck.Status.UnhealthyPods = unhealthyPods
	healthCheck.Status.UnhealthyNodes = unhealthyNodes
	healthCheck.Status.QuotaRecommendations = quotaRecs
	healthCheck.Status.ImageSecurityIssues = imageIssues
	healthCheck.Status.RestartedContainers = restarted
	healthCheck.Status.Warnings = warnings

	healthCheck.Status.Summary.TotalPodsChecked = totalPodsChecked
	healthCheck.Status.Summary.UnhealthyPodCount = len(unhealthyPods)
	healthCheck.Status.Summary.TotalNodesChecked = totalNodesChecked
	healthCheck.Status.Summary.UnhealthyNodeCount = len(unhealthyNodes)
	healthCheck.Status.Summary.QuotaRecommendationsCount = len(quotaRecs)
	healthCheck.Status.Summary.ImageSecurityIssuesCount = len(imageIssues)
	healthCheck.Status.Summary.ContainersRestarted = len(restarted)
	healthCheck.Status.Summary.WarningCount = len(warnings)

	return healthCheck, nil
}

func (r *HealthCheckReconciler) getPodsToCheck(ctx context.Context, healthCheck *healthv1.HealthCheck) ([]corev1.Pod, error) {
	var podList corev1.PodList
	var opts []client.ListOption

	// 命名空间过滤
	if len(healthCheck.Spec.PodCheck.Namespaces) > 0 {
		// 逐个命名空间查询
		var allPods []corev1.Pod
		for _, ns := range healthCheck.Spec.PodCheck.Namespaces {
			var nsPodList corev1.PodList
			if err := r.List(ctx, &nsPodList, client.InNamespace(ns)); err != nil {
				return nil, err
			}
			allPods = append(allPods, nsPodList.Items...)
		}
		return allPods, nil
	}

	if err := r.List(ctx, &podList, opts...); err != nil {
		return nil, err
	}
	return podList.Items, nil
}

func (r *HealthCheckReconciler) getNodesToCheck(ctx context.Context, healthCheck *healthv1.HealthCheck) ([]corev1.Node, error) {
	var nodeList corev1.NodeList
	if err := r.List(ctx, &nodeList); err != nil {
		return nil, err
	}
	return nodeList.Items, nil
}

func (r *HealthCheckReconciler) checkPodHealth(pod *corev1.Pod) *healthv1.PodHealthStatus {
	// 检查 Pod 相位
	if pod.Status.Phase != corev1.PodRunning && pod.Status.Phase != corev1.PodSucceeded {
		return &healthv1.PodHealthStatus{
			Namespace: pod.Namespace,
			Name:      pod.Name,
			Phase:     pod.Status.Phase,
			Reason:    fmt.Sprintf("Pod in %s state", pod.Status.Phase),
		}
	}

	// 检查容器状态
	for _, containerStatus := range pod.Status.ContainerStatuses {
		if !containerStatus.Ready {
			reason := "NotReady"
			restartCount := containerStatus.RestartCount

			if containerStatus.State.Waiting != nil {
				reason = containerStatus.State.Waiting.Reason
				if reason == "CrashLoopBackOff" || reason == "ImagePullBackOff" || reason == "ErrImagePull" {
					return &healthv1.PodHealthStatus{
						Namespace:    pod.Namespace,
						Name:         pod.Name,
						Phase:        pod.Status.Phase,
						Reason:       reason,
						Container:    containerStatus.Name,
						RestartCount: restartCount,
					}
				}
			}

			if containerStatus.State.Terminated != nil {
				reason = containerStatus.State.Terminated.Reason
				if reason == "Error" || reason == "OOMKilled" {
					return &healthv1.PodHealthStatus{
						Namespace:    pod.Namespace,
						Name:         pod.Name,
						Phase:        pod.Status.Phase,
						Reason:       reason,
						Container:    containerStatus.Name,
						RestartCount: restartCount,
					}
				}
			}
		}
	}

	return nil
}

func (r *HealthCheckReconciler) checkNodeHealth(node *corev1.Node, unschedulableAsUnhealthy bool) *healthv1.NodeHealthStatus {
	// 检查 Ready 状态
	for _, condition := range node.Status.Conditions {
		if condition.Type == corev1.NodeReady {
			if condition.Status != corev1.ConditionTrue {
				return &healthv1.NodeHealthStatus{
					Name:          node.Name,
					Ready:         false,
					Unschedulable: node.Spec.Unschedulable,
					Reason:        condition.Reason,
				}
			}
			break
		}
	}

	// 检查是否不可调度
	if unschedulableAsUnhealthy && node.Spec.Unschedulable {
		return &healthv1.NodeHealthStatus{
			Name:          node.Name,
			Ready:         true,
			Unschedulable: true,
			Reason:        "Node marked as unschedulable",
		}
	}

	return nil
}

func (r *HealthCheckReconciler) analyzeResourceQuota(pod *corev1.Pod) *healthv1.QuotaRecommendation {
	for _, container := range pod.Spec.Containers {
		resources := container.Resources

		// 检查 CPU
		cpuReq := resources.Requests.Cpu()
		cpuLim := resources.Limits.Cpu()
		if cpuReq.IsZero() && cpuLim.IsZero() {
			return &healthv1.QuotaRecommendation{
				Namespace:    pod.Namespace,
				PodName:      pod.Name,
				Container:    container.Name,
				ResourceType: "CPU",
				Current:      "Not set",
				Recommended:  "requests: 100m, limits: 500m",
				Reason:       "No CPU limits set, risk of resource exhaustion",
			}
		}

		// 检查 Memory
		memReq := resources.Requests.Memory()
		memLim := resources.Limits.Memory()
		if memReq.IsZero() && memLim.IsZero() {
			return &healthv1.QuotaRecommendation{
				Namespace:    pod.Namespace,
				PodName:      pod.Name,
				Container:    container.Name,
				ResourceType: "Memory",
				Current:      "Not set",
				Recommended:  "requests: 256Mi, limits: 1Gi",
				Reason:       "No memory limits set, risk of OOM kill",
			}
		}

		// 检查 CPU 限制/请求比率
		if !cpuReq.IsZero() && !cpuLim.IsZero() && cpuLim.MilliValue() > cpuReq.MilliValue()*5 {
			return &healthv1.QuotaRecommendation{
				Namespace:    pod.Namespace,
				PodName:      pod.Name,
				Container:    container.Name,
				ResourceType: "CPU",
				Current:      fmt.Sprintf("req: %dm, lim: %dm", cpuReq.MilliValue(), cpuLim.MilliValue()),
				Recommended:  fmt.Sprintf("Adjust limit to ~%dm (3x request)", cpuReq.MilliValue()*3),
				Reason:       "CPU limit/request ratio is too high, poor QoS guarantee",
			}
		}
	}
	return nil
}

func (r *HealthCheckReconciler) checkImageSecurity(pod *corev1.Pod) []healthv1.ImageSecurityIssue {
	var issues []healthv1.ImageSecurityIssue

	vulnerableVersions := map[string]map[string]string{
		"nginx":  {"1.19": "1.25.3-alpine", "1.20": "1.25.3-alpine"},
		"node":   {"14": "20.9.0-alpine", "16": "20.9.0-alpine"},
		"python": {"3.8": "3.12.0-slim", "3.9": "3.12.0-slim"},
		"mysql":  {"5.7": "8.2.0", "8.0": "8.2.0"},
		"redis":  {"6": "7.2.3-alpine", "6.2": "7.2.3-alpine"},
	}

	for _, container := range pod.Spec.Containers {
		image := container.Image

		// 检查 latest 标签
		if len(image) >= 7 && image[len(image)-7:] == ":latest" {
			issues = append(issues, healthv1.ImageSecurityIssue{
				Namespace:      pod.Namespace,
				PodName:        pod.Name,
				Image:          image,
				Severity:       "Medium",
				Description:    "Using latest tag, version not pinned",
				Recommendation: "Use specific version tag",
			})
		}

		// 检查已知漏洞版本
		for baseImage, versions := range vulnerableVersions {
			if len(image) >= len(baseImage) && image[:len(baseImage)] == baseImage {
				for oldVer, safeVer := range versions {
					if len(image) >= len(baseImage)+len(oldVer)+2 &&
						image[len(baseImage)+1:len(baseImage)+1+len(oldVer)] == oldVer {
						issues = append(issues, healthv1.ImageSecurityIssue{
							Namespace:      pod.Namespace,
							PodName:        pod.Name,
							Image:          image,
							Severity:       "High",
							Description:    fmt.Sprintf("Using %s:%s with known vulnerabilities", baseImage, oldVer),
							Recommendation: "Upgrade to safe version",
							SafeVersion:    safeVer,
						})
					}
				}
			}
		}

		// 检查非 alpine/slim 镜像
		if len(image) < 7 || (image[len(image)-7:] != "alpine" &&
			(len(image) < 5 || image[len(image)-5:] != "slim") &&
			(len(image) < 16 || image[len(image)-16:] != "distroless")) {
			issues = append(issues, healthv1.ImageSecurityIssue{
				Namespace:      pod.Namespace,
				PodName:        pod.Name,
				Image:          image,
				Severity:       "Low",
				Description:    "Large base image, larger attack surface",
				Recommendation: "Consider using alpine, slim, or distroless variants",
			})
		}
	}

	return issues
}

func (r *HealthCheckReconciler) performAutoRemediation(ctx context.Context, healthCheck *healthv1.HealthCheck,
	unhealthyPods []healthv1.PodHealthStatus, unhealthyNodes []healthv1.NodeHealthStatus) []healthv1.RestartedContainerStatus {

	var restarted []healthv1.RestartedContainerStatus

	// 重启崩溃的 Pod
	if healthCheck.Spec.AutoRemediation.RestartCrashingPods.Enabled {
		for _, pod := range unhealthyPods {
			if pod.Reason == "CrashLoopBackOff" || pod.Reason == "Error" || pod.Reason == "OOMKilled" {
				if pod.RestartCount >= healthCheck.Spec.PodCheck.MinRestartCount {
					// 删除 Pod 触发重启
					podKey := types.NamespacedName{Namespace: pod.Namespace, Name: pod.Name}
					var targetPod corev1.Pod
					if err := r.Get(ctx, podKey, &targetPod); err == nil {
						if err := r.Delete(ctx, &targetPod, client.GracePeriodSeconds(0)); err == nil {
							restarted = append(restarted, healthv1.RestartedContainerStatus{
								Timestamp:    metav1.Now(),
								Namespace:    pod.Namespace,
								PodName:      pod.Name,
								Container:    pod.Container,
								RestartCount: pod.RestartCount,
							})
							r.Logger.Info("Restarted crashing pod",
								zap.String("namespace", pod.Namespace),
								zap.String("pod", pod.Name))
						}
					}
				}
			}
		}
	}

	// 节点驱逐
	if healthCheck.Spec.AutoRemediation.DrainNodes.Enabled {
		for _, node := range unhealthyNodes {
			if !node.Ready {
				r.Logger.Info("Would drain unhealthy node", zap.String("node", node.Name))
				// 实际的节点驱逐逻辑
			}
		}
	}

	return restarted
}

func (r *HealthCheckReconciler) updateMetrics(healthCheck *healthv1.HealthCheck) {
	labels := []string{healthCheck.Namespace, healthCheck.Name}
	r.Metrics.UnhealthyPods.WithLabelValues(labels...).Set(float64(healthCheck.Status.Summary.UnhealthyPodCount))
	r.Metrics.UnhealthyNodes.WithLabelValues(labels...).Set(float64(healthCheck.Status.Summary.UnhealthyNodeCount))
	r.Metrics.ContainersRestarted.WithLabelValues(labels...).Set(float64(healthCheck.Status.Summary.ContainersRestarted))
	r.Metrics.CheckDuration.WithLabelValues(labels...).Observe(float64(healthCheck.Status.Summary.DurationSeconds))
}

// SetupWithManager sets up the controller with the Manager.
func (r *HealthCheckReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&healthv1.HealthCheck{}).
		Watches(
			&source.Kind{Type: &corev1.Pod{}},
			&handler.EnqueueRequestForObject{},
			builder.WithPredicates(predicate.ResourceVersionChangedPredicate{}),
		).
		Watches(
			&source.Kind{Type: &corev1.Node{}},
			&handler.EnqueueRequestForObject{},
			builder.WithPredicates(predicate.ResourceVersionChangedPredicate{}),
		).
		Complete(r)
}
