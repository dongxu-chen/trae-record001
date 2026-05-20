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

package v1

import (
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// HealthCheckSpec defines the desired state of HealthCheck
type HealthCheckSpec struct {
	// +kubebuilder:validation:Minimum=1
	// 巡检执行间隔（分钟）
	IntervalMinutes int `json:"intervalMinutes,omitempty"`

	// Pod 健康检查配置
	PodCheck PodCheckSpec `json:"podCheck,omitempty"`

	// Node 健康检查配置
	NodeCheck NodeCheckSpec `json:"nodeCheck,omitempty"`

	// 自动修复配置
	AutoRemediation AutoRemediationSpec `json:"autoRemediation,omitempty"`

	// Prometheus 告警触发配置
	PrometheusTrigger PrometheusTriggerSpec `json:"prometheusTrigger,omitempty"`

	// 报告配置
	Report ReportSpec `json:"report,omitempty"`
}

// PodCheckSpec Pod 健康检查配置
type PodCheckSpec struct {
	// 是否启用 Pod 检查
	Enabled bool `json:"enabled,omitempty"`

	// 检查的命名空间列表，空表示所有命名空间
	Namespaces []string `json:"namespaces,omitempty"`

	// 标签选择器
	LabelSelector *metav1.LabelSelector `json:"labelSelector,omitempty"`

	// 异常状态列表，如 CrashLoopBackOff, ImagePullBackOff, Error, Pending 等
	UnhealthyStates []string `json:"unhealthyStates,omitempty"`

	// 最小重启次数，超过才考虑修复
	MinRestartCount int32 `json:"minRestartCount,omitempty"`
}

// NodeCheckSpec Node 健康检查配置
type NodeCheckSpec struct {
	// 是否启用 Node 检查
	Enabled bool `json:"enabled,omitempty"`

	// 节点标签选择器
	LabelSelector *metav1.LabelSelector `json:"labelSelector,omitempty"`

	// 不可调度节点是否标记为异常
	UnschedulableAsUnhealthy bool `json:"unschedulableAsUnhealthy,omitempty"`
}

// AutoRemediationSpec 自动修复配置
type AutoRemediationSpec struct {
	// 是否启用自动修复
	Enabled bool `json:"enabled,omitempty"`

	// 重启崩溃 Pod 配置
	RestartCrashingPods RestartCrashingPodsSpec `json:"restartCrashingPods,omitempty"`

	// 节点驱逐配置
	DrainNodes DrainNodesSpec `json:"drainNodes,omitempty"`

	// 最大并行修复数
	MaxParallel int `json:"maxParallel,omitempty"`
}

// RestartCrashingPodsSpec 重启崩溃 Pod 配置
type RestartCrashingPodsSpec struct {
	// 是否启用
	Enabled bool `json:"enabled,omitempty"`

	// 最大重启次数
	MaxRestarts int32 `json:"maxRestarts,omitempty"`

	// 退避时间（秒）
	BackoffSeconds int32 `json:"backoffSeconds,omitempty"`

	// 最大退避时间（秒）
	MaxBackoffSeconds int32 `json:"maxBackoffSeconds,omitempty"`
}

// DrainNodesSpec 节点驱逐配置
type DrainNodesSpec struct {
	// 是否启用
	Enabled bool `json:"enabled,omitempty"`

	// 驱逐前检查 PDB
	CheckPDB bool `json:"checkPDB,omitempty"`

	// 优雅关闭时间
	GracePeriodSeconds int32 `json:"gracePeriodSeconds,omitempty"`

	// 驱逐时忽略的命名空间
	IgnoreNamespaces []string `json:"ignoreNamespaces,omitempty"`
}

// PrometheusTriggerSpec Prometheus 告警触发配置
type PrometheusTriggerSpec struct {
	// 是否启用 Prometheus 告警触发
	Enabled bool `json:"enabled,omitempty"`

	// Prometheus 服务地址
	ServerAddress string `json:"serverAddress,omitempty"`

	// 触发巡检的告警规则名称列表
	TriggerAlerts []string `json:"triggerAlerts,omitempty"`

	// Alertmanager Webhook 端口
	WebhookPort int `json:"webhookPort,omitempty"`
}

// ReportSpec 报告配置
type ReportSpec struct {
	// 报告格式：html, yaml, text
	Format string `json:"format,omitempty"`

	// 是否保存报告到 PVC
	SaveToPVC bool `json:"saveToPVC,omitempty"`

	// PVC 名称
	PVCName string `json:"pvcName,omitempty"`

	// 邮件通知配置
	EmailNotification EmailNotificationSpec `json:"emailNotification,omitempty"`

	// 钉钉通知配置
	DingTalkNotification DingTalkSpec `json:"dingTalkNotification,omitempty"`

	// 企业微信通知配置
	WeWorkNotification WeWorkSpec `json:"weWorkNotification,omitempty"`
}

// EmailNotificationSpec 邮件通知配置
type EmailNotificationSpec struct {
	Enabled  bool     `json:"enabled,omitempty"`
	SMTPHost string   `json:"smtpHost,omitempty"`
	SMTPPort int      `json:"smtpPort,omitempty"`
	Username string   `json:"username,omitempty"`
	Password string   `json:"password,omitempty"`
	From     string   `json:"from,omitempty"`
	To       []string `json:"to,omitempty"`
}

// DingTalkSpec 钉钉通知配置
type DingTalkSpec struct {
	Enabled     bool   `json:"enabled,omitempty"`
	WebhookURL  string `json:"webhookURL,omitempty"`
	Secret      string `json:"secret,omitempty"`
	AtMobiles   []string `json:"atMobiles,omitempty"`
	AtAll       bool   `json:"atAll,omitempty"`
}

// WeWorkSpec 企业微信通知配置
type WeWorkSpec struct {
	Enabled    bool   `json:"enabled,omitempty"`
	WebhookURL string `json:"webhookURL,omitempty"`
}

// HealthCheckStatus defines the observed state of HealthCheck
type HealthCheckStatus struct {
	// 最近一次巡检时间
	LastCheckTime metav1.Time `json:"lastCheckTime,omitempty"`

	// 巡检状态：Running, Completed, Failed
	Phase string `json:"phase,omitempty"`

	// 异常 Pod 统计
	UnhealthyPods []PodHealthStatus `json:"unhealthyPods,omitempty"`

	// 异常 Node 统计
	UnhealthyNodes []NodeHealthStatus `json:"unhealthyNodes,omitempty"`

	// 已重启的容器统计
	RestartedContainers []RestartedContainerStatus `json:"restartedContainers,omitempty"`

	// 已驱逐的节点统计
	EvictedNodes []EvictedNodeStatus `json:"evictedNodes,omitempty"`

	// 资源配额建议
	QuotaRecommendations []QuotaRecommendation `json:"quotaRecommendations,omitempty"`

	// 镜像安全问题
	ImageSecurityIssues []ImageSecurityIssue `json:"imageSecurityIssues,omitempty"`

	// 汇总统计
	Summary HealthCheckSummary `json:"summary,omitempty"`

	// 错误信息
	Errors []string `json:"errors,omitempty"`

	// 警告信息
	Warnings []string `json:"warnings,omitempty"`
}

// PodHealthStatus Pod 健康状态
type PodHealthStatus struct {
	Namespace string                     `json:"namespace,omitempty"`
	Name      string                     `json:"name,omitempty"`
	Phase     corev1.PodPhase            `json:"phase,omitempty"`
	Reason    string                     `json:"reason,omitempty"`
	Container string                     `json:"container,omitempty"`
	RestartCount int32                   `json:"restartCount,omitempty"`
}

// NodeHealthStatus Node 健康状态
type NodeHealthStatus struct {
	Name          string `json:"name,omitempty"`
	Ready         bool   `json:"ready,omitempty"`
	Unschedulable bool   `json:"unschedulable,omitempty"`
	Reason        string `json:"reason,omitempty"`
}

// RestartedContainerStatus 已重启容器状态
type RestartedContainerStatus struct {
	Timestamp     metav1.Time `json:"timestamp,omitempty"`
	Namespace     string      `json:"namespace,omitempty"`
	PodName       string      `json:"podName,omitempty"`
	Container     string      `json:"container,omitempty"`
	RestartCount  int32       `json:"restartCount,omitempty"`
	BackoffCount  int32       `json:"backoffCount,omitempty"`
}

// EvictedNodeStatus 已驱逐节点状态
type EvictedNodeStatus struct {
	NodeName      string      `json:"nodeName,omitempty"`
	EvictionTime  metav1.Time `json:"evictionTime,omitempty"`
	EvictedPods   int         `json:"evictedPods,omitempty"`
}

// QuotaRecommendation 资源配额建议
type QuotaRecommendation struct {
	Namespace   string `json:"namespace,omitempty"`
	PodName     string `json:"podName,omitempty"`
	Container   string `json:"container,omitempty"`
	ResourceType string `json:"resourceType,omitempty"` // CPU, Memory
	Current     string `json:"current,omitempty"`
	Recommended string `json:"recommended,omitempty"`
	Reason      string `json:"reason,omitempty"`
}

// ImageSecurityIssue 镜像安全问题
type ImageSecurityIssue struct {
	Namespace    string `json:"namespace,omitempty"`
	PodName      string `json:"podName,omitempty"`
	Image        string `json:"image,omitempty"`
	Severity     string `json:"severity,omitempty"` // High, Medium, Low
	Description  string `json:"description,omitempty"`
	Recommendation string `json:"recommendation,omitempty"`
	SafeVersion  string `json:"safeVersion,omitempty"`
}

// HealthCheckSummary 巡检汇总
type HealthCheckSummary struct {
	TotalPodsChecked          int `json:"totalPodsChecked,omitempty"`
	UnhealthyPodCount         int `json:"unhealthyPodCount,omitempty"`
	TotalNodesChecked         int `json:"totalNodesChecked,omitempty"`
	UnhealthyNodeCount        int `json:"unhealthyNodeCount,omitempty"`
	ContainersRestarted       int `json:"containersRestarted,omitempty"`
	NodesEvicted              int `json:"nodesEvicted,omitempty"`
	QuotaRecommendationsCount int `json:"quotaRecommendationsCount,omitempty"`
	ImageSecurityIssuesCount  int `json:"imageSecurityIssuesCount,omitempty"`
	ErrorCount                int `json:"errorCount,omitempty"`
	WarningCount              int `json:"warningCount,omitempty"`
	DurationSeconds           int `json:"durationSeconds,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Age",type="date",JSONPath=".metadata.creationTimestamp"
// +kubebuilder:printcolumn:name="Phase",type="string",JSONPath=".status.phase"
// +kubebuilder:printcolumn:name="LastCheck",type="date",JSONPath=".status.lastCheckTime"
// +kubebuilder:printcolumn:name="UnhealthyPods",type="integer",JSONPath=".status.summary.unhealthyPodCount"
// +kubebuilder:printcolumn:name="UnhealthyNodes",type="integer",JSONPath=".status.summary.unhealthyNodeCount"

// HealthCheck is the Schema for the healthchecks API
type HealthCheck struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   HealthCheckSpec   `json:"spec,omitempty"`
	Status HealthCheckStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

// HealthCheckList contains a list of HealthCheck
type HealthCheckList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []HealthCheck `json:"items"`
}

func init() {
	SchemeBuilder.Register(&HealthCheck{}, &HealthCheckList{})
}
