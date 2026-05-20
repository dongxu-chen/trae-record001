package rules

import (
	"fmt"
	"regexp"
	"strings"

	"k8s.io/apimachinery/pkg/api/resource"

	"k8s-auditor/pkg/audit"
	"k8s-auditor/pkg/config"
)

type RuleChecker interface {
	Check(resource audit.ResourceInfo) []audit.Violation
}

type ResourceQuotaChecker struct {
	cfg config.ResourceQuotaConfig
}

type LabelsChecker struct {
	cfg config.LabelsConfig
}

type ImageSourceChecker struct {
	cfg                  config.ImageSourceConfig
	authorizedRegistries map[string]bool
}

func NewResourceQuotaChecker(cfg config.ResourceQuotaConfig) *ResourceQuotaChecker {
	return &ResourceQuotaChecker{cfg: cfg}
}

func NewLabelsChecker(cfg config.LabelsConfig) *LabelsChecker {
	return &LabelsChecker{cfg: cfg}
}

func NewImageSourceChecker(cfg config.ImageSourceConfig) *ImageSourceChecker {
	return &ImageSourceChecker{
		cfg:                  cfg,
		authorizedRegistries: make(map[string]bool),
	}
}

func (i *ImageSourceChecker) SetAuthorizedRegistries(registries map[string]bool) {
	i.authorizedRegistries = registries
}

