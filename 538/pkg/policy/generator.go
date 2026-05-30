package policy

import (
	"context"
	"fmt"
	"sort"

	"k8s-network-policy-recommender/pkg/config"
	"k8s-network-policy-recommender/pkg/k8s"
	"k8s-network-policy-recommender/pkg/neo4jclient"

	v1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

type Generator struct {
	config    config.PolicyConfig
	k8sClient *k8s.Client
	neo4j     *neo4jclient.Client
}

type PolicyRecommendation struct {
	Name         string            `json:"name"`
	Namespace    string            `json:"namespace"`
	Description  string            `json:"description"`
	Policy       *v1.NetworkPolicy `json:"policy"`
	Reasoning    []string          `json:"reasoning"`
	Confidence   float64           `json:"confidence"`
	CoveredPairs []CommPair        `json:"coveredPairs"`
}

type CommPair struct {
	Source      string            `json:"source"`
	Destination string            `json:"destination"`
	Protocol    string            `json:"protocol"`
	Port        int32             `json:"port"`
	SourceType  string            `json:"sourceType"`
	DestType    string            `json:"destType"`
	SourceLabel map[string]string `json:"sourceLabel"`
	DestLabel   map[string]string `json:"destLabel"`
}

type CoverageReport struct {
	TotalPairs       int              `json:"totalPairs"`
	CoveredPairs     int              `json:"coveredPairs"`
	CoverageRatio    float64          `json:"coverageRatio"`
	UncoveredPairs   []CommPair       `json:"uncoveredPairs"`
	CoveredByPolicy  map[string][]CommPair `json:"coveredByPolicy"`
}

func NewGenerator(cfg config.PolicyConfig, k8sClient *k8s.Client, neo4j *neo4jclient.Client) *Generator {
	return &Generator{
		config:    cfg,
		k8sClient: k8sClient,
		neo4j:     neo4j,
	}
}

func (g *Generator) GeneratePolicies(ctx context.Context, namespace string) ([]PolicyRecommendation, *CoverageReport, error) {
	flows, err := g.neo4j.GetFlowsByNamespace(ctx, namespace)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to get flows: %w", err)
	}

	pods, err := g.k8sClient.GetPods(ctx, namespace)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to get pods: %w", err)
	}

	services, err := g.k8sClient.GetServices(ctx, namespace)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to get services: %w", err)
	}

	allPairs := g.enumerateAllPairs(flows, pods, namespace)

	ingressMap, egressMap := g.analyzeFlows(flows, pods, services)

	var recommendations []PolicyRecommendation

	defaultDenyRec := g.generateDefaultDenyPolicy(namespace)
	recommendations = append(recommendations, defaultDenyRec)

	svcPolicies := g.generateServicePolicies(namespace, services, ingressMap, egressMap)
	recommendations = append(recommendations, svcPolicies...)

	podPolicies := g.generatePodPairPolicies(namespace, pods, ingressMap)
	recommendations = append(recommendations, podPolicies...)

	crossNsPolicies := g.generateCrossNamespacePolicies(namespace, flows, pods)
	recommendations = append(recommendations, crossNsPolicies...)

	if g.config.AllowDNS {
		dnsRec := g.generateDNSPolicy(namespace)
		recommendations = append(recommendations, dnsRec)
	}

	coverage := g.computeCoverage(allPairs, recommendations)

	return recommendations, coverage, nil
}

