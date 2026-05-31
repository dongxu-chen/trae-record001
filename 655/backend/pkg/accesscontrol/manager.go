package accesscontrol

import (
	"context"
	"fmt"
	"net"
	"sync"
	"time"

	"github.com/google/uuid"

	"servicemesh-gateway/pkg/istio"
	"servicemesh-gateway/pkg/models"
	redisclient "servicemesh-gateway/pkg/redis"
)

type AccessControlManager struct {
	istioClient  *istio.Client
	trafficStore *redisclient.TrafficStore
	rules        map[string]*models.AccessControlRule
	mu           sync.RWMutex
}

func NewAccessControlManager(istioClient *istio.Client, trafficStore *redisclient.TrafficStore) *AccessControlManager {
	return &AccessControlManager{
		istioClient:  istioClient,
		trafficStore: trafficStore,
		rules:        make(map[string]*models.AccessControlRule),
	}
}

func (acm *AccessControlManager) CreateRule(rule *models.AccessControlRule) (*models.AccessControlRule, error) {
	rule.ID = uuid.New().String()
	rule.CreatedAt = time.Now()
	rule.UpdatedAt = time.Now()
	if rule.Status == "" {
		rule.Status = "active"
	}

	if err := acm.validateRule(rule); err != nil {
		return nil, err
	}

	acm.mu.Lock()
	acm.rules[rule.ID] = rule
	acm.mu.Unlock()

	if rule.Status == "active" {
		if err := acm.applyRuleToIstio(rule); err != nil {
			return nil, fmt.Errorf("failed to apply rule to istio: %w", err)
		}
	}

	acm.trafficStore.HSet("accesscontrol:rules", rule.ID, rule)

	return rule, nil
}

func (acm *AccessControlManager) validateRule(rule *models.AccessControlRule) error {
	if rule.RuleType != "ip" && rule.RuleType != "user" && rule.RuleType != "header" {
		return fmt.Errorf("invalid rule type: %s (must be ip, user, or header)", rule.RuleType)
	}

	if rule.ControlType != "allow" && rule.ControlType != "deny" {
		return fmt.Errorf("invalid control type: %s (must be allow or deny)", rule.ControlType)
	}

	if rule.ListType != "whitelist" && rule.ListType != "blacklist" {
		return fmt.Errorf("invalid list type: %s (must be whitelist or blacklist)", rule.ListType)
	}

	switch rule.RuleType {
	case "ip":
		for _, ip := range rule.IPList {
			if _, _, err := net.ParseCIDR(ip); err != nil {
				if net.ParseIP(ip) == nil {
					return fmt.Errorf("invalid IP address or CIDR: %s", ip)
				}
			}
		}
	case "user":
		if len(rule.UserIDList) == 0 {
			return fmt.Errorf("user id list cannot be empty for user rule type")
		}
	case "header":
		if rule.HeaderName == "" {
			return fmt.Errorf("header name cannot be empty for header rule type")
		}
	}

	return nil
}

func (acm *AccessControlManager) applyRuleToIstio(rule *models.AccessControlRule) error {
	vs, err := acm.istioClient.GetVirtualService(rule.Namespace, rule.ServiceName)
	if err != nil {
		vs = &models.VirtualService{
			Metadata: models.Metadata{
				Name:      rule.ServiceName,
				Namespace: rule.Namespace,
			},
			Spec: models.VSSpec{
				Hosts: []string{rule.ServiceName},
				HTTP:  []models.HTTPRoute{},
			},
		}
	}

	match := models.HTTPMatch{}

	switch rule.RuleType {
	case "ip":
		headers := make(map[string]models.StringMatch)
		for _, ip := range rule.IPList {
			headers["x-forwarded-for"] = models.StringMatch{
				Regex: ip,
			}
		}
		match.Headers = headers

	case "user":
		headers := make(map[string]models.StringMatch)
		for _, userID := range rule.UserIDList {
			headers["x-user-id"] = models.StringMatch{
				Exact: userID,
			}
		}
		match.Headers = headers

	case "header":
		headers := make(map[string]models.StringMatch)
		for _, value := range rule.HeaderValues {
			headers[rule.HeaderName] = models.StringMatch{
				Exact: value,
			}
		}
		match.Headers = headers
	}

	var route *models.HTTPRoute
	if rule.ControlType == "allow" && rule.ListType == "whitelist" {
		route = &models.HTTPRoute{
			Match: []models.HTTPMatch{match},
			Route: []models.Destination{
				{Host: rule.ServiceName},
			},
		}
	} else if rule.ControlType == "deny" && rule.ListType == "blacklist" {
		route = &models.HTTPRoute{
			Match: []models.HTTPMatch{match},
			Fault: &models.HTTPFaultInjection{
				Abort: &models.AbortFault{
					HTTPStatus: 403,
					Percentage: 100,
				},
			},
		}
	}

	if route != nil {
		routes := []models.HTTPRoute{*route}
		routes = append(routes, vs.Spec.HTTP...)
		vs.Spec.HTTP = routes

		return acm.istioClient.CreateOrUpdateVirtualService(rule.Namespace, vs)
	}

	return nil
}

