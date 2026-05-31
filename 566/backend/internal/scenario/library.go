package scenario

import (
	"time"

	"github.com/google/uuid"
	"fault-injection-platform/internal/model"
)

type Library struct {
	presets []*model.PresetScenario
}

func NewLibrary() *Library {
	lib := &Library{
		presets: make([]*model.PresetScenario, 0),
	}
	lib.initBuiltinScenarios()
	return lib
}

func (l *Library) initBuiltinScenarios() {
	now := time.Now()

	l.presets = append(l.presets, &model.PresetScenario{
		ID:                "builtin-network-latency-500ms",
		Name:              "500ms网络延迟",
		Description:       "模拟网络拥塞，给目标服务注入500ms固定延迟，用于测试系统在中等延迟下的用户体验。",
		Category:          model.PresetCategoryNetwork,
		Tags:              []string{"network", "latency", "medium"},
		Severity:          "medium",
		EstimatedDuration: 60,
		FaultConfig: &model.Fault{
			ID:            uuid.New().String(),
			Type:          model.FaultTypeDelay,
			Percentage:    100,
			Duration:      60,
			DelayConfig: &model.DelayConfig{
				Distribution: model.DelayDistributionFixed,
				FixedDelay:   500,
			},
		},
		IsBuiltin: true,
		CreatedAt:  now,
		UpdatedAt:  now,
	})

	l.presets = append(l.presets, &model.PresetScenario{
		ID:                "builtin-network-latency-normal",
		Name:              "网络波动模拟",
		Description:       "使用正态分布模拟真实网络波动，均值1000ms，标准差300ms，模拟真实互联网环境。",
		Category:          model.PresetCategoryNetwork,
		Tags:              []string{"network", "latency", "normal-distribution"},
		Severity:          "medium",
		EstimatedDuration: 120,
		FaultConfig: &model.Fault{
			ID:            uuid.New().String(),
			Type:          model.FaultTypeDelay,
			Percentage:    100,
			Duration:      120,
			DelayConfig: &model.DelayConfig{
				Distribution: model.DelayDistributionNormal,
				MeanDelay:    1000,
				StdDevDelay:  300,
				MinDelay:     100,
				MaxDelay:     5000,
			},
		},
		IsBuiltin: true,
		CreatedAt:  now,
		UpdatedAt:  now,
	})

	l.presets = append(l.presets, &model.PresetScenario{
		ID:                "builtin-network-longtail",
		Name:              "长尾延迟测试",
		Description:       "使用指数分布模拟长尾延迟场景，大部分请求延迟较小，但少数请求延迟很长，测试系统对异常请求的处理能力。",
		Category:          model.PresetCategoryNetwork,
		Tags:              []string{"network", "latency", "long-tail", "exponential"},
		Severity:          "high",
		EstimatedDuration: 120,
		FaultConfig: &model.Fault{
			ID:            uuid.New().String(),
			Type:          model.FaultTypeDelay,
			Percentage:    100,
			Duration:      120,
			DelayConfig: &model.DelayConfig{
				Distribution: model.DelayDistributionExponential,
				MeanDelay:    500,
				MinDelay:     50,
				MaxDelay:     10000,
			},
		},
		IsBuiltin: true,
		CreatedAt:  now,
		UpdatedAt:  now,
	})

	l.presets = append(l.presets, &model.PresetScenario{
		ID:                "builtin-service-503-10pct",
		Name:              "10%服务不可用",
		Description:       "模拟10%的请求返回503错误，测试系统在部分服务失败时的降级处理能力。",
		Category:          model.PresetCategoryService,
		Tags:              []string{"service", "error", "503", "partial-failure"},
		Severity:          "low",
		EstimatedDuration: 60,
		FaultConfig: &model.Fault{
			ID:         uuid.New().String(),
			Type:       model.FaultTypeAbort,
			Percentage: 10,
			Duration:   60,
			AbortConfig: &model.AbortConfig{
				HTTPStatus: 503,
				Message:    "Service Unavailable",
			},
		},
		IsBuiltin: true,
		CreatedAt:  now,
		UpdatedAt:  now,
	})

	l.presets = append(l.presets, &model.PresetScenario{
		ID:                "builtin-service-503-50pct",
		Name:              "50%服务不可用",
		Description:       "模拟半数请求返回503错误，测试系统在严重服务降级场景下的容错能力和用户体验。",
		Category:          model.PresetCategoryService,
		Tags:              []string{"service", "error", "503", "degradation"},
		Severity:          "high",
		EstimatedDuration: 60,
		FaultConfig: &model.Fault{
			ID:         uuid.New().String(),
			Type:       model.FaultTypeAbort,
			Percentage: 50,
			Duration:   60,
			AbortConfig: &model.AbortConfig{
				HTTPStatus: 503,
				Message:    "Service Unavailable",
			},
		},
		IsBuiltin: true,
		CreatedAt:  now,
		UpdatedAt:  now,
	})

	l.presets = append(l.presets, &model.PresetScenario{
		ID:                "builtin-service-500-error",
		Name:              "内部服务错误",
		Description:       "模拟20%的请求返回500错误，测试系统对服务器内部错误的处理和重试机制。",
		Category:          model.PresetCategoryService,
		Tags:              []string{"service", "error", "500", "internal-error"},
		Severity:          "medium",
		EstimatedDuration: 60,
		FaultConfig: &model.Fault{
			ID:         uuid.New().String(),
			Type:       model.FaultTypeAbort,
			Percentage: 20,
			Duration:   60,
			AbortConfig: &model.AbortConfig{
				HTTPStatus: 500,
				Message:    "Internal Server Error",
			},
		},
		IsBuiltin: true,
		CreatedAt:  now,
		UpdatedAt:  now,
	})

	l.presets = append(l.presets, &model.PresetScenario{
		ID:                "builtin-service-404-error",
		Name:              "资源不存在错误",
		Description:       "模拟15%的请求返回404错误，测试系统对缺失资源的优雅降级处理。",
		Category:          model.PresetCategoryService,
		Tags:              []string{"service", "error", "404", "not-found"},
		Severity:          "low",
		EstimatedDuration: 60,
		FaultConfig: &model.Fault{
			ID:         uuid.New().String(),
			Type:       model.FaultTypeAbort,
			Percentage: 15,
			Duration:   60,
			AbortConfig: &model.AbortConfig{
				HTTPStatus: 404,
				Message:    "Not Found",
			},
		},
		IsBuiltin: true,
		CreatedAt:  now,
		UpdatedAt:  now,
	})

	l.presets = append(l.presets, &model.PresetScenario{
		ID:                "builtin-database-slow-query",
		Name:              "数据库慢查询",
		Description:       "模拟数据库慢查询场景，注入2000ms延迟，测试系统在数据库性能下降时的表现。",
		Category:          model.PresetCategoryDatabase,
		Tags:              []string{"database", "slow-query", "latency"},
		Severity:          "high",
		EstimatedDuration: 120,
		FaultConfig: &model.Fault{
			ID:            uuid.New().String(),
			Type:          model.FaultTypeDelay,
			Percentage:    100,
			Duration:      120,
			DelayConfig: &model.DelayConfig{
				Distribution: model.DelayDistributionFixed,
				FixedDelay:   2000,
			},
		},
		IsBuiltin: true,
		CreatedAt:  now,
		UpdatedAt:  now,
	})

	l.presets = append(l.presets, &model.PresetScenario{
		ID:                "builtin-database-connection-failure",
		Name:              "数据库连接失败",
		Description:       "模拟数据库连接失败场景，30%的请求返回503错误，测试数据库连接池和故障转移机制。",
		Category:          model.PresetCategoryDatabase,
		Tags:              []string{"database", "connection", "failure"},
		Severity:          "critical",
		EstimatedDuration: 60,
		FaultConfig: &model.Fault{
			ID:         uuid.New().String(),
			Type:       model.FaultTypeAbort,
			Percentage: 30,
			Duration:   60,
			AbortConfig: &model.AbortConfig{
				HTTPStatus: 503,
				Message:    "Database Connection Failed",
			},
		},
		IsBuiltin: true,
		CreatedAt:  now,
		UpdatedAt:  now,
	})

	l.presets = append(l.presets, &model.PresetScenario{
		ID:                "builtin-chaos-extreme-latency",
		Name:              "极端延迟风暴",
		Description:       "混沌测试：注入极端长尾延迟（均值2000ms，最大15秒），测试系统在极端恶劣网络环境下的生存能力。",
		Category:          model.PresetCategoryChaos,
		Tags:              []string{"chaos", "extreme", "latency", "stress"},
		Severity:          "critical",
		EstimatedDuration: 180,
		FaultConfig: &model.Fault{
			ID:            uuid.New().String(),
			Type:          model.FaultTypeDelay,
			Percentage:    100,
			Duration:      180,
			DelayConfig: &model.DelayConfig{
				Distribution: model.DelayDistributionExponential,
				MeanDelay:    2000,
				MinDelay:     100,
				MaxDelay:     15000,
			},
		},
		IsBuiltin: true,
		CreatedAt:  now,
		UpdatedAt:  now,
	})

	l.presets = append(l.presets, &model.PresetScenario{
		ID:                "builtin-chaos-cascading-failure",
		Name:              "级联故障模拟",
		Description:       "混沌测试：70%的请求失败，模拟服务大规模故障场景，测试熔断和降级机制。",
		Category:          model.PresetCategoryChaos,
		Tags:              []string{"chaos", "cascading", "failure", "circuit-breaker"},
		Severity:          "critical",
		EstimatedDuration: 90,
		FaultConfig: &model.Fault{
			ID:         uuid.New().String(),
			Type:       model.FaultTypeAbort,
			Percentage: 70,
			Duration:   90,
			AbortConfig: &model.AbortConfig{
				HTTPStatus: 500,
				Message:    "Cascading Failure",
			},
		},
		IsBuiltin: true,
		CreatedAt:  now,
		UpdatedAt:  now,
	})

	l.presets = append(l.presets, &model.PresetScenario{
		ID:                "builtin-chaos-random-blend",
		Name:              "随机混合故障",
		Description:       "混沌测试：随机混合延迟和错误，50%概率注入1秒延迟，30%概率返回错误，测试系统的综合韧性。",
		Category:          model.PresetCategoryChaos,
		Tags:              []string{"chaos", "random", "mixed", "resilience"},
		Severity:          "high",
		EstimatedDuration: 180,
		FaultConfig: &model.Fault{
			ID:            uuid.New().String(),
			Type:          model.FaultTypeDelay,
			Percentage:    50,
			Duration:      180,
			DelayConfig: &model.DelayConfig{
				Distribution: model.DelayDistributionNormal,
				MeanDelay:    1000,
				StdDevDelay:  500,
				MinDelay:     100,
				MaxDelay:     5000,
			},
		},
		IsBuiltin: true,
		CreatedAt:  now,
		UpdatedAt:  now,
	})
}

func (l *Library) ListAll() []*model.PresetScenario {
	return l.presets
}

func (l *Library) ListByCategory(category model.PresetScenarioCategory) []*model.PresetScenario {
	result := make([]*model.PresetScenario, 0)
	for _, p := range l.presets {
		if p.Category == category {
			result = append(result, p)
		}
	}
	return result
}

func (l *Library) GetByID(id string) *model.PresetScenario {
	for _, p := range l.presets {
		if p.ID == id {
			return p
		}
	}
	return nil
}

func (l *Library) Search(keyword string) []*model.PresetScenario {
	result := make([]*model.PresetScenario, 0)
	for _, p := range l.presets {
		if containsKeyword(p.Name, keyword) || containsKeyword(p.Description, keyword) {
			result = append(result, p)
			continue
		}
		for _, tag := range p.Tags {
			if containsKeyword(tag, keyword) {
				result = append(result, p)
				break
			}
		}
	}
	return result
}

func containsKeyword(s, keyword string) bool {
	return len(s) >= len(keyword) && (s == keyword || len(keyword) > 0 && containsSubstring(s, keyword))
}

func containsSubstring(s, substr string) bool {
	if len(substr) == 0 {
		return true
	}
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