func (g *Generator) enumerateAllPairs(flows []neo4jclient.FlowEdge, pods []k8s.PodInfo, namespace string) []CommPair {
	seen := make(map[string]bool)
	var pairs []CommPair

	for _, flow := range flows {
		srcLabel := make(map[string]string)
		dstLabel := make(map[string]string)
		srcType := "pod"
		dstType := "pod"

		for _, pod := range pods {
			if pod.Name == flow.SourceName && pod.Namespace == flow.SourceNamespace {
				srcLabel = pod.Labels
			}
			if pod.Name == flow.DestName && pod.Namespace == flow.DestNamespace {
				dstLabel = pod.Labels
			}
		}

		if flow.SourceNamespace != namespace {
			srcType = "external"
		}
		if flow.DestNamespace != namespace {
			dstType = "external"
		}

		pair := CommPair{
			Source:      fmt.Sprintf("%s/%s", flow.SourceNamespace, flow.SourceName),
			Destination: fmt.Sprintf("%s/%s", flow.DestNamespace, flow.DestName),
			Protocol:    flow.Protocol,
			Port:        flow.Port,
			SourceType:  srcType,
			DestType:    dstType,
			SourceLabel: srcLabel,
			DestLabel:   dstLabel,
		}

		key := fmt.Sprintf("%s->%s|%s:%d", pair.Source, pair.Destination, pair.Protocol, pair.Port)
		if !seen[key] {
			seen[key] = true
			pairs = append(pairs, pair)
		}
	}

	return pairs
}

func (g *Generator) computeCoverage(allPairs []CommPair, recommendations []PolicyRecommendation) *CoverageReport {
	report := &CoverageReport{
		TotalPairs:      len(allPairs),
		CoveredByPolicy: make(map[string][]CommPair),
	}

	covered := make(map[string]bool)

	for _, pair := range allPairs {
		pairKey := fmt.Sprintf("%s->%s|%s:%d", pair.Source, pair.Destination, pair.Protocol, pair.Port)
		pairCovered := false

		for _, rec := range recommendations {
			if rec.Policy == nil {
				continue
			}

			spec := rec.Policy.Spec

			if !g.selectorMatchesPod(spec.PodSelector, pair.DestLabel) && !g.selectorMatchesPod(spec.PodSelector, pair.SourceLabel) {
				continue
			}

			for _, ingress := range spec.Ingress {
				if g.ingressCoversPair(ingress, pair) {
					report.CoveredByPolicy[rec.Name] = append(report.CoveredByPolicy[rec.Name], pair)
					pairCovered = true
					break
				}
			}

			for _, egress := range spec.Egress {
				if g.egressCoversPair(egress, pair) {
					report.CoveredByPolicy[rec.Name] = append(report.CoveredByPolicy[rec.Name], pair)
					pairCovered = true
					break
				}
			}

			if pairCovered {
				break
			}
		}

		if pairCovered {
			covered[pairKey] = true
		}
	}

	report.CoveredPairs = len(covered)
	if report.TotalPairs > 0 {
		report.CoverageRatio = float64(report.CoveredPairs) / float64(report.TotalPairs)
	}

	for _, pair := range allPairs {
		pairKey := fmt.Sprintf("%s->%s|%s:%d", pair.Source, pair.Destination, pair.Protocol, pair.Port)
		if !covered[pairKey] {
			report.UncoveredPairs = append(report.UncoveredPairs, pair)
		}
	}

	return report
}

func (g *Generator) selectorMatchesPod(selector metav1.LabelSelector, podLabels map[string]string) bool {
	if len(selector.MatchLabels) == 0 && len(selector.MatchExpressions) == 0 {
		return true
	}

	for k, v := range selector.MatchLabels {
		if podVal, ok := podLabels[k]; !ok || podVal != v {
			return false
		}
	}

	return true
}

func (g *Generator) ingressCoversPair(ingress v1.NetworkPolicyIngressRule, pair CommPair) bool {
	if len(ingress.Ports) > 0 {
		portCovered := false
		for _, p := range ingress.Ports {
			if p.Protocol != nil && string(*p.Protocol) != pair.Protocol {
				continue
			}
			if p.Port != nil && p.Port.IntVal != pair.Port {
				continue
			}
			portCovered = true
			break
		}
		if !portCovered {
			return false
		}
	}

	if len(ingress.From) > 0 {
		fromCovered := false
		for _, peer := range ingress.From {
			if peer.PodSelector != nil && g.selectorMatchesPod(*peer.PodSelector, pair.SourceLabel) {
				fromCovered = true
				break
			}
			if peer.NamespaceSelector != nil && pair.SourceType == "external" {
				fromCovered = true
				break
			}
		}
		if !fromCovered {
			return false
		}
	}

	return true
}