func (r *ResourceQuotaChecker) Check(resource audit.ResourceInfo) []audit.Violation {
	if !r.cfg.Enabled {
		return nil
	}

	var violations []audit.Violation

	containers := extractContainers(resource)
	for _, container := range containers {
		if container.Resources.Requests.Cpu().IsZero() {
			violations = append(violations, audit.Violation{
				ResourceType: resource.Type,
				Namespace:  resource.Namespace,
				ResourceName: resource.Name,
				RuleType:   "resource_quota",
				Severity:   audit.SeverityHigh,
				Message:    fmt.Sprintf("Container '%s' 缺少 CPU 请求", container.Name),
				Suggestion: fmt.Sprintf("为容器设置 CPU 请求，建议范围: %s - %s", r.cfg.CPURequestMin, r.cfg.CPURequestMax),
			})
		} else {
			cpu := container.Resources.Requests.Cpu()
			minCPU, _ := resource.ParseQuantity(r.cfg.CPURequestMin)
			maxCPU, _ := resource.ParseQuantity(r.cfg.CPURequestMax)
			if cpu.Cmp(minCPU) < 0 || cpu.Cmp(maxCPU) > 0 {
				violations = append(violations, audit.Violation{
					ResourceType: resource.Type,
					Namespace:  resource.Namespace,
					ResourceName: resource.Name,
					RuleType:   "resource_quota",
					Severity:   audit.SeverityMedium,
					Message:    fmt.Sprintf("容器 '%s' CPU 请求 %s 超出范围 [%s, %s]", container.Name, cpu.String(), r.cfg.CPURequestMin, r.cfg.CPURequestMax),
					Suggestion: fmt.Sprintf("调整 CPU 请求至推荐范围: %s - %s", r.cfg.CPURequestMin, r.cfg.CPURequestMax),
				})
			}
		}

		if container.Resources.Requests.Memory().IsZero() {
			violations = append(violations, audit.Violation{
				ResourceType: resource.Type,
				Namespace:  resource.Namespace,
				ResourceName: resource.Name,
				RuleType:   "resource_quota",
				Severity:   audit.SeverityHigh,
				Message:    fmt.Sprintf("Container '%s' 缺少内存请求", container.Name),
				Suggestion: fmt.Sprintf("为容器设置内存请求，建议范围: %s - %s", r.cfg.MemoryRequestMin, r.cfg.MemoryRequestMax),
			})
		} else {
			mem := container.Resources.Requests.Memory()
			minMem, _ := resource.ParseQuantity(r.cfg.MemoryRequestMin)
			maxMem, _ := resource.ParseQuantity(r.cfg.MemoryRequestMax)
			if mem.Cmp(minMem) < 0 || mem.Cmp(maxMem) > 0 {
				violations = append(violations, audit.Violation{
					ResourceType: resource.Type,
					Namespace:  resource.Namespace,
					ResourceName: resource.Name,
					RuleType:   "resource_quota",
					Severity:   audit.SeverityMedium,
					Message:    fmt.Sprintf("容器 '%s' 内存请求 %s 超出范围 [%s, %s]", container.Name, mem.String(), r.cfg.MemoryRequestMin, r.cfg.MemoryRequestMax),
					Suggestion: fmt.Sprintf("调整内存请求至推荐范围: %s - %s", r.cfg.MemoryRequestMin, r.cfg.MemoryRequestMax),
				})
			}
		}

		if container.Resources.Limits.Cpu().IsZero() {
			violations = append(violations, audit.Violation{
				ResourceType: resource.Type,
				Namespace:  resource.Namespace,
				ResourceName: resource.Name,
				RuleType:   "resource_quota",
				Severity:   audit.SeverityHigh,
				Message:    fmt.Sprintf("Container '%s' 缺少 CPU 限制", container.Name),
				Suggestion: fmt.Sprintf("为容器设置 CPU 限制，建议范围: %s - %s", r.cfg.CPULimitMin, r.cfg.CPULimitMax),
			})
		} else {
			cpu := container.Resources.Limits.Cpu()
			minCPU, _ := resource.ParseQuantity(r.cfg.CPULimitMin)
			maxCPU, _ := resource.ParseQuantity(r.cfg.CPULimitMax)
			if cpu.Cmp(minCPU) < 0 || cpu.Cmp(maxCPU) > 0 {
				violations = append(violations, audit.Violation{
					ResourceType: resource.Type,
					Namespace:  resource.Namespace,
					ResourceName: resource.Name,
					RuleType:   "resource_quota",
					Severity:   audit.SeverityMedium,
					Message:    fmt.Sprintf("容器 '%s' CPU 限制 %s 超出范围 [%s, %s]", container.Name, cpu.String(), r.cfg.CPULimitMin, r.cfg.CPULimitMax),
					Suggestion: fmt.Sprintf("调整 CPU 限制至推荐范围: %s - %s", r.cfg.CPULimitMin, r.cfg.CPULimitMax),
				})
			}
		}

		if container.Resources.Limits.Memory().IsZero() {
			violations = append(violations, audit.Violation{
				ResourceType: resource.Type,
				Namespace:  resource.Namespace,
				ResourceName: resource.Name,
				RuleType:   "resource_quota",
				Severity:   audit.SeverityHigh,
				Message:    fmt.Sprintf("Container '%s' 缺少内存限制", container.Name),
				Suggestion: fmt.Sprintf("为容器设置内存限制，建议范围: %s - %s", r.cfg.MemoryLimitMin, r.cfg.MemoryLimitMax),
			})
		} else {
			mem := container.Resources.Limits.Memory()
			minMem, _ := resource.ParseQuantity(r.cfg.MemoryLimitMin)
			maxMem, _ := resource.ParseQuantity(r.cfg.MemoryLimitMax)
			if mem.Cmp(minMem) < 0 || mem.Cmp(maxMem) > 0 {
				violations = append(violations, audit.Violation{
					ResourceType: resource.Type,
					Namespace:  resource.Namespace,
					ResourceName: resource.Name,
					RuleType:   "resource_quota",
					Severity:   audit.SeverityMedium,
					Message:    fmt.Sprintf("容器 '%s' 内存限制 %s 超出范围 [%s, %s]", container.Name, mem.String(), r.cfg.MemoryLimitMin, r.cfg.MemoryLimitMax),
					Suggestion: fmt.Sprintf("调整内存限制至推荐范围: %s - %s", r.cfg.MemoryLimitMin, r.cfg.MemoryLimitMax),
				})
			}
		}
	}

	return violations
}

