package compliance

import (
	"authz-policy-recommender/backend/pkg/models"
	"strings"
)

type ScenarioChecker struct {
	templates []models.ComplianceScenarioTemplate
}

func NewScenarioChecker() *ScenarioChecker {
	return &ScenarioChecker{
		templates: GetDefaultScenarios(),
	}
}

func GetDefaultScenarios() []models.ComplianceScenarioTemplate {
	return []models.ComplianceScenarioTemplate{
		{
			ID:          "SCENARIO-001",
			Name:        "数据库访问限制",
			Category:    models.ScenarioDatabaseAccess,
			Description: "数据库服务只允许后端服务访问，禁止前端直接访问",
			Severity:    "CRITICAL",
			Conditions: []models.TemplateCondition{
				{Type: "service_name", Field: "destination", Operator: "contains", Value: "database"},
				{Type: "service_name", Field: "destination", Operator: "suffix", Value: "-db"},
			},
			ExpectedRules: []models.Rule{
				{From: "product-service", To: "database", Methods: []string{"QUERY", "EXEC"}, Paths: []string{"/db/query", "/db/exec"}},
				{From: "order-service", To: "database", Methods: []string{"QUERY", "EXEC"}, Paths: []string{"/db/query", "/db/exec"}},
				{From: "user-service", To: "database", Methods: []string{"QUERY", "EXEC"}, Paths: []string{"/db/query", "/db/exec"}},
			},
			Examples: []models.ScenarioExample{
				{Name: "正确配置", Description: "仅product/order/user服务可访问数据库", Valid: true, Config: "ALLOW product-service,order-service,user-service -> database"},
				{Name: "错误配置", Description: "frontend直接访问数据库", Valid: false, Config: "ALLOW frontend -> database"},
			},
		},
		{
			ID:          "SCENARIO-002",
			Name:        "支付服务访问控制",
			Category:    models.ScenarioSensitiveData,
			Description: "支付服务仅允许订单服务访问，其他服务禁止直接调用",
			Severity:    "CRITICAL",
			Conditions: []models.TemplateCondition{
				{Type: "service_name", Field: "destination", Operator: "equals", Value: "payment-service"},
			},
			ExpectedRules: []models.Rule{
				{From: "order-service", To: "payment-service", Methods: []string{"POST"}, Paths: []string{"/payments", "/payments/*"}},
			},
			Examples: []models.ScenarioExample{
				{Name: "正确配置", Description: "仅order-service可调用支付接口", Valid: true, Config: "ALLOW order-service -> payment-service POST /payments"},
				{Name: "错误配置", Description: "任意服务均可调用支付接口", Valid: false, Config: "ALLOW * -> payment-service"},
			},
		},
		{
			ID:          "SCENARIO-003",
			Name:        "管理员接口保护",
			Category:    models.ScenarioAdminAccess,
			Description: "/admin路径的接口需要严格的来源限制，避免权限提升",
			Severity:    "HIGH",
			Conditions: []models.TemplateCondition{
				{Type: "path_prefix", Field: "path", Operator: "prefix", Value: "/admin"},
			},
			ExpectedRules: []models.Rule{
				{From: "admin-service", To: "*", Methods: []string{"*"}, Paths: []string{"/admin/*"}},
			},
			Examples: []models.ScenarioExample{
				{Name: "正确配置", Description: "仅admin-service可访问管理员接口", Valid: true, Config: "ALLOW admin-service -> * /admin/*"},
				{Name: "错误配置", Description: "所有服务均可访问管理员接口", Valid: false, Config: "ALLOW * -> * /admin/*"},
			},
		},
		{
			ID:          "SCENARIO-004",
			Name:        "外部API网关限制",
			Category:    models.ScenarioExternalAPI,
			Description: "调用外部API的服务需要限制，避免数据泄露",
			Severity:    "HIGH",
			Conditions: []models.TemplateCondition{
				{Type: "service_name", Field: "destination", Operator: "prefix", Value: "external-"},
				{Type: "service_name", Field: "destination", Operator: "suffix", Value: "-external"},
			},
			ExpectedRules: []models.Rule{
				{From: "payment-service", To: "external-payment-gateway", Methods: []string{"POST"}, Paths: []string{"/charge", "/refund"}},
			},
			Examples: []models.ScenarioExample{
				{Name: "正确配置", Description: "仅特定服务可调用外部API", Valid: true, Config: "ALLOW payment-service -> external-payment-gateway"},
				{Name: "错误配置", Description: "所有服务均可调用外部API", Valid: false, Config: "ALLOW * -> external-*"},
			},
		},
		{
			ID:          "SCENARIO-005",
			Name:        "公开API只读限制",
			Category:    models.ScenarioPublicAPI,
			Description: "公开API应该只允许GET方法，禁止写操作",
			Severity:    "MEDIUM",
			Conditions: []models.TemplateCondition{
				{Type: "path_prefix", Field: "path", Operator: "prefix", Value: "/public"},
			},
			ExpectedRules: []models.Rule{
				{From: "*", To: "*", Methods: []string{"GET", "HEAD"}, Paths: []string{"/public/*"}},
			},
			Examples: []models.ScenarioExample{
				{Name: "正确配置", Description: "公开接口仅允许GET/HEAD", Valid: true, Config: "ALLOW * GET,HEAD /public/*"},
				{Name: "错误配置", Description: "公开接口允许POST/PUT/DELETE", Valid: false, Config: "ALLOW * * /public/*"},
			},
		},
		{
			ID:          "SCENARIO-006",
			Name:        "用户数据隔离",
			Category:    models.ScenarioSensitiveData,
			Description: "用户服务不允许被除frontend和api-gateway外的服务直接调用",
			Severity:    "HIGH",
			Conditions: []models.TemplateCondition{
				{Type: "service_name", Field: "destination", Operator: "equals", Value: "user-service"},
			},
			ExpectedRules: []models.Rule{
				{From: "frontend", To: "user-service", Methods: []string{"GET", "PUT"}, Paths: []string{"/users/*"}},
				{From: "api-gateway", To: "user-service", Methods: []string{"GET", "PUT"}, Paths: []string{"/users/*"}},
			},
			Examples: []models.ScenarioExample{
				{Name: "正确配置", Description: "仅frontend可访问用户数据", Valid: true, Config: "ALLOW frontend -> user-service"},
				{Name: "错误配置", Description: "所有服务均可访问用户数据", Valid: false, Config: "ALLOW * -> user-service"},
			},
		},
		{
			ID:          "SCENARIO-007",
			Name:        "消息队列访问控制",
			Category:    models.ScenarioMQCommunication,
			Description: "消息队列服务需要严格控制生产者和消费者",
			Severity:    "MEDIUM",
			Conditions: []models.TemplateCondition{
				{Type: "service_name", Field: "destination", Operator: "contains", Value: "mq"},
				{Type: "service_name", Field: "destination", Operator: "contains", Value: "kafka"},
				{Type: "service_name", Field: "destination", Operator: "contains", Value: "rabbit"},
			},
			ExpectedRules: []models.Rule{
				{From: "order-service", To: "mq-service", Methods: []string{"PRODUCE", "CONSUME"}, Paths: []string{"/orders"}},
				{From: "payment-service", To: "mq-service", Methods: []string{"CONSUME"}, Paths: []string{"/orders"}},
			},
			Examples: []models.ScenarioExample{
				{Name: "正确配置", Description: "指定服务的生产者/消费者权限", Valid: true, Config: "ALLOW order-service PRODUCE, payment-service CONSUME -> mq-service /orders"},
			},
		},
		{
			ID:          "SCENARIO-008",
			Name:        "缓存服务访问限制",
			Category:    models.ScenarioCacheAccess,
			Description: "缓存服务应该只允许业务服务访问，避免缓存污染",
			Severity:    "MEDIUM",
			Conditions: []models.TemplateCondition{
				{Type: "service_name", Field: "destination", Operator: "contains", Value: "redis"},
				{Type: "service_name", Field: "destination", Operator: "contains", Value: "cache"},
			},
			ExpectedRules: []models.Rule{
				{From: "product-service", To: "redis-cache", Methods: []string{"GET", "SET", "DEL"}, Paths: []string{"/products/*"}},
				{From: "user-service", To: "redis-cache", Methods: []string{"GET", "SET", "DEL"}, Paths: []string{"/users/*"}},
			},
			Examples: []models.ScenarioExample{
				{Name: "正确配置", Description: "仅业务服务可访问缓存", Valid: true, Config: "ALLOW product-service,user-service -> redis-cache"},
				{Name: "错误配置", Description: "任意服务可操作缓存", Valid: false, Config: "ALLOW * -> redis-cache"},
			},
		},
		{
			ID:          "SCENARIO-009",
			Name:        "服务间单向调用",
			Category:    models.ScenarioServiceToService,
			Description: "避免服务间循环依赖，确保单向调用",
			Severity:    "MEDIUM",
			Conditions: []models.TemplateCondition{
				{Type: "circular_dependency", Field: "graph", Operator: "detect", Value: "true"},
			},
			ExpectedRules: []models.Rule{},
			Examples: []models.ScenarioExample{
				{Name: "正确配置", Description: "无循环依赖的服务调用", Valid: true, Config: "A->B->C, 无反向调用"},
				{Name: "错误配置", Description: "存在循环依赖", Valid: false, Config: "A->B, B->A"},
			},
		},
		{
			ID:          "SCENARIO-010",
			Name:        "敏感数据接口保护",
			Category:    models.ScenarioSensitiveData,
			Description: "/api/v*/payment、/api/v*/credit路径需要额外的访问控制",
			Severity:    "CRITICAL",
			Conditions: []models.TemplateCondition{
				{Type: "path_pattern", Field: "path", Operator: "regex", Value: ".*/payment.*"},
				{Type: "path_pattern", Field: "path", Operator: "regex", Value: ".*/credit.*"},
				{Type: "path_pattern", Field: "path", Operator: "regex", Value: ".*/card.*"},
			},
			ExpectedRules: []models.Rule{
				{From: "payment-service", To: "*", Methods: []string{"POST"}, Paths: []string{"*/payment*", "*/credit*", "*/card*"}},
			},
			Examples: []models.ScenarioExample{
				{Name: "正确配置", Description: "敏感路径限制特定服务访问", Valid: true, Config: "ALLOW payment-service POST */payment*"},
				{Name: "错误配置", Description: "敏感路径无访问限制", Valid: false, Config: "ALLOW * * */payment*"},
			},
		},
	}
}