func (g *Generator) egressCoversPair(egress v1.NetworkPolicyEgressRule, pair CommPair) bool {
	if len(egress.Ports) > 0 {
		portCovered := false
		for _, p := range egress.Ports {
			if p.Protocol != nil && string(*p.Protocol) != pair.Protocol {
				continue
			}
			if p.Port != nil && p.Port.IntVal != pair.Port {
				continue
			}
			portCovered = true
			break
		}
		if !portCovered {
			return false
		}
	}

	if len(egress.To) > 0 {
		toCovered := false
		for _, peer := range egress.To {
			if peer.PodSelector != nil && g.selectorMatchesPod(*peer.PodSelector, pair.DestLabel) {
				toCovered = true
				break
			}
		}
		if !toCovered {
			return false
		}
	}

	return true
}

func (g *Generator) analyzeFlows(flows []neo4jclient.FlowEdge, pods []k8s.PodInfo, services []k8s.ServiceInfo) (
	ingressMap map[string][]FlowRule,
	egressMap map[string][]FlowRule,
) {
	ingressMap = make(map[string][]FlowRule)
	egressMap = make(map[string][]FlowRule)

	podLabels := make(map[string]map[string]string)
	for _, pod := range pods {
		key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
		podLabels[key] = pod.Labels
	}

	for _, flow := range flows {
		srcKey := fmt.Sprintf("%s/%s", flow.SourceNamespace, flow.SourceName)
		dstKey := fmt.Sprintf("%s/%s", flow.DestNamespace, flow.DestName)

		srcSelector := podLabels[srcKey]
		dstSelector := podLabels[dstKey]

		rule := FlowRule{
			Protocol: flow.Protocol,
			Port:     flow.Port,
			Count:    flow.Count,
		}

		if srcSelector != nil {
			rule.SourceSelector = srcSelector
		}
		if dstSelector != nil {
			rule.DestSelector = dstSelector
		}

		ingressMap[dstKey] = append(ingressMap[dstKey], rule)
		egressMap[srcKey] = append(egressMap[srcKey], rule)
	}

	return ingressMap, egressMap
}

type FlowRule struct {
	SourceSelector map[string]string
	DestSelector   map[string]string
	Protocol       string
	Port           int32
	Count          int64
}

func (g *Generator) generateDefaultDenyPolicy(namespace string) PolicyRecommendation {
	policyType := v1.PolicyTypeIngress
	egressType := v1.PolicyTypeEgress

	policy := &v1.NetworkPolicy{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "default-deny-all",
			Namespace: namespace,
			Labels: map[string]string{
				"generated-by": "network-policy-recommender",
				"policy-type":  "default-deny",
			},
		},
		Spec: v1.NetworkPolicySpec{
			PodSelector: metav1.LabelSelector{},
			PolicyTypes: []v1.PolicyType{policyType, egressType},
		},
	}

	return PolicyRecommendation{
		Name:        "default-deny-all",
		Namespace:   namespace,
		Description: "Default deny all ingress and egress traffic - least privilege baseline",
		Policy:      policy,
		Reasoning:   []string{"Enable zero-trust networking by default", "Explicitly allow only required traffic"},
		Confidence:  0.95,
	}
}