func (l *LabelsChecker) Check(resource audit.ResourceInfo) []audit.Violation {
	if !l.cfg.Enabled {
		return nil
	}

	var violations []audit.Violation

	for _, required := range l.cfg.Required {
		if _, ok := resource.Labels[required]; !ok {
			violations = append(violations, audit.Violation{
				ResourceType: resource.Type,
				Namespace:  resource.Namespace,
				ResourceName: resource.Name,
				RuleType:   "labels",
				Severity:   audit.SeverityMedium,
				Message:    fmt.Sprintf("缺少必需标签: %s", required),
				Suggestion: fmt.Sprintf("添加标签 '%s' 到资源", required),
			})
		}
	}

	for label, pattern := range l.cfg.Patterns {
		value, ok := resource.Labels[label]
		if !ok {
			continue
		}
		matched, _ := regexp.MatchString(pattern, value)
		if !matched {
			violations = append(violations, audit.Violation{
				ResourceType: resource.Type,
				Namespace:  resource.Namespace,
				ResourceName: resource.Name,
				RuleType:   "labels",
				Severity:   audit.SeverityLow,
				Message:    fmt.Sprintf("标签 '%s' 的值 '%s' 不匹配模式: %s", label, value, pattern),
				Suggestion: fmt.Sprintf("修改标签 '%s' 的值以匹配模式: %s", label, pattern),
			})
		}
	}

	return violations
}

func (i *ImageSourceChecker) Check(resource audit.ResourceInfo) []audit.Violation {
	if !i.cfg.Enabled {
		return nil
	}

	var violations []audit.Violation

	containers := extractContainers(resource)
	for _, container := range containers {
		image := container.Image
		if image == "" {
			continue
		}

		registry, repo, tag := parseImage(image)

		for _, disallowed := range i.cfg.DisallowedTags {
			if tag == disallowed || tag == "" {
				violations = append(violations, audit.Violation{
					ResourceType: resource.Type,
					Namespace:  resource.Namespace,
					ResourceName: resource.Name,
					RuleType:   "image_source",
					Severity:   audit.SeverityHigh,
					Message:    fmt.Sprintf("容器 '%s' 使用了不允许的镜像标签: %s", container.Name, tag),
					Suggestion: fmt.Sprintf("使用具体的镜像版本标签，避免使用 '%s' 或空标签", disallowed),
				})
				break
			}
		}

		if len(i.cfg.AllowedRegistries) > 0 && registry != "" {
			allowed := false
			for _, ar := range i.cfg.AllowedRegistries {
				if registry == ar || strings.HasPrefix(registry, ar) {
					allowed = true
					break
				}
			}
			if !allowed {
				violations = append(violations, audit.Violation{
					ResourceType: resource.Type,
					Namespace:  resource.Namespace,
					ResourceName: resource.Name,
					RuleType:   "image_source",
					Severity:   audit.SeverityCritical,
					Message:    fmt.Sprintf("容器 '%s' 使用了未授权的镜像仓库: %s", container.Name, registry),
					Suggestion: fmt.Sprintf("将镜像 '%s' 迁移到允许的仓库之一: %v", repo, i.cfg.AllowedRegistries),
				})
			}
		}

		if i.cfg.CheckPrivateRegistryAuth && registry != "" {
			isPrivate := false
			for _, pr := range i.cfg.PrivateRegistries {
				if registry == pr || strings.HasPrefix(registry, pr) {
					isPrivate = true
					break
				}
			}

			if isPrivate && len(i.authorizedRegistries) > 0 {
				authorized := false
				for authReg := range i.authorizedRegistries {
					if registry == authReg || strings.HasPrefix(registry, authReg) {
						authorized = true
						break
					}
				}
				if !authorized {
					violations = append(violations, audit.Violation{
						ResourceType: resource.Type,
						Namespace:  resource.Namespace,
						ResourceName: resource.Name,
						RuleType:   "image_private_registry_auth",
						Severity:   audit.SeverityHigh,
						Message:    fmt.Sprintf("容器 '%s' 使用私有仓库 '%s' 但未配置有效的拉取Secret", container.Name, registry),
						Suggestion: fmt.Sprintf("在命名空间 '%s' 中创建包含 '%s' 认证信息的dockerconfigjson类型Secret，并在Pod或ServiceAccount中引用", resource.Namespace, registry),
					})
				}
			}
		}
	}

	return violations
}

