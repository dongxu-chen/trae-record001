package autofix

import (
	"encoding/json"
	"fmt"
	"time"

	"servicemesh-policy/internal/models"
)

type AutoFixer struct{}

func NewAutoFixer() *AutoFixer {
	return &AutoFixer{}
}

func (af *AutoFixer) GenerateFix(policy *models.Policy, issueType string) (*models.AutoFixResult, error) {
	result := &models.AutoFixResult{
		Success: true,
	}

	var patch *models.PolicyPatch
	var err error

	switch issueType {
	case "tls_mode_to_strict":
		patch, err = af.fixTLSModeToStrict(policy)
	case "add_jwt_authentication":
		patch, err = af.addJWTAuthentication(policy)
	case "add_authorization_policy":
		patch, err = af.addAuthorizationPolicy(policy)
	case "fix_conflict":
		patch, err = af.fixPolicyConflict(policy)
	case "add_default_deny":
		patch, err = af.addDefaultDenyPolicy(policy)
	case "update_tls_version":
		patch, err = af.updateTLSVersion(policy)
	case "add_audit_logging":
		patch, err = af.addAuditLogging(policy)
	default:
		result.Success = false
		result.Message = fmt.Sprintf("未知的修复类型: %s", issueType)
		return result, nil
	}

	if err != nil {
		result.Success = false
		result.Message = err.Error()
		return result, nil
	}

	result.Patch = patch
	result.Message = "修复补丁生成成功"

	return result, nil
}

func (af *AutoFixer) fixTLSModeToStrict(policy *models.Policy) (*models.PolicyPatch, error) {
	if policy.Type != models.PolicyTypeMTLS {
		return nil, fmt.Errorf("该修复仅适用于 mTLS 策略")
	}

	originalSpec, err := af.specToMap(policy.Spec)
	if err != nil {
		return nil, err
	}

	patchedSpec := make(map[string]interface{})
	for k, v := range originalSpec {
		patchedSpec[k] = v
	}
	patchedSpec["mode"] = "STRICT"

	patch := &models.PolicyPatch{
		PatchID:      generatePatchID(),
		PolicyID:     policy.ID,
		IssueType:    "tls_mode_to_strict",
		Description:  "将 mTLS 模式从 PERMISSIVE 升级为 STRICT",
		OriginalSpec: originalSpec,
		PatchedSpec:  patchedSpec,
		Changes: []models.PatchChange{
			{
				Operation: "replace",
				Path:      "/spec/mode",
				OldValue:  originalSpec["mode"],
				NewValue:  "STRICT",
				Reason:    "PCI DSS / GDPR 要求强制加密传输，PERMISSIVE 模式允许明文通信",
			},
		},
		RiskLevel:  "low",
		Confidence: 0.95,
		CreatedAt:  time.Now(),
	}

	return patch, nil
}

func (af *AutoFixer) addJWTAuthentication(policy *models.Policy) (*models.PolicyPatch, error) {
	originalSpec, err := af.specToMap(policy.Spec)
	if err != nil {
		return nil, err
	}

	patchedSpec := map[string]interface{}{
		"jwtRules": []interface{}{
			map[string]interface{}{
				"issuer":  "https://auth.example.com",
				"jwksUri": "https://auth.example.com/.well-known/jwks.json",
				"audiences": []string{
					"example.com",
				},
			},
		},
		"selector": map[string]interface{}{
			"matchLabels": map[string]interface{}{
				"app": policy.Name,
			},
		},
	}

	patch := &models.PolicyPatch{
		PatchID:      generatePatchID(),
		PolicyID:     policy.ID,
		IssueType:    "add_jwt_authentication",
		Description:  "为服务添加 JWT 认证规则",
		OriginalSpec: originalSpec,
		PatchedSpec:  patchedSpec,
		Changes: []models.PatchChange{
			{
				Operation: "add",
				Path:      "/spec/jwtRules",
				OldValue:  nil,
				NewValue:  patchedSpec["jwtRules"],
				Reason:    "PCI DSS Requirement 8.1 要求对所有用户进行身份认证",
			},
			{
				Operation: "add",
				Path:      "/spec/selector",
				OldValue:  nil,
				NewValue:  patchedSpec["selector"],
				Reason:    "指定策略应用的服务",
			},
		},
		RiskLevel:  "medium",
		Confidence: 0.85,
		CreatedAt:  time.Now(),
	}

	return patch, nil
}