func (g *Generator) generateServicePolicies(namespace string, services []k8s.ServiceInfo,
	ingressMap, egressMap map[string][]FlowRule) []PolicyRecommendation {
	var recommendations []PolicyRecommendation

	for _, svc := range services {
		if len(svc.Selector) == 0 {
			continue
		}

		var ingressRules []v1.NetworkPolicyIngressRule
		var reasoning []string
		var coveredPairs []CommPair

		svcKey := fmt.Sprintf("%s/%s", svc.Namespace, svc.Name)
		if rules, ok := ingressMap[svcKey]; ok {
			uniqueSelectors := make(map[string]map[string]string)
			uniquePorts := make(map[string]struct{})

			for _, rule := range rules {
				if rule.SourceSelector != nil {
					selectorKey := fmt.Sprintf("%v", rule.SourceSelector)
					uniqueSelectors[selectorKey] = rule.SourceSelector
				}
				portKey := fmt.Sprintf("%s/%d", rule.Protocol, rule.Port)
				uniquePorts[portKey] = struct{}{}
			}

			var peers []v1.NetworkPolicyPeer
			for _, sel := range uniqueSelectors {
				peers = append(peers, v1.NetworkPolicyPeer{
					PodSelector: &metav1.LabelSelector{
						MatchLabels: sel,
					},
				})
			}

			var ports []v1.NetworkPolicyPort
			for portKey := range uniquePorts {
				var proto string
				var port int32
				fmt.Sscanf(portKey, "%s/%d", &proto, &port)
				protoType := v1.Protocol(proto)
				ports = append(ports, v1.NetworkPolicyPort{
					Protocol: &protoType,
					Port:     &metav1.IntOrString{Type: metav1.IntOrStringInt, IntVal: port},
				})
			}

			sort.Slice(ports, func(i, j int) bool {
				return ports[i].Port.IntVal < ports[j].Port.IntVal
			})

			if len(peers) > 0 || len(ports) > 0 {
				ingressRules = append(ingressRules, v1.NetworkPolicyIngressRule{
					From:  peers,
					Ports: ports,
				})
				reasoning = append(reasoning, fmt.Sprintf("Allow traffic to service %s on observed ports", svc.Name))

				for _, rule := range rules {
					if rule.SourceSelector != nil {
						for _, sel := range uniqueSelectors {
							coveredPairs = append(coveredPairs, CommPair{
								Source:      fmt.Sprintf("pod(labels=%v)", sel),
								Destination: fmt.Sprintf("svc/%s", svc.Name),
								Protocol:    rule.Protocol,
								Port:        rule.Port,
								DestLabel:   svc.Selector,
								SourceLabel: sel,
							})
						}
					}
				}
			}
		}

		if len(ingressRules) > 0 {
			policy := &v1.NetworkPolicy{
				ObjectMeta: metav1.ObjectMeta{
					Name:      fmt.Sprintf("allow-%s-ingress", svc.Name),
					Namespace: namespace,
					Labels: map[string]string{
						"generated-by": "network-policy-recommender",
						"policy-type":  "service-ingress",
						"service":      svc.Name,
					},
				},
				Spec: v1.NetworkPolicySpec{
					PodSelector: metav1.LabelSelector{
						MatchLabels: svc.Selector,
					},
					Ingress:     ingressRules,
					PolicyTypes: []v1.PolicyType{v1.PolicyTypeIngress},
				},
			}

			recommendations = append(recommendations, PolicyRecommendation{
				Name:         fmt.Sprintf("allow-%s-ingress", svc.Name),
				Namespace:    namespace,
				Description:  fmt.Sprintf("Allow ingress traffic to %s service", svc.Name),
				Policy:       policy,
				Reasoning:    reasoning,
				Confidence:   0.85,
				CoveredPairs: coveredPairs,
			})
		}
	}

	return recommendations
}