func (sc *ScenarioChecker) GetAllScenarios() []models.ComplianceScenarioTemplate {
	return sc.templates
}

func (sc *ScenarioChecker) GetScenarioByID(id string) *models.ComplianceScenarioTemplate {
	for _, t := range sc.templates {
		if t.ID == id {
			return &t
		}
	}
	return nil
}

func (sc *ScenarioChecker) GetScenariosByCategory(category models.ScenarioCategory) []models.ComplianceScenarioTemplate {
	result := make([]models.ComplianceScenarioTemplate, 0)
	for _, t := range sc.templates {
		if t.Category == category {
			result = append(result, t)
		}
	}
	return result
}

func (sc *ScenarioChecker) CheckSemanticCompliance(req models.SemanticComplianceRequest) models.SemanticComplianceReport {
	scenariosToCheck := sc.templates
	if len(req.Scenarios) > 0 {
		scenariosToCheck = make([]models.ComplianceScenarioTemplate, 0)
		for _, id := range req.Scenarios {
			if t := sc.GetScenarioByID(id); t != nil {
				scenariosToCheck = append(scenariosToCheck, *t)
			}
		}
	}

	results := make([]models.SemanticComplianceResult, 0, len(scenariosToCheck))
	passedCount := 0

	for _, scenario := range scenariosToCheck {
		result := sc.checkScenario(scenario, req.Policies, req.Graph)
		results = append(results, result)
		if result.Passed {
			passedCount++
		}
	}

	score := 0
	if len(scenariosToCheck) > 0 {
		score = (passedCount * 100) / len(scenariosToCheck)
	}

	return models.SemanticComplianceReport{
		TotalScenarios:  len(scenariosToCheck),
		PassedScenarios: passedCount,
		FailedScenarios: len(scenariosToCheck) - passedCount,
		OverallScore:    score,
		Results:         results,
	}
}

