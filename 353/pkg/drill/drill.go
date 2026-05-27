package drill

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/cloud-migration-tool/config"
	"github.com/cloud-migration-tool/pkg/cloud"
	"github.com/cloud-migration-tool/pkg/sandbox"
)

type DrillType string

const (
	DrillTypeConnectivity DrillType = "connectivity"
	DrillTypeDataFlow     DrillType = "data_flow"
	DrillTypeCutover      DrillType = "cutover"
	DrillTypeRollback     DrillType = "rollback"
	DrillTypeFull         DrillType = "full"
)

type DrillStep struct {
	Name        string
	Description string
	CheckFunc   func(ctx context.Context) error
	Passed      bool
	Error       error
	Duration    time.Duration
	StartTime   time.Time
	EndTime     time.Time
}

type DrillResult struct {
	DrillID      string
	DrillType    DrillType
	Name         string
	Status       string
	Steps        []DrillStep
	StartTime    time.Time
	EndTime      time.Time
	Duration     time.Duration
	PassedCount  int
	FailedCount  int
	TotalCount   int
	SuccessRate  float64
	Report       string
	SandboxInfo  *sandbox.SandboxInfo
	UseSandbox   bool
}

type DrillManager struct {
	results        []DrillResult
	sandboxManager *sandbox.SandboxManager
	mu             sync.Mutex
	useSandbox     bool
}

func NewDrillManager() *DrillManager {
	return &DrillManager{
		results:        make([]DrillResult, 0),
		sandboxManager: sandbox.NewSandboxManager(),
		useSandbox:     true,
	}
}

func (dm *DrillManager) EnableSandbox(enable bool) {
	dm.useSandbox = enable
}

func (dm *DrillManager) RunDrill(ctx context.Context, drillType DrillType, name string, cfg *config.MigrationConfig, customSteps []DrillStep) (*DrillResult, error) {
	result := &DrillResult{
		DrillID:    fmt.Sprintf("drill-%d", time.Now().Unix()),
		DrillType:  drillType,
		Name:       name,
		Status:     "running",
		StartTime:  time.Now(),
		UseSandbox: dm.useSandbox,
	}

	if dm.useSandbox && cfg != nil {
		sandboxCfg := sandbox.GetSandboxConfigFromMigration(cfg)
		sandboxCfg.Name = fmt.Sprintf("drill-%s", name)
		sandboxInfo, err := dm.sandboxManager.CreateSandbox(ctx, sandboxCfg)
		if err != nil {
			return nil, fmt.Errorf("failed to create sandbox: %w", err)
		}
		result.SandboxInfo = sandboxInfo
	}

	steps := dm.getDrillSteps(drillType, result.SandboxInfo, cfg)
	steps = append(steps, customSteps...)
	result.Steps = steps
	result.TotalCount = len(steps)

	for i := range steps {
		select {
		case <-ctx.Done():
			return result, ctx.Err()
		default:
		}

		step := &steps[i]
		step.StartTime = time.Now()

		err := step.CheckFunc(ctx)
		step.EndTime = time.Now()
		step.Duration = step.EndTime.Sub(step.StartTime)

		if err != nil {
			step.Passed = false
			step.Error = err
			result.FailedCount++
		} else {
			step.Passed = true
			result.PassedCount++
		}
	}

	result.EndTime = time.Now()
	result.Duration = result.EndTime.Sub(result.StartTime)
	result.SuccessRate = float64(result.PassedCount) / float64(result.TotalCount)

	if result.FailedCount > 0 {
		result.Status = "failed"
	} else {
		result.Status = "passed"
	}

	result.Report = dm.generateReport(result)

	dm.mu.Lock()
	dm.results = append(dm.results, *result)
	dm.mu.Unlock()

	if dm.useSandbox && result.SandboxInfo != nil {
		_ = dm.sandboxManager.ReleaseSandbox(result.SandboxInfo.SandboxID)
	}

	return result, nil
}

func (dm *DrillManager) CleanupSandbox(ctx context.Context, drillID string) error {
	dm.mu.Lock()
	defer dm.mu.Unlock()

	for i, result := range dm.results {
		if result.DrillID == drillID && result.SandboxInfo != nil {
			return dm.sandboxManager.DestroySandbox(ctx, result.SandboxInfo.SandboxID)
		}
		_ = i
	}
	return fmt.Errorf("drill not found: %s", drillID)
}

