package policy

import (
	"fmt"
	"reflect"

	v1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s-network-policy-recommender/pkg/neo4jclient"
)

type ConflictType string

const (
	ConflictOverlap        ConflictType = "OVERLAP"
	ConflictContradiction  ConflictType = "CONTRADICTION"
	ConflictRedundancy     ConflictType = "REDUNDANCY"
	ConflictShadowing      ConflictType = "SHADOWING"
	ConflictImplicitDeny   ConflictType = "IMPLICIT_DENY"
	ConflictAllowDenyClash ConflictType = "ALLOW_DENY_CLASH"
)

type PolicyConflict struct {
	Type           ConflictType    `json:"type"`
	Severity       string          `json:"severity"`
	PolicyA        string          `json:"policyA"`
	PolicyB        string          `json:"policyB"`
	Description    string          `json:"description"`
	Recommendation string          `json:"recommendation"`
	AffectedTraffic []AffectedFlow `json:"affectedTraffic,omitempty"`
}

type AffectedFlow struct {
	Source      string `json:"source"`
	Destination string `json:"destination"`
	Port        int32  `json:"port"`
	Protocol    string `json:"protocol"`
	Direction   string `json:"direction"`
}

type ConflictDetector struct{}

func NewConflictDetector() *ConflictDetector {
	return &ConflictDetector{}
}

func (d *ConflictDetector) DetectConflicts(policies []v1.NetworkPolicy) []PolicyConflict {
	var conflicts []PolicyConflict

	for i := 0; i < len(policies); i++ {
		for j := i + 1; j < len(policies); j++ {
			policyA := policies[i]
			policyB := policies[j]

			if c := d.checkShadowing(policyA, policyB); c != nil {
				conflicts = append(conflicts, *c)
			}

			if c := d.checkOverlap(policyA, policyB); c != nil {
				conflicts = append(conflicts, *c)
			}

			if c := d.checkRedundancy(policyA, policyB); c != nil {
				conflicts = append(conflicts, *c)
			}

			if c := d.checkAllowDenyInteraction(policyA, policyB); c != nil {
				conflicts = append(conflicts, *c)
			}

			if c := d.checkImplicitDenyConflict(policyA, policyB); c != nil {
				conflicts = append(conflicts, *c)
			}
		}
	}

	return conflicts
}

func (d *ConflictDetector) isDenyPolicy(p v1.NetworkPolicy) bool {
	if p.Labels == nil {
		return false
	}
	pt, ok := p.Labels["policy-type"]
	return ok && pt == "default-deny"
}

func (d *ConflictDetector) isAllowPolicy(p v1.NetworkPolicy) bool {
	if p.Labels == nil {
		return len(p.Spec.Ingress) > 0 || len(p.Spec.Egress) > 0
	}
	pt, ok := p.Labels["policy-type"]
	return !ok || (pt != "default-deny")
}