func (sc *ScenarioChecker) checkScenario(scenario models.ComplianceScenarioTemplate, policies []models.AuthorizationPolicy, graph *models.ServiceGraph) models.SemanticComplianceResult {
	result := models.SemanticComplianceResult{
		ScenarioID:      scenario.ID,
		ScenarioName:    scenario.Name,
		Category:        scenario.Category,
		Severity:        scenario.Severity,
		Passed:          true,
		MissingRules:    make([]models.Rule, 0),
		Recommendations: make([]string, 0),
		AffectedServices: make([]string, 0),
	}

	switch scenario.ID {
	case "SCENARIO-001":
		sc.checkDatabaseAccess(scenario, policies, &result)
	case "SCENARIO-002":
		sc.checkPaymentService(scenario, policies, &result)
	case "SCENARIO-003":
		sc.checkAdminEndpoints(scenario, policies, &result)
	case "SCENARIO-004":
		sc.checkExternalAPI(scenario, policies, &result)
	case "SCENARIO-005":
		sc.checkPublicAPI(scenario, policies, &result)
	case "SCENARIO-006":
		sc.checkUserData(scenario, policies, &result)
	case "SCENARIO-007":
		sc.checkMQAccess(scenario, policies, &result)
	case "SCENARIO-008":
		sc.checkCacheAccess(scenario, policies, &result)
	case "SCENARIO-009":
		sc.checkCircularDependency(scenario, graph, &result)
	case "SCENARIO-010":
		sc.checkSensitivePaths(scenario, policies, &result)
	default:
		result.Details = "未实现的检查场景"
	}

	return result
}