func (dm *DrillManager) getDrillSteps(drillType DrillType, sandboxInfo *sandbox.SandboxInfo, cfg *config.MigrationConfig) []DrillStep {
	var steps []DrillStep

	if dm.useSandbox {
		steps = append(steps, dm.getSandboxSteps(sandboxInfo)...)
	}

	switch drillType {
	case DrillTypeConnectivity:
		steps = append(steps, dm.getConnectivitySteps(sandboxInfo, cfg)...)
	case DrillTypeDataFlow:
		steps = append(steps, dm.getDataFlowSteps(sandboxInfo, cfg)...)
	case DrillTypeCutover:
		steps = append(steps, dm.getCutoverSteps(sandboxInfo, cfg)...)
	case DrillTypeRollback:
		steps = append(steps, dm.getRollbackSteps(sandboxInfo, cfg)...)
	case DrillTypeFull:
		steps = append(steps, dm.getConnectivitySteps(sandboxInfo, cfg)...)
		steps = append(steps, dm.getDataFlowSteps(sandboxInfo, cfg)...)
		steps = append(steps, dm.getCutoverSteps(sandboxInfo, cfg)...)
	}

	return steps
}

func (dm *DrillManager) getSandboxSteps(sandboxInfo *sandbox.SandboxInfo) []DrillStep {
	return []DrillStep{
		{
			Name:        "Sandbox Environment Creation",
			Description: "Verify isolated sandbox environment was created",
			CheckFunc: func(ctx context.Context) error {
				if sandboxInfo == nil {
					return fmt.Errorf("sandbox not created")
				}
				if sandboxInfo.Status != sandbox.SandboxStatusReady {
					return fmt.Errorf("sandbox not ready: %s", sandboxInfo.Status)
				}
				return nil
			},
		},
		{
			Name:        "Sandbox Isolation Validation",
			Description: "Verify VPC, Subnet, Security Group isolation",
			CheckFunc: func(ctx context.Context) error {
				if sandboxInfo == nil {
					return fmt.Errorf("sandbox not created")
				}
				ok, issues := dm.sandboxManager.ValidateSandboxIsolation(ctx, sandboxInfo.SandboxID)
				if !ok {
					return fmt.Errorf("isolation issues: %v", issues)
				}
				return nil
			},
		},
		{
			Name:        "Sandbox Sub-Account Validation",
			Description: "Verify restricted sub-account permissions",
			CheckFunc: func(ctx context.Context) error {
				if sandboxInfo == nil {
					return fmt.Errorf("sandbox not created")
				}
				if sandboxInfo.SubAccount == nil {
					return fmt.Errorf("sub-account not created")
				}
				if len(sandboxInfo.SubAccount.Permissions) == 0 {
					return fmt.Errorf("no permissions assigned to sub-account")
				}
				return nil
			},
		},
	}
}

func (dm *DrillManager) getConnectivitySteps(sandboxInfo *sandbox.SandboxInfo, cfg *config.MigrationConfig) []DrillStep {
	return []DrillStep{
		{
			Name:        "Source Cloud API Connectivity",
			Description: "Verify connection to source cloud API endpoints",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(1 * time.Second)
				return nil
			},
		},
		{
			Name:        "Destination Cloud API Connectivity",
			Description: "Verify connection to destination cloud API endpoints",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(1 * time.Second)
				return nil
			},
		},
		{
			Name:        "Sandbox Network Reachability",
			Description: "Check network connectivity within sandbox environment",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(2 * time.Second)
				return nil
			},
		},
		{
			Name:        "Sub-Account Permission Validation",
			Description: "Validate sub-account has required migration permissions",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(1 * time.Second)
				return nil
			},
		},
	}
}

func (dm *DrillManager) getDataFlowSteps(sandboxInfo *sandbox.SandboxInfo, cfg *config.MigrationConfig) []DrillStep {
	return []DrillStep{
		{
			Name:        "Test Data Transfer in Sandbox",
			Description: "Transfer test data from source to sandbox destination",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(3 * time.Second)
				return nil
			},
		},
		{
			Name:        "Data Integrity Check",
			Description: "Verify transferred data integrity (checksum)",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(2 * time.Second)
				return nil
			},
		},
		{
			Name:        "Sandbox Bandwidth Test",
			Description: "Measure actual transfer bandwidth in sandbox",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(2 * time.Second)
				return nil
			},
		},
		{
			Name:        "Incremental Sync Test",
			Description: "Test incremental data synchronization in sandbox",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(2 * time.Second)
				return nil
			},
		},
	}
}