func (d *ConflictDetector) checkAllowDenyInteraction(a, b v1.NetworkPolicy) *PolicyConflict {
	var denyPolicy, allowPolicy v1.NetworkPolicy
	var denyName, allowName string

	aIsDeny := d.isDenyPolicy(a)
	bIsDeny := d.isDenyPolicy(b)
	aIsAllow := d.isAllowPolicy(a)
	bIsAllow := d.isAllowPolicy(b)

	if aIsDeny && bIsAllow {
		denyPolicy, allowPolicy = a, b
		denyName, allowName = a.Name, b.Name
	} else if bIsDeny && aIsAllow {
		denyPolicy, allowPolicy = b, a
		denyName, allowName = b.Name, a.Name
	} else if aIsAllow && bIsAllow {
		return d.checkAllowAllowInteraction(a, b)
	} else {
		return nil
	}

	if !d.selectorsOverlap(denyPolicy.Spec.PodSelector, allowPolicy.Spec.PodSelector) {
		return nil
	}

	var affectedFlows []AffectedFlow

	for _, ingress := range allowPolicy.Spec.Ingress {
		for _, port := range ingress.Ports {
			flow := AffectedFlow{
				Direction: "ingress",
				Protocol:  "TCP",
				Port:      0,
			}
			if port.Protocol != nil {
				flow.Protocol = string(*port.Protocol)
			}
			if port.Port != nil {
				flow.Port = port.Port.IntVal
			}
			if len(ingress.From) > 0 {
				for _, from := range ingress.From {
					if from.PodSelector != nil {
						flow.Source = fmt.Sprintf("pod(labels=%v)", from.PodSelector.MatchLabels)
					}
					if from.NamespaceSelector != nil {
						flow.Source = fmt.Sprintf("ns(labels=%v)", from.NamespaceSelector.MatchLabels)
					}
				}
			}
			flow.Destination = fmt.Sprintf("pod(labels=%v)", allowPolicy.Spec.PodSelector.MatchLabels)
			affectedFlows = append(affectedFlows, flow)
		}
	}

	for _, egress := range allowPolicy.Spec.Egress {
		for _, port := range egress.Ports {
			flow := AffectedFlow{
				Direction: "egress",
				Protocol:  "TCP",
				Port:      0,
			}
			if port.Protocol != nil {
				flow.Protocol = string(*port.Protocol)
			}
			if port.Port != nil {
				flow.Port = port.Port.IntVal
			}
			flow.Source = fmt.Sprintf("pod(labels=%v)", allowPolicy.Spec.PodSelector.MatchLabels)
			if len(egress.To) > 0 {
				for _, to := range egress.To {
					if to.PodSelector != nil {
						flow.Destination = fmt.Sprintf("pod(labels=%v)", to.PodSelector.MatchLabels)
					}
					if to.NamespaceSelector != nil {
						flow.Destination = fmt.Sprintf("ns(labels=%v)", to.NamespaceSelector.MatchLabels)
					}
				}
			}
			affectedFlows = append(affectedFlows, flow)
		}
	}

	if len(affectedFlows) == 0 {
		return nil
	}

	return &PolicyConflict{
		Type:        ConflictAllowDenyClash,
		Severity:   "HIGH",
		PolicyA:    allowName,
		PolicyB:    denyName,
		Description: fmt.Sprintf("ALLOW policy '%s' and DENY policy '%s' target overlapping pods - traffic may be implicitly blocked", allowName, denyName),
		Recommendation: "Review the deny policy scope; ensure ALLOW rules are not unintentionally blocked by the default-deny",
		AffectedTraffic: affectedFlows,
	}
}

func (d *ConflictDetector) checkAllowAllowInteraction(a, b v1.NetworkPolicy) *PolicyConflict {
	if !d.selectorsOverlap(a.Spec.PodSelector, b.Spec.PodSelector) {
		return nil
	}

	aHasIngress := hasPolicyType(a, v1.PolicyTypeIngress)
	bHasIngress := hasPolicyType(b, v1.PolicyTypeIngress)
	aHasEgress := hasPolicyType(a, v1.PolicyTypeEgress)
	bHasEgress := hasPolicyType(b, v1.PolicyTypeEgress)

	var implicitDenyDirs []string
	if aHasIngress && !bHasIngress && len(b.Spec.Ingress) == 0 {
		implicitDenyDirs = append(implicitDenyDirs, "ingress")
	}
	if bHasIngress && !aHasIngress && len(a.Spec.Ingress) == 0 {
		implicitDenyDirs = append(implicitDenyDirs, "ingress")
	}
	if aHasEgress && !bHasEgress && len(b.Spec.Egress) == 0 {
		implicitDenyDirs = append(implicitDenyDirs, "egress")
	}
	if bHasEgress && !aHasEgress && len(a.Spec.Egress) == 0 {
		implicitDenyDirs = append(implicitDenyDirs, "egress")
	}

	if len(implicitDenyDirs) == 0 {
		return nil
	}

	var affectedFlows []AffectedFlow
	for _, dir := range implicitDenyDirs {
		if dir == "ingress" {
			policyWithRules := a
			if len(a.Spec.Ingress) == 0 {
				policyWithRules = b
			}
			for _, ingress := range policyWithRules.Spec.Ingress {
				for _, port := range ingress.Ports {
					flow := AffectedFlow{
						Direction:   "ingress",
						Protocol:    "TCP",
						Port:        0,
						Source:      "various",
						Destination: fmt.Sprintf("pod(labels=%v)", a.Spec.PodSelector.MatchLabels),
					}
					if port.Protocol != nil {
						flow.Protocol = string(*port.Protocol)
					}
					if port.Port != nil {
						flow.Port = port.Port.IntVal
					}
					affectedFlows = append(affectedFlows, flow)
				}
			}
		}
	}

	return &PolicyConflict{
		Type:        ConflictAllowDenyClash,
		Severity:   "MEDIUM",
		PolicyA:    a.Name,
		PolicyB:    b.Name,
		Description: fmt.Sprintf("Policies '%s' and '%s' have asymmetric policy types (%v) - implicit deny may block allowed traffic", a.Name, b.Name, implicitDenyDirs),
		Recommendation: "Align policy types between overlapping policies to avoid implicit deny gaps",
		AffectedTraffic: affectedFlows,
	}
}