func (sc *ScenarioChecker) checkDatabaseAccess(scenario models.ComplianceScenarioTemplate, policies []models.AuthorizationPolicy, result *models.SemanticComplianceResult) {
	for _, policy := range policies {
		if policy.Action != "ALLOW" {
			continue
		}
		for _, rule := range policy.Rules {
			if strings.Contains(rule.To, "database") || strings.HasSuffix(rule.To, "-db") {
				if rule.From == "*" || rule.From == "frontend" {
					result.Passed = false
					result.Details = "检测到frontend或通配符源可以直接访问数据库"
					result.AffectedServices = append(result.AffectedServices, rule.To)
					result.Recommendations = append(result.Recommendations, "移除frontend对数据库的直接访问权限")
					result.Recommendations = append(result.Recommendations, "将通配符源替换为具体的后端服务名称")
				}
			}
		}
	}

	if result.Passed {
		result.Details = "数据库访问控制符合安全要求"
	}
}

func (sc *ScenarioChecker) checkPaymentService(scenario models.ComplianceScenarioTemplate, policies []models.AuthorizationPolicy, result *models.SemanticComplianceResult) {
	for _, policy := range policies {
		if policy.Action != "ALLOW" {
			continue
		}
		for _, rule := range policy.Rules {
			if rule.To == "payment-service" {
				if rule.From == "*" || (rule.From != "order-service" && rule.From != "payment-service") {
					result.Passed = false
					result.Details = "支付服务的访问源限制不符合要求"
					result.AffectedServices = append(result.AffectedServices, "payment-service")
					result.Recommendations = append(result.Recommendations, "仅允许order-service访问payment-service")
				}
			}
		}
	}

	if result.Passed {
		result.Details = "支付服务访问控制符合安全要求"
	}
}