func (acm *AccessControlManager) UpdateRule(id string, updates *models.AccessControlRule) (*models.AccessControlRule, error) {
	acm.mu.Lock()
	defer acm.mu.Unlock()

	rule, exists := acm.rules[id]
	if !exists {
		return nil, fmt.Errorf("rule %s not found", id)
	}

	if updates.Name != "" {
		rule.Name = updates.Name
	}
	if updates.Description != "" {
		rule.Description = updates.Description
	}
	if updates.Status != "" {
		rule.Status = updates.Status
	}
	if len(updates.IPList) > 0 {
		rule.IPList = updates.IPList
	}
	if len(updates.UserIDList) > 0 {
		rule.UserIDList = updates.UserIDList
	}
	if len(updates.HeaderValues) > 0 {
		rule.HeaderValues = updates.HeaderValues
	}
	rule.UpdatedAt = time.Now()

	acm.rules[id] = rule
	acm.trafficStore.HSet("accesscontrol:rules", id, rule)

	if rule.Status == "active" {
		if err := acm.applyRuleToIstio(rule); err != nil {
			return nil, err
		}
	}

	return rule, nil
}

func (acm *AccessControlManager) DeleteRule(id string) error {
	acm.mu.Lock()
	defer acm.mu.Unlock()

	rule, exists := acm.rules[id]
	if !exists {
		return fmt.Errorf("rule %s not found", id)
	}

	delete(acm.rules, id)
	acm.trafficStore.HDel("accesscontrol:rules", id)

	return nil
}

func (acm *AccessControlManager) GetRule(id string) (*models.AccessControlRule, bool) {
	acm.mu.RLock()
	defer acm.mu.RUnlock()

	rule, exists := acm.rules[id]
	return rule, exists
}

func (acm *AccessControlManager) ListRules(namespace string, serviceName string) []*models.AccessControlRule {
	acm.mu.RLock()
	defer acm.mu.RUnlock()

	result := make([]*models.AccessControlRule, 0)
	for _, rule := range acm.rules {
		if namespace != "" && rule.Namespace != namespace {
			continue
		}
		if serviceName != "" && rule.ServiceName != serviceName {
			continue
		}
		result = append(result, rule)
	}

	return result
}

func (acm *AccessControlManager) CheckAccess(ctx context.Context, ruleID string, sourceIP string, userID string, headers map[string]string) (bool, string, error) {
	acm.mu.RLock()
	rule, exists := acm.rules[ruleID]
	acm.mu.RUnlock()

	if !exists {
		return true, "rule not found, access allowed by default", nil
	}

	if rule.Status != "active" {
		return true, "rule is inactive, access allowed", nil
	}

	var match bool
	switch rule.RuleType {
	case "ip":
		match = acm.checkIPMatch(sourceIP, rule.IPList)
	case "user":
		match = acm.checkUserIDMatch(userID, rule.UserIDList)
	case "header":
		match = acm.checkHeaderMatch(headers, rule.HeaderName, rule.HeaderValues)
	}

	if rule.ListType == "whitelist" {
		if match {
			return true, "matched whitelist, access allowed", nil
		}
		return false, "not in whitelist, access denied", nil
	} else {
		if match {
			return false, "matched blacklist, access denied", nil
		}
		return true, "not in blacklist, access allowed", nil
	}
}

func (acm *AccessControlManager) checkIPMatch(sourceIP string, ipList []string) bool {
	parsedIP := net.ParseIP(sourceIP)
	if parsedIP == nil {
		return false
	}

	for _, ipOrCIDR := range ipList {
		if _, cidr, err := net.ParseCIDR(ipOrCIDR); err == nil {
			if cidr.Contains(parsedIP) {
				return true
			}
		} else {
			if net.ParseIP(ipOrCIDR) != nil && net.ParseIP(ipOrCIDR).Equal(parsedIP) {
				return true
			}
		}
	}

	return false
}

func (acm *AccessControlManager) checkUserIDMatch(userID string, userIDList []string) bool {
	for _, id := range userIDList {
		if id == userID {
			return true
		}
	}
	return false
}

func (acm *AccessControlManager) checkHeaderMatch(headers map[string]string, headerName string, values []string) bool {
	headerValue := headers[headerName]
	for _, v := range values {
		if v == headerValue {
			return true
		}
	}
	return false
}
