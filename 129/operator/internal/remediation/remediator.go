package remediation

import (
	"context"
	"fmt"
	"time"

	"go.uber.org/zap"
	corev1 "k8s.io/api/core/v1"
	policyv1 "k8s.io/api/policy/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"

	healthv1 "github.com/k8s-health-checker/operator/api/v1"
)

type Remediator struct {
	Client client.Client
	Logger *zap.Logger
}

// PodRestartHistory tracks restart history for backoff
type PodRestartHistory struct {
	PodKey         string
	LastRestartTime metav1.Time
	RestartCount   int32
	BackoffSeconds int32
}

var restartHistory = make(map[string]*PodRestartHistory)

// RestartCrashingPod restarts a pod with backoff logic
func (r *Remediator) RestartCrashingPod(ctx context.Context, podHealth healthv1.PodHealthStatus,
	maxRestarts int32, backoffBase int32, maxBackoff int32) (bool, error) {

	podKey := fmt.Sprintf("%s/%s", podHealth.Namespace, podHealth.Name)

	// Check backoff
	history, exists := restartHistory[podKey]
	if exists {
		if history.RestartCount >= maxRestarts {
			r.Logger.Warn("Max restarts reached, skipping",
				zap.String("pod", podKey),
				zap.Int32("maxRestarts", maxRestarts))
			return false, nil
		}

		nextAllowed := history.LastRestartTime.Time.Add(time.Duration(history.BackoffSeconds) * time.Second)
		if time.Now().Before(nextAllowed) {
			r.Logger.Warn("Backoff active, skipping restart",
				zap.String("pod", podKey),
				zap.Duration("remaining", time.Until(nextAllowed)))
			return false, nil
		}
	}

	// Get and delete the pod
	var pod corev1.Pod
	if err := r.Client.Get(ctx, types.NamespacedName{
		Namespace: podHealth.Namespace,
		Name:      podHealth.Name,
	}, &pod); err != nil {
		return false, err
	}

	// Delete pod to trigger restart
	if err := r.Client.Delete(ctx, &pod, client.GracePeriodSeconds(0)); err != nil {
		return false, err
	}

	// Update restart history
	if !exists {
		history = &PodRestartHistory{PodKey: podKey}
	}
	history.LastRestartTime = metav1.Now()
	history.RestartCount++
	history.BackoffSeconds = min(backoffBase*(1<<(history.RestartCount-1)), maxBackoff)
	restartHistory[podKey] = history

	r.Logger.Info("Successfully restarted pod",
		zap.String("pod", podKey),
		zap.Int32("restartCount", history.RestartCount),
		zap.Int32("nextBackoff", history.BackoffSeconds))

	return true, nil
}

// DrainNode drains a node safely with PDB check
func (r *Remediator) DrainNode(ctx context.Context, nodeName string, checkPDB bool,
	gracePeriodSeconds int32, ignoreNamespaces []string) (bool, error) {

	r.Logger.Info("Starting node drain", zap.String("node", nodeName))

	// Mark node as unschedulable first
	var node corev1.Node
	if err := r.Client.Get(ctx, types.NamespacedName{Name: nodeName}, &node); err != nil {
		return false, err
	}

	if !node.Spec.Unschedulable {
		node.Spec.Unschedulable = true
		if err := r.Client.Update(ctx, &node); err != nil {
			return false, err
		}
		r.Logger.Info("Node marked as unschedulable", zap.String("node", nodeName))
	}

	// Get all pods on the node
	var allPods corev1.PodList
	if err := r.Client.List(ctx, &allPods); err != nil {
		return false, err
	}

	var podsOnNode []corev1.Pod
	for _, pod := range allPods.Items {
		if pod.Spec.NodeName == nodeName {
			// Skip ignored namespaces
			ignored := false
			for _, ns := range ignoreNamespaces {
				if pod.Namespace == ns {
					ignored = true
					break
				}
			}
			if !ignored {
				podsOnNode = append(podsOnNode, pod)
			}
		}
	}

	// Check PDB if enabled
	if checkPDB {
		canDrain, violations := r.checkPDBConstraints(ctx, podsOnNode)
		if !canDrain {
			for _, v := range violations {
				r.Logger.Warn("PDB violation", zap.String("violation", v))
			}
			return false, fmt.Errorf("PDB constraints violated, cannot drain node")
		}
	}

	// Evict each pod
	evictedCount := 0
	for _, pod := range podsOnNode {
		// Skip daemonsets (typically managed separately)
		isDaemonSet := false
		for _, owner := range pod.OwnerReferences {
			if owner.Kind == "DaemonSet" {
				isDaemonSet = true
				break
			}
		}
		if isDaemonSet {
			continue
		}

		// Create eviction
		eviction := &policyv1.Eviction{
			ObjectMeta: metav1.ObjectMeta{
				Name:      pod.Name,
				Namespace: pod.Namespace,
			},
			DeleteOptions: &metav1.DeleteOptions{
				GracePeriodSeconds: &gracePeriodSeconds,
			},
		}

		if err := r.Client.SubResource("eviction").Create(ctx, &pod, eviction); err != nil {
			r.Logger.Warn("Failed to evict pod",
				zap.String("pod", pod.Name),
				zap.String("namespace", pod.Namespace),
				zap.Error(err))
			continue
		}

		evictedCount++
		r.Logger.Info("Evicted pod",
			zap.String("pod", pod.Name),
			zap.String("namespace", pod.Namespace))
	}

	r.Logger.Info("Node drain completed",
		zap.String("node", nodeName),
		zap.Int("evictedPods", evictedCount))

	return true, nil
}

func (r *Remediator) checkPDBConstraints(ctx context.Context, pods []corev1.Pod) (bool, []string) {
	var violations []string

	// Get all PDBs
	var pdbList policyv1.PodDisruptionBudgetList
	if err := r.Client.List(ctx, &pdbList); err != nil {
		violations = append(violations, fmt.Sprintf("Failed to list PDBs: %v", err))
		return false, violations
	}

	// Group pods by PDB
	pdbPodCount := make(map[string]int)
	for _, pod := range pods {
		for _, pdb := range pdbList.Items {
			if pdb.Namespace == pod.Namespace {
				// Simple label selector match
				selector, err := metav1.LabelSelectorAsSelector(pdb.Spec.Selector)
				if err != nil {
					continue
				}
				if selector.Matches(labelsSet(pod.Labels)) {
					pdbPodCount[fmt.Sprintf("%s/%s", pdb.Namespace, pdb.Name)]++
				}
			}
		}
	}

	// Check minAvailable
	for _, pdb := range pdbList.Items {
		pdbKey := fmt.Sprintf("%s/%s", pdb.Namespace, pdb.Name)
		podsToEvict := pdbPodCount[pdbKey]
		if podsToEvict == 0 {
			continue
		}

		healthy := pdb.Status.CurrentHealthy
		minAvailable := pdb.Spec.MinAvailable

		if minAvailable != nil {
			minAvailInt := int(minAvailable.IntValue())
			if healthy-int32(podsToEvict) < int32(minAvailInt) {
				violations = append(violations,
					fmt.Sprintf("PDB %s: evicting %d pods would violate minAvailable=%d, currentHealthy=%d",
						pdbKey, podsToEvict, minAvailInt, healthy))
			}
		}
	}

	return len(violations) == 0, violations
}

func labelsSet(labels map[string]string) labels {
	return labels
}

type labels map[string]string

func (l labels) Has(label string) bool {
	_, exists := l[label]
	return exists
}

func (l labels) Get(label string) string {
	return l[label]
}

func min(a, b int32) int32 {
	if a < b {
		return a
	}
	return b
}