func (af *AutoFixer) addAuthorizationPolicy(policy *models.Policy) (*models.PolicyPatch, error) {
	originalSpec, err := af.specToMap(policy.Spec)
	if err != nil {
		return nil, err
	}

	patchedSpec := map[string]interface{}{
		"action": "ALLOW",
		"rules": []interface{}{
			map[string]interface{}{
				"from": []interface{}{
					map[string]interface{}{
						"source": map[string]interface{}{
							"principals": []string{
								"cluster.local/ns/default/sa/frontend",
							},
						},
					},
				},
				"to": []interface{}{
					map[string]interface{}{
						"operation": map[string]interface{}{
							"methods": []string{"GET", "POST"},
						},
					},
				},
			},
		},
		"selector": map[string]interface{}{
			"matchLabels": map[string]interface{}{
				"app": policy.Name,
			},
		},
	}

	patch := &models.PolicyPatch{
		PatchID:      generatePatchID(),
		PolicyID:     policy.ID,
		IssueType:    "add_authorization_policy",
		Description:  "添加基于角色的访问控制策略",
		OriginalSpec: originalSpec,
		PatchedSpec:  patchedSpec,
		Changes: []models.PatchChange{
			{
				Operation: "add",
				Path:      "/spec/action",
				OldValue:  nil,
				NewValue:  "ALLOW",
				Reason:    "设置默认允许动作",
			},
			{
				Operation: "add",
				Path:      "/spec/rules",
				OldValue:  nil,
				NewValue:  patchedSpec["rules"],
				Reason:    "最小权限原则：只允许授权服务访问",
			},
		},
		RiskLevel:  "medium",
		Confidence: 0.80,
		CreatedAt:  time.Now(),
	}

	return patch, nil
}

func (af *AutoFixer) fixPolicyConflict(policy *models.Policy) (*models.PolicyPatch, error) {
	originalSpec, err := af.specToMap(policy.Spec)
	if err != nil {
		return nil, err
	}

	patchedSpec := make(map[string]interface{})
	for k, v := range originalSpec {
		patchedSpec[k] = v
	}

	if labels, ok := patchedSpec["labels"].(map[string]interface{}); ok {
		labels["priority"] = "high"
	} else {
		patchedSpec["labels"] = map[string]interface{}{
			"priority": "high",
		}
	}

	patch := &models.PolicyPatch{
		PatchID:      generatePatchID(),
		PolicyID:     policy.ID,
		IssueType:    "fix_conflict",
		Description:  "提升策略优先级以解决冲突",
		OriginalSpec: originalSpec,
		PatchedSpec:  patchedSpec,
		Changes: []models.PatchChange{
			{
				Operation: "add",
				Path:      "/metadata/labels/priority",
				OldValue:  nil,
				NewValue:  "high",
				Reason:    "提升优先级，确保该策略在冲突中获胜",
			},
		},
		RiskLevel:  "low",
		Confidence: 0.90,
		CreatedAt:  time.Now(),
	}

	altPatch := &models.PolicyPatch{
		PatchID:      generatePatchID(),
		PolicyID:     policy.ID,
		IssueType:    "fix_conflict",
		Description:  "调整策略选择器避免冲突",
		OriginalSpec: originalSpec,
		PatchedSpec:  patchedSpec,
		Changes: []models.PatchChange{
			{
				Operation: "modify",
				Path:      "/spec/selector",
				OldValue:  originalSpec["selector"],
				NewValue:  map[string]interface{}{"matchLabels": map[string]interface{}{"app": "specific-service"}},
				Reason:    "缩小选择器范围，避免与其他策略重叠",
			},
		},
		RiskLevel:  "medium",
		Confidence: 0.70,
		CreatedAt:  time.Now(),
	}

	patch.Alternatives = []models.PolicyPatch{*altPatch}

	return patch, nil
}

func (af *AutoFixer) addDefaultDenyPolicy(policy *models.Policy) (*models.PolicyPatch, error) {
	originalSpec, err := af.specToMap(policy.Spec)
	if err != nil {
		return nil, err
	}

	patchedSpec := map[string]interface{}{
		"action":   "DENY",
		"rules":    []interface{}{},
		"selector": map[string]interface{}{},
	}

	patch := &models.PolicyPatch{
		PatchID:      generatePatchID(),
		PolicyID:     policy.ID,
		IssueType:    "add_default_deny",
		Description:  "添加默认拒绝策略，实现最小权限原则",
		OriginalSpec: originalSpec,
		PatchedSpec:  patchedSpec,
		Changes: []models.PatchChange{
			{
				Operation: "replace",
				Path:      "/spec/action",
				OldValue:  originalSpec["action"],
				NewValue:  "DENY",
				Reason:    "安全最佳实践：默认拒绝所有未明确允许的请求",
			},
			{
				Operation: "replace",
				Path:      "/spec/selector",
				OldValue:  originalSpec["selector"],
				NewValue:  map[string]interface{}{},
				Reason:    "空选择器匹配所有工作负载",
			},
		},
		RiskLevel:  "high",
		Confidence: 0.95,
		CreatedAt:  time.Now(),
	}

	return patch, nil
}