func (g *Generator) generatePodPairPolicies(namespace string, pods []k8s.PodInfo, ingressMap map[string][]FlowRule) []PolicyRecommendation {
	grouped := make(map[string][]FlowRule)

	for dstKey, rules := range ingressMap {
		for _, rule := range rules {
			if rule.SourceSelector == nil {
				continue
			}
			srcGroupKey := fmt.Sprintf("%v", rule.SourceSelector)
			dstGroupKey := fmt.Sprintf("%v", rule.DestSelector)
			comboKey := srcGroupKey + "->" + dstGroupKey
			grouped[comboKey] = append(grouped[comboKey], rule)
		}
	}

	var recommendations []PolicyRecommendation
	idx := 0
	for comboKey, rules := range grouped {
		if len(rules) == 0 {
			continue
		}

		srcSelector := rules[0].SourceSelector
		dstSelector := rules[0].DestSelector
		if srcSelector == nil || dstSelector == nil {
			continue
		}

		uniquePorts := make(map[string]struct{})
		for _, r := range rules {
			portKey := fmt.Sprintf("%s/%d", r.Protocol, r.Port)
			uniquePorts[portKey] = struct{}{}
		}

		var ports []v1.NetworkPolicyPort
		for portKey := range uniquePorts {
			var proto string
			var port int32
			fmt.Sscanf(portKey, "%s/%d", &proto, &port)
			protoType := v1.Protocol(proto)
			ports = append(ports, v1.NetworkPolicyPort{
				Protocol: &protoType,
				Port:     &metav1.IntOrString{Type: metav1.IntOrStringInt, IntVal: port},
			})
		}

		sort.Slice(ports, func(i, j int) bool {
			return ports[i].Port.IntVal < ports[j].Port.IntVal
		})

		var coveredPairs []CommPair
		for _, r := range rules {
			coveredPairs = append(coveredPairs, CommPair{
				Source:      fmt.Sprintf("pod(labels=%v)", srcSelector),
				Destination: fmt.Sprintf("pod(labels=%v)", dstSelector),
				Protocol:    r.Protocol,
				Port:        r.Port,
				SourceLabel: srcSelector,
				DestLabel:   dstSelector,
			})
		}

		policyName := fmt.Sprintf("allow-podpair-%d", idx)
		policy := &v1.NetworkPolicy{
			ObjectMeta: metav1.ObjectMeta{
				Name:      policyName,
				Namespace: namespace,
				Labels: map[string]string{
					"generated-by": "network-policy-recommender",
					"policy-type":  "pod-pair-ingress",
				},
			},
			Spec: v1.NetworkPolicySpec{
				PodSelector: metav1.LabelSelector{
					MatchLabels: dstSelector,
				},
				Ingress: []v1.NetworkPolicyIngressRule{
					{
						From: []v1.NetworkPolicyPeer{
							{
								PodSelector: &metav1.LabelSelector{
									MatchLabels: srcSelector,
								},
							},
						},
						Ports: ports,
					},
				},
				PolicyTypes: []v1.PolicyType{v1.PolicyTypeIngress},
			},
		}

		recommendations = append(recommendations, PolicyRecommendation{
			Name:         policyName,
			Namespace:    namespace,
			Description:  fmt.Sprintf("Allow ingress from %v to %v", srcSelector, dstSelector),
			Policy:       policy,
			Reasoning:    []string{fmt.Sprintf("Observed traffic from pods matching %v to pods matching %v", srcSelector, dstSelector)},
			Confidence:   0.80,
			CoveredPairs: coveredPairs,
		})

		idx++
	}

	return recommendations
}