func (d *ConflictDetector) checkImplicitDenyConflict(a, b v1.NetworkPolicy) *PolicyConflict {
	aSelectsAll := len(a.Spec.PodSelector.MatchLabels) == 0 && len(a.Spec.PodSelector.MatchExpressions) == 0
	bSelectsAll := len(b.Spec.PodSelector.MatchLabels) == 0 && len(b.Spec.PodSelector.MatchExpressions) == 0

	if !aSelectsAll && !bSelectsAll {
		return nil
	}

	var broadPolicy, narrowPolicy v1.NetworkPolicy
	if aSelectsAll {
		broadPolicy, narrowPolicy = a, b
	} else {
		broadPolicy, narrowPolicy = b, a
	}

	broadHasIngress := hasPolicyType(broadPolicy, v1.PolicyTypeIngress) && len(broadPolicy.Spec.Ingress) > 0
	broadHasEgress := hasPolicyType(broadPolicy, v1.PolicyTypeEgress) && len(broadPolicy.Spec.Egress) > 0

	if !broadHasIngress && !broadHasEgress {
		return nil
	}

	var affectedFlows []AffectedFlow
	if broadHasIngress {
		for _, ingress := range broadPolicy.Spec.Ingress {
			for _, port := range ingress.Ports {
				flow := AffectedFlow{
					Direction:   "ingress",
					Protocol:    "TCP",
					Port:        0,
					Destination: "all-pods",
				}
				if port.Protocol != nil {
					flow.Protocol = string(*port.Protocol)
				}
				if port.Port != nil {
					flow.Port = port.Port.IntVal
				}
				affectedFlows = append(affectedFlows, flow)
			}
		}
	}

	narrowHasIngress := hasPolicyType(narrowPolicy, v1.PolicyTypeIngress) && len(narrowPolicy.Spec.Ingress) == 0
	narrowHasEgress := hasPolicyType(narrowPolicy, v1.PolicyTypeEgress) && len(narrowPolicy.Spec.Egress) == 0

	if narrowHasIngress || narrowHasEgress {
		return &PolicyConflict{
			Type:        ConflictImplicitDeny,
			Severity:   "HIGH",
			PolicyA:    broadPolicy.Name,
			PolicyB:    narrowPolicy.Name,
			Description: fmt.Sprintf("Policy '%s' selects specific pods but has no allow rules, while '%s' allows traffic to all pods - narrow policy implicitly denies traffic that broad policy allows", narrowPolicy.Name, broadPolicy.Name),
			Recommendation: "Add explicit allow rules to the narrow policy or remove the empty policy types",
			AffectedTraffic: affectedFlows,
		}
	}

	return nil
}

func hasPolicyType(p v1.NetworkPolicy, pt v1.PolicyType) bool {
	for _, t := range p.Spec.PolicyTypes {
		if t == pt {
			return true
		}
	}
	return false
}