func (sc *ScenarioChecker) checkAdminEndpoints(scenario models.ComplianceScenarioTemplate, policies []models.AuthorizationPolicy, result *models.SemanticComplianceResult) {
	for _, policy := range policies {
		if policy.Action != "ALLOW" {
			continue
		}
		for _, rule := range policy.Rules {
			for _, path := range rule.Paths {
				if strings.HasPrefix(path, "/admin") {
					if rule.From == "*" || rule.From != "admin-service" {
						result.Passed = false
						result.Details = "管理员接口的访问源限制不符合要求"
						result.AffectedServices = append(result.AffectedServices, rule.To)
						result.Recommendations = append(result.Recommendations, "管理员接口仅允许admin-service访问")
					}
				}
			}
		}
	}

	if result.Passed {
		result.Details = "管理员接口访问控制符合安全要求"
	}
}

func (sc *ScenarioChecker) checkExternalAPI(scenario models.ComplianceScenarioTemplate, policies []models.AuthorizationPolicy, result *models.SemanticComplianceResult) {
	for _, policy := range policies {
		if policy.Action != "ALLOW" {
			continue
		}
		for _, rule := range policy.Rules {
			if strings.HasPrefix(rule.To, "external-") || strings.HasSuffix(rule.To, "-external") {
				if rule.From == "*" {
					result.Passed = false
					result.Details = "外部API的访问源使用了通配符"
					result.AffectedServices = append(result.AffectedServices, rule.To)
					result.Recommendations = append(result.Recommendations, "将通配符源替换为具体的服务名称")
				}
			}
		}
	}

	if result.Passed {
		result.Details = "外部API访问控制符合安全要求"
	}
}

func (sc *ScenarioChecker) checkPublicAPI(scenario models.ComplianceScenarioTemplate, policies []models.AuthorizationPolicy, result *models.SemanticComplianceResult) {
	for _, policy := range policies {
		if policy.Action != "ALLOW" {
			continue
		}
		for _, rule := range policy.Rules {
			for _, path := range rule.Paths {
				if strings.HasPrefix(path, "/public") {
					hasWriteMethod := false
					for _, method := range rule.Methods {
						if method == "*" || method == "POST" || method == "PUT" || method == "DELETE" || method == "PATCH" {
							hasWriteMethod = true
							break
						}
					}
					if hasWriteMethod {
						result.Passed = false
						result.Details = "公开API允许了写操作"
						result.AffectedServices = append(result.AffectedServices, rule.To)
						result.Recommendations = append(result.Recommendations, "公开API仅允许GET和HEAD方法")
					}
				}
			}
		}
	}

	if result.Passed {
		result.Details = "公开API访问控制符合安全要求"
	}
}

func (sc *ScenarioChecker) checkUserData(scenario models.ComplianceScenarioTemplate, policies []models.AuthorizationPolicy, result *models.SemanticComplianceResult) {
	for _, policy := range policies {
		if policy.Action != "ALLOW" {
			continue
		}
		for _, rule := range policy.Rules {
			if rule.To == "user-service" {
				if rule.From == "*" || (rule.From != "frontend" && rule.From != "api-gateway") {
					result.Passed = false
					result.Details = "用户服务的访问源限制不符合要求"
					result.AffectedServices = append(result.AffectedServices, "user-service")
					result.Recommendations = append(result.Recommendations, "用户服务仅允许frontend和api-gateway访问")
				}
			}
		}
	}

	if result.Passed {
		result.Details = "用户数据访问控制符合安全要求"
	}
}