func (g *Generator) generateCrossNamespacePolicies(namespace string, flows []neo4jclient.FlowEdge, pods []k8s.PodInfo) []PolicyRecommendation {
	crossNsFlows := make(map[string][]neo4jclient.FlowEdge)
	for _, flow := range flows {
		if flow.SourceNamespace != namespace && flow.DestNamespace == namespace {
			key := flow.SourceNamespace
			crossNsFlows[key] = append(crossNsFlows[key], flow)
		}
	}

	var recommendations []PolicyRecommendation
	for srcNs, nsFlows := range crossNsFlows {
		uniquePorts := make(map[string]struct{})
		var coveredPairs []CommPair

		dstLabels := make(map[string]string)
		for _, pod := range pods {
			for _, flow := range nsFlows {
				if pod.Name == flow.DestName {
					for k, v := range pod.Labels {
						dstLabels[k] = v
						break
					}
				}
			}
			if len(dstLabels) > 0 {
				break
			}
		}

		for _, flow := range nsFlows {
			portKey := fmt.Sprintf("%s/%d", flow.Protocol, flow.Port)
			uniquePorts[portKey] = struct{}{}
			coveredPairs = append(coveredPairs, CommPair{
				Source:     fmt.Sprintf("%s/*", srcNs),
				Destination: fmt.Sprintf("%s/%s", flow.DestNamespace, flow.DestName),
				Protocol:   flow.Protocol,
				Port:       flow.Port,
				SourceType: "external",
			})
		}

		var ports []v1.NetworkPolicyPort
		for portKey := range uniquePorts {
			var proto string
			var port int32
			fmt.Sscanf(portKey, "%s/%d", &proto, &port)
			protoType := v1.Protocol(proto)
			ports = append(ports, v1.NetworkPolicyPort{
				Protocol: &protoType,
				Port:     &metav1.IntOrString{Type: metav1.IntOrStringInt, IntVal: port},
			})
		}

		sort.Slice(ports, func(i, j int) bool {
			return ports[i].Port.IntVal < ports[j].Port.IntVal
		})

		policyName := fmt.Sprintf("allow-crossns-%s-to-%s", srcNs, namespace)
		policy := &v1.NetworkPolicy{
			ObjectMeta: metav1.ObjectMeta{
				Name:      policyName,
				Namespace: namespace,
				Labels: map[string]string{
					"generated-by": "network-policy-recommender",
					"policy-type":  "cross-namespace-ingress",
					"source-ns":    srcNs,
				},
			},
			Spec: v1.NetworkPolicySpec{
				PodSelector: metav1.LabelSelector{
					MatchLabels: dstLabels,
				},
				Ingress: []v1.NetworkPolicyIngressRule{
					{
						From: []v1.NetworkPolicyPeer{
							{
								NamespaceSelector: &metav1.LabelSelector{
									MatchLabels: map[string]string{
										"kubernetes.io/metadata.name": srcNs,
									},
								},
							},
						},
						Ports: ports,
					},
				},
				PolicyTypes: []v1.PolicyType{v1.PolicyTypeIngress},
			},
		}

		recommendations = append(recommendations, PolicyRecommendation{
			Name:         policyName,
			Namespace:    namespace,
			Description:  fmt.Sprintf("Allow cross-namespace ingress from %s to %s", srcNs, namespace),
			Policy:       policy,
			Reasoning:    []string{fmt.Sprintf("Observed traffic from namespace %s to %s", srcNs, namespace)},
			Confidence:   0.70,
			CoveredPairs: coveredPairs,
		})
	}

	return recommendations
}

func (g *Generator) generateDNSPolicy(namespace string) PolicyRecommendation {
	protocol := v1.ProtocolUDP
	port53 := int32(53)

	policy := &v1.NetworkPolicy{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "allow-dns-egress",
			Namespace: namespace,
			Labels: map[string]string{
				"generated-by": "network-policy-recommender",
				"policy-type":  "dns-egress",
			},
		},
		Spec: v1.NetworkPolicySpec{
			PodSelector: metav1.LabelSelector{},
			Egress: []v1.NetworkPolicyEgressRule{
				{
					Ports: []v1.NetworkPolicyPort{
						{
							Protocol: &protocol,
							Port:     &metav1.IntOrString{Type: metav1.IntOrStringInt, IntVal: port53},
						},
					},
					To: []v1.NetworkPolicyPeer{
						{
							NamespaceSelector: &metav1.LabelSelector{
								MatchLabels: map[string]string{
									"kubernetes.io/metadata.name": "kube-system",
								},
							},
						},
					},
				},
			},
			PolicyTypes: []v1.PolicyType{v1.PolicyTypeEgress},
		},
	}

	return PolicyRecommendation{
		Name:        "allow-dns-egress",
		Namespace:   namespace,
		Description: "Allow DNS egress traffic for name resolution",
		Policy:      policy,
		Reasoning:   []string{"DNS is required for service discovery in Kubernetes"},
		Confidence:  0.9,
	}
}