type Container struct {
	Name      string
	Image     string
	Resources ResourceRequirements
}

type ResourceRequirements struct {
	Requests ResourceList
	Limits   ResourceList
}

type ResourceList struct {
	CPU    resource.Quantity
	Memory resource.Quantity
}

func extractContainers(resource audit.ResourceInfo) []Container {
	var containers []Container

	spec, ok := resource.Spec.(map[string]interface{})
	if !ok {
		return containers
	}

	var podSpec map[string]interface{}

	switch resource.Type {
	case "pods":
		specVal, ok := spec["spec"].(map[string]interface{})
		if ok {
			podSpec = specVal
		}
	case "deployments", "statefulsets", "daemonsets":
		specVal, ok := spec["spec"].(map[string]interface{})
		if ok {
			template, ok := specVal["template"].(map[string]interface{})
			if ok {
				templateSpec, ok := template["spec"].(map[string]interface{})
				if ok {
					podSpec = templateSpec
				}
			}
		}
	}

	if podSpec == nil {
		return containers
	}

	containerList, ok := podSpec["containers"].([]interface{})
	if !ok {
		return containers
	}

	for _, c := range containerList {
		cm, ok := c.(map[string]interface{})
		if !ok {
			continue
		}

		container := Container{
			Name:  getString(cm, "name"),
			Image: getString(cm, "image"),
		}

		if resources, ok := cm["resources"].(map[string]interface{}); ok {
			container.Resources = parseResources(resources)
		}

		containers = append(containers, container)
	}

	return containers
}

func parseResources(resources map[string]interface{}) ResourceRequirements {
	var rr ResourceRequirements

	if requests, ok := resources["requests"].(map[string]interface{}); ok {
		rr.Requests.CPU = parseQuantity(requests, "cpu")
		rr.Requests.Memory = parseQuantity(requests, "memory")
	}

	if limits, ok := resources["limits"].(map[string]interface{}); ok {
		rr.Limits.CPU = parseQuantity(limits, "cpu")
		rr.Limits.Memory = parseQuantity(limits, "memory")
	}

	return rr
}

func parseQuantity(m map[string]interface{}, key string) resource.Quantity {
	val, ok := m[key]
	if !ok {
		return resource.Quantity{}
	}
	strVal, ok := val.(string)
	if !ok {
		return resource.Quantity{}
	}
	q, _ := resource.ParseQuantity(strVal)
	return q
}

func getString(m map[string]interface{}, key string) string {
	val, ok := m[key]
	if !ok {
		return ""
	}
	str, ok := val.(string)
	if !ok {
		return ""
	}
	return str
}

func parseImage(image string) (registry, repo, tag string) {
	parts := strings.Split(image, "/")
	if len(parts) > 1 && (strings.Contains(parts[0], ".") || strings.Contains(parts[0], ":")) {
		registry = parts[0]
		image = strings.Join(parts[1:], "/")
	}

	parts = strings.Split(image, ":")
	if len(parts) > 1 {
		tag = parts[len(parts)-1]
		repo = strings.Join(parts[:len(parts)-1], ":")
	} else {
		repo = image
		tag = "latest"
	}

	if registry != "" {
		repo = registry + "/" + repo
	}

	return
}