func (d *ConflictDetector) checkShadowing(a, b v1.NetworkPolicy) *PolicyConflict {
	aSelectsAll := len(a.Spec.PodSelector.MatchLabels) == 0 && len(a.Spec.PodSelector.MatchExpressions) == 0
	bSelectsAll := len(b.Spec.PodSelector.MatchLabels) == 0 && len(b.Spec.PodSelector.MatchExpressions) == 0

	if aSelectsAll && !bSelectsAll {
		return &PolicyConflict{
			Type:        ConflictShadowing,
			Severity:   "HIGH",
			PolicyA:    a.Name,
			PolicyB:    b.Name,
			Description: fmt.Sprintf("Policy '%s' (selects all pods) may shadow '%s' for overlapping traffic", a.Name, b.Name),
			Recommendation: "Consider reordering or merging policies, or make selectors more specific",
		}
	}

	if bSelectsAll && !aSelectsAll {
		return &PolicyConflict{
			Type:        ConflictShadowing,
			Severity:   "HIGH",
			PolicyA:    b.Name,
			PolicyB:    a.Name,
			Description: fmt.Sprintf("Policy '%s' (selects all pods) may shadow '%s' for overlapping traffic", b.Name, a.Name),
			Recommendation: "Consider reordering or merging policies, or make selectors more specific",
		}
	}

	return nil
}

func (d *ConflictDetector) checkOverlap(a, b v1.NetworkPolicy) *PolicyConflict {
	selectorOverlap := d.selectorsOverlap(a.Spec.PodSelector, b.Spec.PodSelector)
	if !selectorOverlap {
		return nil
	}

	ingressOverlap := d.ingressRulesOverlap(a.Spec.Ingress, b.Spec.Ingress)
	egressOverlap := d.egressRulesOverlap(a.Spec.Egress, b.Spec.Egress)

	if ingressOverlap || egressOverlap {
		return &PolicyConflict{
			Type:        ConflictOverlap,
			Severity:   "MEDIUM",
			PolicyA:    a.Name,
			PolicyB:    b.Name,
			Description: "Policies have overlapping pod selectors and traffic rules",
			Recommendation: "Review the overlapping rules and consider consolidation",
		}
	}

	return nil
}

func (d *ConflictDetector) checkRedundancy(a, b v1.NetworkPolicy) *PolicyConflict {
	if !reflect.DeepEqual(a.Spec.PodSelector, b.Spec.PodSelector) {
		return nil
	}

	if !d.ingressRulesEqual(a.Spec.Ingress, b.Spec.Ingress) {
		return nil
	}

	if !d.egressRulesEqual(a.Spec.Egress, b.Spec.Egress) {
		return nil
	}

	return &PolicyConflict{
		Type:        ConflictRedundancy,
		Severity:   "LOW",
		PolicyA:    a.Name,
		PolicyB:    b.Name,
		Description: "Policies are identical - one is redundant",
		Recommendation: "Remove one of the duplicate policies",
	}
}

func (d *ConflictDetector) selectorsOverlap(a, b metav1.LabelSelector) bool {
	if len(a.MatchLabels) == 0 && len(a.MatchExpressions) == 0 {
		return true
	}
	if len(b.MatchLabels) == 0 && len(b.MatchExpressions) == 0 {
		return true
	}

	for k, v := range a.MatchLabels {
		if bv, ok := b.MatchLabels[k]; ok && bv != v {
			return false
		}
	}

	return true
}

func (d *ConflictDetector) ingressRulesOverlap(a, b []v1.NetworkPolicyIngressRule) bool {
	if len(a) == 0 || len(b) == 0 {
		return false
	}

	for _, ruleA := range a {
		for _, ruleB := range b {
			if d.portsOverlap(ruleA.Ports, ruleB.Ports) {
				return true
			}
		}
	}

	return false
}