func (sc *ScenarioChecker) checkMQAccess(scenario models.ComplianceScenarioTemplate, policies []models.AuthorizationPolicy, result *models.SemanticComplianceResult) {
	for _, policy := range policies {
		if policy.Action != "ALLOW" {
			continue
		}
		for _, rule := range policy.Rules {
			if strings.Contains(rule.To, "mq") || strings.Contains(rule.To, "kafka") || strings.Contains(rule.To, "rabbit") {
				if rule.From == "*" {
					result.Passed = false
					result.Details = "消息队列的访问源使用了通配符"
					result.AffectedServices = append(result.AffectedServices, rule.To)
					result.Recommendations = append(result.Recommendations, "明确指定允许访问消息队列的服务")
				}
			}
		}
	}

	if result.Passed {
		result.Details = "消息队列访问控制符合安全要求"
	}
}

func (sc *ScenarioChecker) checkCacheAccess(scenario models.ComplianceScenarioTemplate, policies []models.AuthorizationPolicy, result *models.SemanticComplianceResult) {
	for _, policy := range policies {
		if policy.Action != "ALLOW" {
			continue
		}
		for _, rule := range policy.Rules {
			if strings.Contains(rule.To, "redis") || strings.Contains(rule.To, "cache") {
				if rule.From == "*" {
					result.Passed = false
					result.Details = "缓存服务的访问源使用了通配符"
					result.AffectedServices = append(result.AffectedServices, rule.To)
					result.Recommendations = append(result.Recommendations, "仅允许业务服务访问缓存")
				}
			}
		}
	}

	if result.Passed {
		result.Details = "缓存服务访问控制符合安全要求"
	}
}

func (sc *ScenarioChecker) checkCircularDependency(scenario models.ComplianceScenarioTemplate, graph *models.ServiceGraph, result *models.SemanticComplianceResult) {
	if graph == nil {
		result.Passed = true
		result.Details = "无服务图数据，跳过循环依赖检查"
		return
	}

	serviceCalls := make(map[string]map[string]bool)
	for _, edge := range graph.Edges {
		if _, ok := serviceCalls[edge.Source.Name]; !ok {
			serviceCalls[edge.Source.Name] = make(map[string]bool)
		}
		serviceCalls[edge.Source.Name][edge.Destination.Name] = true
	}

	visited := make(map[string]bool)
	recStack := make(map[string]bool)
	hasCycle := false
	cyclePath := make([]string, 0)

	var dfs func(string, []string) bool
	dfs = func(service string, path []string) bool {
		visited[service] = true
		recStack[service] = true
		path = append(path, service)

		for dest := range serviceCalls[service] {
			if !visited[dest] {
				if dfs(dest, path) {
					return true
				}
			} else if recStack[dest] {
				hasCycle = true
				cyclePath = append(path, dest)
				return true
			}
		}

		recStack[service] = false
		return false
	}

	for service := range serviceCalls {
		if !visited[service] {
			dfs(service, make([]string, 0))
		}
	}

	if hasCycle {
		result.Passed = false
		result.Details = "检测到服务间循环依赖: " + strings.Join(cyclePath, " -> ")
		result.AffectedServices = cyclePath
		result.Recommendations = append(result.Recommendations, "重构服务调用关系，消除循环依赖")
		result.Recommendations = append(result.Recommendations, "考虑引入消息队列解耦服务")
	} else {
		result.Details = "服务间无循环依赖，符合架构要求"
	}
}

func (sc *ScenarioChecker) checkSensitivePaths(scenario models.ComplianceScenarioTemplate, policies []models.AuthorizationPolicy, result *models.SemanticComplianceResult) {
	for _, policy := range policies {
		if policy.Action != "ALLOW" {
			continue
		}
		for _, rule := range policy.Rules {
			for _, path := range rule.Paths {
				if strings.Contains(path, "payment") || strings.Contains(path, "credit") || strings.Contains(path, "card") {
					if rule.From == "*" {
						result.Passed = false
						result.Details = "敏感数据路径的访问源使用了通配符"
						result.AffectedServices = append(result.AffectedServices, rule.To)
						result.Recommendations = append(result.Recommendations, "敏感数据路径需要严格限制访问源")
					}
				}
			}
		}
	}

	if result.Passed {
		result.Details = "敏感数据路径访问控制符合安全要求"
	}
}