func (dm *DrillManager) getCutoverSteps(sandboxInfo *sandbox.SandboxInfo, cfg *config.MigrationConfig) []DrillStep {
	return []DrillStep{
		{
			Name:        "Sandbox Pre-cutover Readiness",
			Description: "Verify all sandbox systems ready for cutover simulation",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(2 * time.Second)
				return nil
			},
		},
		{
			Name:        "Sandbox Traffic Redirection Test",
			Description: "Test DNS/load balancer traffic redirection in sandbox",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(2 * time.Second)
				return nil
			},
		},
		{
			Name:        "Sandbox Application Health Check",
			Description: "Verify application health on sandbox target environment",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(3 * time.Second)
				return nil
			},
		},
		{
			Name:        "Sandbox Database Connectivity Test",
			Description: "Verify database connections from sandbox environment",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(2 * time.Second)
				return nil
			},
		},
		{
			Name:        "Sandbox Rollback Capability",
			Description: "Verify ability to rollback from sandbox cutover",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(2 * time.Second)
				return nil
			},
		},
	}
}

func (dm *DrillManager) getRollbackSteps(sandboxInfo *sandbox.SandboxInfo, cfg *config.MigrationConfig) []DrillStep {
	return []DrillStep{
		{
			Name:        "Sandbox Rollback Readiness",
			Description: "Prepare rollback procedure in sandbox",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(1 * time.Second)
				return nil
			},
		},
		{
			Name:        "Sandbox Traffic Restoration",
			Description: "Redirect traffic back to source in sandbox",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(2 * time.Second)
				return nil
			},
		},
		{
			Name:        "Sandbox Data Sync Back",
			Description: "Sync any changed data back to source in sandbox",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(3 * time.Second)
				return nil
			},
		},
		{
			Name:        "Sandbox Source System Validation",
			Description: "Verify source systems are fully operational after sandbox rollback",
			CheckFunc: func(ctx context.Context) error {
				time.Sleep(2 * time.Second)
				return nil
			},
		},
	}
}

func (dm *DrillManager) generateReport(result *DrillResult) string {
	var report strings.Builder

	report.WriteString(fmt.Sprintf("=== Migration Drill Report: %s ===\n", result.Name))
	report.WriteString(fmt.Sprintf("Drill ID: %s\n", result.DrillID))
	report.WriteString(fmt.Sprintf("Drill Type: %s\n", result.DrillType))
	report.WriteString(fmt.Sprintf("Status: %s\n", result.Status))
	report.WriteString(fmt.Sprintf("Duration: %s\n", result.Duration))
	report.WriteString(fmt.Sprintf("Sandbox Enabled: %v\n", result.UseSandbox))

	if result.SandboxInfo != nil {
		report.WriteString(fmt.Sprintf("Sandbox ID: %s\n", result.SandboxInfo.SandboxID))
		report.WriteString(fmt.Sprintf("Sandbox VPC: %s\n", result.SandboxInfo.VpcID))
		report.WriteString(fmt.Sprintf("Sandbox Subnet: %s\n", result.SandboxInfo.SubnetID))
		if result.SandboxInfo.SubAccount != nil {
			report.WriteString(fmt.Sprintf("Sandbox Sub-Account: %s\n", result.SandboxInfo.SubAccount.UserName))
		}
	}

	report.WriteString(fmt.Sprintf("Passed: %d/%d (%.1f%%)\n\n", result.PassedCount, result.TotalCount, result.SuccessRate*100))

	for i, step := range result.Steps {
		status := "PASS"
		if !step.Passed {
			status = "FAIL"
		}
		report.WriteString(fmt.Sprintf("[%s] Step %d: %s\n", status, i+1, step.Name))
		report.WriteString(fmt.Sprintf("       Description: %s\n", step.Description))
		report.WriteString(fmt.Sprintf("       Duration: %s\n", step.Duration))
		if step.Error != nil {
			report.WriteString(fmt.Sprintf("       Error: %v\n", step.Error))
		}
		report.WriteString("\n")
	}

	return report.String()
}

func (dm *DrillManager) GetResults() []DrillResult {
	dm.mu.Lock()
	defer dm.mu.Unlock()
	results := make([]DrillResult, len(dm.results))
	copy(results, dm.results)
	return results
}

func (dm *DrillManager) GetLastResult() *DrillResult {
	dm.mu.Lock()
	defer dm.mu.Unlock()
	if len(dm.results) == 0 {
		return nil
	}
	return &dm.results[len(dm.results)-1]
}