func (af *AutoFixer) updateTLSVersion(policy *models.Policy) (*models.PolicyPatch, error) {
	originalSpec, err := af.specToMap(policy.Spec)
	if err != nil {
		return nil, err
	}

	patchedSpec := make(map[string]interface{})
	for k, v := range originalSpec {
		patchedSpec[k] = v
	}

	patchedSpec["minProtocolVersion"] = "TLSV1_2"
	patchedSpec["cipherSuites"] = []string{
		"ECDHE-ECDSA-AES256-GCM-SHA384",
		"ECDHE-RSA-AES256-GCM-SHA384",
		"ECDHE-ECDSA-AES128-GCM-SHA256",
		"ECDHE-RSA-AES128-GCM-SHA256",
	}

	patch := &models.PolicyPatch{
		PatchID:      generatePatchID(),
		PolicyID:     policy.ID,
		IssueType:    "update_tls_version",
		Description:  "升级 TLS 版本到 1.2+ 并使用安全密码套件",
		OriginalSpec: originalSpec,
		PatchedSpec:  patchedSpec,
		Changes: []models.PatchChange{
			{
				Operation: "add",
				Path:      "/spec/minProtocolVersion",
				OldValue:  nil,
				NewValue:  "TLSV1_2",
				Reason:    "PCI DSS Requirement 2.2.3 要求 TLS 1.2+",
			},
			{
				Operation: "add",
				Path:      "/spec/cipherSuites",
				OldValue:  nil,
				NewValue:  patchedSpec["cipherSuites"],
				Reason:    "仅使用 NIST 推荐的安全密码套件",
			},
		},
		RiskLevel:  "medium",
		Confidence: 0.90,
		CreatedAt:  time.Now(),
	}

	return patch, nil
}

func (af *AutoFixer) addAuditLogging(policy *models.Policy) (*models.PolicyPatch, error) {
	originalSpec, err := af.specToMap(policy.Spec)
	if err != nil {
		return nil, err
	}

	patchedSpec := make(map[string]interface{})
	for k, v := range originalSpec {
		patchedSpec[k] = v
	}

	patchedSpec["auditLog"] = map[string]interface{}{
		"enabled": true,
		"include": []string{
			"request.method",
			"request.path",
			"source.principal",
			"destination.service",
			"response.code",
		},
	}

	patch := &models.PolicyPatch{
		PatchID:      generatePatchID(),
		PolicyID:     policy.ID,
		IssueType:    "add_audit_logging",
		Description:  "启用审计日志记录",
		OriginalSpec: originalSpec,
		PatchedSpec:  patchedSpec,
		Changes: []models.PatchChange{
			{
				Operation: "add",
				Path:      "/spec/auditLog",
				OldValue:  nil,
				NewValue:  patchedSpec["auditLog"],
				Reason:    "PCI DSS Requirement 10.2 要求记录所有访问活动",
			},
		},
		RiskLevel:  "low",
		Confidence: 0.95,
		CreatedAt:  time.Now(),
	}

	return patch, nil
}

func (af *AutoFixer) specToMap(spec interface{}) (map[string]interface{}, error) {
	if spec == nil {
		return make(map[string]interface{}), nil
	}

	bytes, err := json.Marshal(spec)
	if err != nil {
		return nil, err
	}

	var result map[string]interface{}
	err = json.Unmarshal(bytes, &result)
	if err != nil {
		return nil, err
	}

	return result, nil
}

func (af *AutoFixer) GetAvailableFixes() []map[string]string {
	return []map[string]string{
		{
			"id":          "tls_mode_to_strict",
			"name":        "强制 mTLS 加密",
			"description": "将 PERMISSIVE 模式升级为 STRICT 模式",
			"risk":        "low",
			"applies_to":  "PeerAuthentication",
		},
		{
			"id":          "add_jwt_authentication",
			"name":        "添加 JWT 认证",
			"description": "为 API 端点添加 JWT 身份验证",
			"risk":        "medium",
			"applies_to":  "RequestAuthentication",
		},
		{
			"id":          "add_authorization_policy",
			"name":        "添加访问控制",
			"description": "添加基于角色的授权策略",
			"risk":        "medium",
			"applies_to":  "AuthorizationPolicy",
		},
		{
			"id":          "add_default_deny",
			"name":        "默认拒绝策略",
			"description": "添加默认拒绝所有请求的策略",
			"risk":        "high",
			"applies_to":  "AuthorizationPolicy",
		},
		{
			"id":          "update_tls_version",
			"name":        "升级 TLS 版本",
			"description": "强制使用 TLS 1.2+ 和安全密码套件",
			"risk":        "medium",
			"applies_to":  "Gateway",
		},
		{
			"id":          "add_audit_logging",
			"name":        "启用审计日志",
			"description": "记录所有访问和授权决策",
			"risk":        "low",
			"applies_to":  "All",
		},
		{
			"id":          "fix_conflict",
			"name":        "解决策略冲突",
			"description": "自动调整策略以解决冲突",
			"risk":        "low",
			"applies_to":  "All",
		},
	}
}

func generatePatchID() string {
	return fmt.Sprintf("patch-%d", time.Now().Unix())
}
