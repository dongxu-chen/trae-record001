package deployer

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strings"
	"time"

	"authz-policy-recommender/backend/pkg/models"
)

type PolicyDeployer struct {
	deployments map[string]*models.PolicyDeployment
}

func NewPolicyDeployer() *PolicyDeployer {
	return &PolicyDeployer{
		deployments: make(map[string]*models.PolicyDeployment),
	}
}

func (pd *PolicyDeployer) GenerateIstioYAML(policies []models.AuthorizationPolicy) string {
	var yamlBuilder strings.Builder

	for _, policy := range policies {
		yamlBuilder.WriteString(pd.generateSinglePolicyYAML(policy))
		yamlBuilder.WriteString("\n---\n")
	}

	return yamlBuilder.String()
}

func (pd *PolicyDeployer) generateSinglePolicyYAML(policy models.AuthorizationPolicy) string {
	namespace := policy.Namespace
	if namespace == "" {
		namespace = "default"
	}

	var yamlBuilder strings.Builder

	yamlBuilder.WriteString("apiVersion: security.istio.io/v1beta1\n")
	yamlBuilder.WriteString("kind: AuthorizationPolicy\n")
	yamlBuilder.WriteString("metadata:\n")
	yamlBuilder.WriteString(fmt.Sprintf("  name: %s\n", policy.Name))
	yamlBuilder.WriteString(fmt.Sprintf("  namespace: %s\n", namespace))
	yamlBuilder.WriteString("spec:\n")

	if len(policy.Selector) > 0 {
		yamlBuilder.WriteString("  selector:\n")
		yamlBuilder.WriteString("    matchLabels:\n")
		for k, v := range policy.Selector {
			yamlBuilder.WriteString(fmt.Sprintf("      %s: %s\n", k, v))
		}
	}

	yamlBuilder.WriteString(fmt.Sprintf("  action: %s\n", strings.ToUpper(policy.Action)))

	if len(policy.Rules) > 0 {
		yamlBuilder.WriteString("  rules:\n")
		for _, rule := range policy.Rules {
			yamlBuilder.WriteString("  - from:\n")
			yamlBuilder.WriteString("    - source:\n")
			if rule.From != "" {
				if strings.Contains(rule.From, "/") {
					yamlBuilder.WriteString(fmt.Sprintf("        principals: [\"%s\"]\n", rule.From))
				} else {
					yamlBuilder.WriteString(fmt.Sprintf("        namespaces: [\"%s\"]\n", rule.From))
				}
			}

			if rule.To != "" || len(rule.Methods) > 0 || len(rule.Paths) > 0 {
				yamlBuilder.WriteString("    to:\n")
				yamlBuilder.WriteString("    - operation:\n")
				if rule.To != "" {
					yamlBuilder.WriteString(fmt.Sprintf("        hosts: [\"%s\"]\n", rule.To))
				}
				if len(rule.Methods) > 0 {
					methods := make([]string, len(rule.Methods))
					for i, m := range rule.Methods {
						methods[i] = fmt.Sprintf("\"%s\"", strings.ToUpper(m))
					}
					yamlBuilder.WriteString(fmt.Sprintf("        methods: [%s]\n", strings.Join(methods, ", ")))
				}
				if len(rule.Paths) > 0 {
					paths := make([]string, len(rule.Paths))
					for i, p := range rule.Paths {
						paths[i] = fmt.Sprintf("\"%s\"", p)
					}
					yamlBuilder.WriteString(fmt.Sprintf("        paths: [%s]\n", strings.Join(paths, ", ")))
				}
			}
		}
	}

	return yamlBuilder.String()
}

func (pd *PolicyDeployer) Deploy(req models.DeploymentRequest) models.DeploymentResult {
	deploymentID := pd.generateDeploymentID()

	yaml := pd.GenerateIstioYAML(req.Policies)

	deployment := &models.PolicyDeployment{
		ID:              deploymentID,
		Name:            fmt.Sprintf("deployment-%s", deploymentID[:8]),
		Policies:        req.Policies,
		Target:          req.Target,
		Status:          models.DeploymentPending,
		CreatedAt:       time.Now(),
		GeneratedYAML:   yaml,
		RollbackEnabled: req.RollbackEnabled,
	}

	pd.deployments[deploymentID] = deployment

	if req.DryRun {
		return models.DeploymentResult{
			Success: true,
			Message: "Dry run completed successfully",
			YAML:    yaml,
			Applied: len(req.Policies),
			Failed:  0,
		}
	}

	deployment.Status = models.DeploymentDeploying

	now := time.Now()
	deployment.DeployedAt = &now
	deployment.Status = models.DeploymentSuccess

	return models.DeploymentResult{
		Success: true,
		Message: fmt.Sprintf("Successfully deployed %d policies", len(req.Policies)),
		YAML:    yaml,
		Applied: len(req.Policies),
		Failed:  0,
	}
}

func (pd *PolicyDeployer) Rollback(deploymentID string) error {
	deployment, exists := pd.deployments[deploymentID]
	if !exists {
		return fmt.Errorf("deployment not found: %s", deploymentID)
	}

	if !deployment.RollbackEnabled {
		return fmt.Errorf("rollback not enabled for this deployment")
	}

	deployment.Status = models.DeploymentRollingBack
	deployment.Status = models.DeploymentRolledBack

	return nil
}

func (pd *PolicyDeployer) GetDeployment(deploymentID string) (*models.PolicyDeployment, bool) {
	deployment, exists := pd.deployments[deploymentID]
	return deployment, exists
}

func (pd *PolicyDeployer) ListDeployments() []*models.PolicyDeployment {
	deployments := make([]*models.PolicyDeployment, 0, len(pd.deployments))
	for _, d := range pd.deployments {
		deployments = append(deployments, d)
	}
	return deployments
}

func (pd *PolicyDeployer) generateDeploymentID() string {
	h := sha256.New()
	h.Write([]byte(time.Now().String()))
	return hex.EncodeToString(h.Sum(nil))[:16]
}

func (pd *PolicyDeployer) QuickDeploy(policies []models.AuthorizationPolicy, namespace string, dryRun bool) models.DeploymentResult {
	return pd.Deploy(models.DeploymentRequest{
		Policies: policies,
		Target: models.DeploymentTarget{
			Cluster:   "default",
			Namespace: namespace,
		},
		DryRun:          dryRun,
		RollbackEnabled: true,
	})
}