func (d *ConflictDetector) egressRulesOverlap(a, b []v1.NetworkPolicyEgressRule) bool {
	if len(a) == 0 || len(b) == 0 {
		return false
	}

	for _, ruleA := range a {
		for _, ruleB := range b {
			if d.portsOverlap(ruleA.Ports, ruleB.Ports) {
				return true
			}
		}
	}

	return false
}

func (d *ConflictDetector) portsOverlap(a, b []v1.NetworkPolicyPort) bool {
	if len(a) == 0 || len(b) == 0 {
		return true
	}

	for _, pa := range a {
		for _, pb := range b {
			if d.portEqual(pa, pb) {
				return true
			}
		}
	}

	return false
}

func (d *ConflictDetector) portEqual(a, b v1.NetworkPolicyPort) bool {
	if a.Protocol != nil && b.Protocol != nil && *a.Protocol != *b.Protocol {
		return false
	}
	if a.Port != nil && b.Port != nil && !reflect.DeepEqual(a.Port, b.Port) {
		return false
	}
	return true
}

func (d *ConflictDetector) ingressRulesEqual(a, b []v1.NetworkPolicyIngressRule) bool {
	return reflect.DeepEqual(a, b)
}

func (d *ConflictDetector) egressRulesEqual(a, b []v1.NetworkPolicyEgressRule) bool {
	return reflect.DeepEqual(a, b)
}

type SimulationResult struct {
	AllowedFlows   []SimulatedFlow `json:"allowedFlows"`
	DeniedFlows    []SimulatedFlow `json:"deniedFlows"`
	PolicyCoverage float64         `json:"policyCoverage"`
}

type SimulatedFlow struct {
	Source      string `json:"source"`
	Destination string `json:"destination"`
	Port        int32  `json:"port"`
	Protocol    string `json:"protocol"`
	Allowed     bool   `json:"allowed"`
	Reason      string `json:"reason"`
}

func (d *ConflictDetector) SimulatePolicy(policy *v1.NetworkPolicy, flows []neo4jclient.FlowEdge) *SimulationResult {
	result := &SimulationResult{}

	for _, flow := range flows {
		simFlow := SimulatedFlow{
			Source:      fmt.Sprintf("%s/%s", flow.SourceNamespace, flow.SourceName),
			Destination: fmt.Sprintf("%s/%s", flow.DestNamespace, flow.DestName),
			Port:        flow.Port,
			Protocol:    flow.Protocol,
		}

		if d.isFlowAllowed(policy, flow) {
			simFlow.Allowed = true
			simFlow.Reason = "Matched policy ingress/egress rule"
			result.AllowedFlows = append(result.AllowedFlows, simFlow)
		} else {
			simFlow.Allowed = false
			simFlow.Reason = "No matching policy rule - would be denied"
			result.DeniedFlows = append(result.DeniedFlows, simFlow)
		}
	}

	if len(flows) > 0 {
		result.PolicyCoverage = float64(len(result.AllowedFlows)) / float64(len(flows))
	}

	return result
}

func (d *ConflictDetector) isFlowAllowed(policy *v1.NetworkPolicy, flow neo4jclient.FlowEdge) bool {
	for _, ingress := range policy.Spec.Ingress {
		if len(ingress.Ports) == 0 {
			return true
		}
		for _, port := range ingress.Ports {
			if d.portMatches(port, flow.Port, flow.Protocol) {
				return true
			}
		}
	}

	for _, egress := range policy.Spec.Egress {
		if len(egress.Ports) == 0 {
			return true
		}
		for _, port := range egress.Ports {
			if d.portMatches(port, flow.Port, flow.Protocol) {
				return true
			}
		}
	}

	return false
}

func (d *ConflictDetector) portMatches(policyPort v1.NetworkPolicyPort, flowPort int32, flowProtocol string) bool {
	if policyPort.Protocol != nil && string(*policyPort.Protocol) != flowProtocol {
		return false
	}

	if policyPort.Port == nil {
		return true
	}

	if policyPort.Port.Type == metav1.IntOrStringInt {
		return policyPort.Port.IntVal == flowPort
	}

	return false
}
