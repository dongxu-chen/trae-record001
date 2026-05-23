package dependency

import (
	"encoding/json"
	"fmt"
	"os/exec"
	"sort"
	"strings"
)

type Package struct {
	Name        string   `json:"name"`
	Version     string   `json:"version"`
	License     string   `json:"license"`
	Source      string   `json:"source"`
	DependsOn   []string `json:"depends_on"`
	DependedBy  []string `json:"depended_by"`
	Layer       string   `json:"layer"`
	Vulnerabilities []string `json:"vulnerabilities"`
}

type DependencyTree struct {
	Package
	Children []*DependencyTree `json:"children"`
}

type LicenseRisk string

const (
	LicenseRiskHigh   LicenseRisk = "HIGH"
	LicenseRiskMedium LicenseRisk = "MEDIUM"
	LicenseRiskLow    LicenseRisk = "LOW"
	LicenseRiskUnknown LicenseRisk = "UNKNOWN"
)

type LicenseInfo struct {
	Name        string      `json:"name"`
	SPDXID      string      `json:"spdx_id"`
	RiskLevel   LicenseRisk `json:"risk_level"`
	Description string      `json:"description"`
	Restrictions string     `json:"restrictions"`
}

type DependencyAnalysis struct {
	Packages        []Package
	DependencyTree  *DependencyTree
	LicenseSummary  map[string]int
	LicenseRisks    map[string][]LicenseInfo
	TotalPackages   int
	UniqueLicenses  int
	HighRiskLicenses int
}

var licenseDatabase = map[string]LicenseInfo{
	"MIT": {
		Name:        "MIT License",
		SPDXID:      "MIT",
		RiskLevel:   LicenseRiskLow,
		Description: "宽松的开源许可证",
		Restrictions: "需保留版权声明",
	},
	"Apache-2.0": {
		Name:        "Apache License 2.0",
		SPDXID:      "Apache-2.0",
		RiskLevel:   LicenseRiskLow,
		Description: "宽松的开源许可证",
		Restrictions: "需声明修改、保留版权",
	},
	"BSD-2-Clause": {
		Name:        "BSD 2-Clause License",
		SPDXID:      "BSD-2-Clause",
		RiskLevel:   LicenseRiskLow,
		Description: "宽松的开源许可证",
		Restrictions: "需保留版权声明",
	},
	"BSD-3-Clause": {
		Name:        "BSD 3-Clause License",
		SPDXID:      "BSD-3-Clause",
		RiskLevel:   LicenseRiskLow,
		Description: "宽松的开源许可证",
		Restrictions: "需保留版权声明，不得使用作者名义推广",
	},
	"GPL-2.0": {
		Name:        "GNU General Public License v2.0",
		SPDXID:      "GPL-2.0",
		RiskLevel:   LicenseRiskHigh,
		Description: "强copyleft许可证",
		Restrictions: "衍生作品必须以相同许可证开源",
	},
	"GPL-3.0": {
		Name:        "GNU General Public License v3.0",
		SPDXID:      "GPL-3.0",
		RiskLevel:   LicenseRiskHigh,
		Description: "强copyleft许可证",
		Restrictions: "衍生作品必须以相同许可证开源",
	},
	"LGPL-2.1": {
		Name:        "GNU Lesser General Public License v2.1",
		SPDXID:      "LGPL-2.1",
		RiskLevel:   LicenseRiskMedium,
		Description: "弱copyleft许可证",
		Restrictions: "库修改需开源，静态链接需开源",
	},
	"LGPL-3.0": {
		Name:        "GNU Lesser General Public License v3.0",
		SPDXID:      "LGPL-3.0",
		RiskLevel:   LicenseRiskMedium,
		Description: "弱copyleft许可证",
		Restrictions: "库修改需开源",
	},
	"AGPL-3.0": {
		Name:        "GNU Affero General Public License v3.0",
		SPDXID:      "AGPL-3.0",
		RiskLevel:   LicenseRiskHigh,
		Description: "网络服务copyleft许可证",
		Restrictions: "网络服务也需开源",
	},
	"MPL-2.0": {
		Name:        "Mozilla Public License 2.0",
		SPDXID:      "MPL-2.0",
		RiskLevel:   LicenseRiskMedium,
		Description: "弱copyleft许可证",
		Restrictions: "修改的文件需开源",
	},
	"CDDL-1.0": {
		Name:        "Common Development and Distribution License",
		SPDXID:      "CDDL-1.0",
		RiskLevel:   LicenseRiskMedium,
		Description: "GPL不兼容许可证",
		Restrictions: "修改的文件需开源",
	},
	"Proprietary": {
		Name:        "专有软件",
		SPDXID:      "Proprietary",
		RiskLevel:   LicenseRiskHigh,
		Description: "专有软件许可证",
		Restrictions: "需审查许可条款",
	},
}

type DependencyAnalyzer struct {
	trivyPath string
}

func NewDependencyAnalyzer(trivyPath string) *DependencyAnalyzer {
	return &DependencyAnalyzer{trivyPath: trivyPath}
}

func (a *DependencyAnalyzer) Analyze(imageName string) (*DependencyAnalysis, error) {
	cmd := exec.Command(a.trivyPath, "image", "--format", "json", "--list-all-pkgs", imageName)
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to analyze dependencies: %w", err)
	}

	var result struct {
		Results []struct {
			Target string `json:"Target"`
			Type   string `json:"Type"`
			Packages []struct {
				Name    string `json:"Name"`
				Version string `json:"Version"`
				License string `json:"License"`
				Source  string `json:"SrcName"`
			} `json:"Packages"`
		} `json:"Results"`
	}

	if err := json.Unmarshal(output, &result); err != nil {
		return nil, fmt.Errorf("failed to parse dependency data: %w", err)
	}

	analysis := &DependencyAnalysis{
		Packages:       make([]Package, 0),
		LicenseSummary: make(map[string]int),
		LicenseRisks:   make(map[string][]LicenseInfo),
	}

	packageMap := make(map[string]*Package)

	for _, res := range result.Results {
		for _, pkg := range res.Packages {
			license := strings.TrimSpace(pkg.License)
			if license == "" {
				license = "Unknown"
			}

			p := Package{
				Name:     pkg.Name,
				Version:  pkg.Version,
				License:  license,
				Source:   pkg.Source,
				Layer:    res.Target,
			}

			analysis.Packages = append(analysis.Packages, p)
			packageMap[pkg.Name+"@"+pkg.Version] = &p

			analysis.LicenseSummary[license]++
			licenseInfo := getLicenseInfo(license)
			analysis.LicenseRisks[string(licenseInfo.RiskLevel)] = append(
				analysis.LicenseRisks[string(licenseInfo.RiskLevel)], licenseInfo)
			
			if licenseInfo.RiskLevel == LicenseRiskHigh {
				analysis.HighRiskLicenses++
			}
		}
	}

	analysis.TotalPackages = len(analysis.Packages)
	analysis.UniqueLicenses = len(analysis.LicenseSummary)
	analysis.DependencyTree = buildDependencyTree(analysis.Packages)

	return analysis, nil
}

func getLicenseInfo(license string) LicenseInfo {
	normalized := normalizeLicense(license)
	if info, ok := licenseDatabase[normalized]; ok {
		return info
	}
	return LicenseInfo{
		Name:        license,
		SPDXID:      license,
		RiskLevel:   LicenseRiskUnknown,
		Description: "未知许可证",
		Restrictions: "需人工审查",
	}
}

func normalizeLicense(license string) string {
	license = strings.TrimSpace(license)
	license = strings.TrimPrefix(license, "(")
	license = strings.TrimSuffix(license, ")")
	license = strings.ReplaceAll(license, " ", "-")
	
	for known := range licenseDatabase {
		if strings.HasPrefix(strings.ToUpper(license), strings.ToUpper(known)) {
			return known
		}
	}
	
	return license
}

func buildDependencyTree(packages []Package) *DependencyTree {
	if len(packages) == 0 {
		return nil
	}

	sort.Slice(packages, func(i, j int) bool {
		return packages[i].Name < packages[j].Name
	})

	root := &DependencyTree{
		Package: Package{Name: "root", Version: "virtual"},
	}

	nodeMap := make(map[string]*DependencyTree)
	for _, pkg := range packages {
		node := &DependencyTree{
			Package: pkg,
		}
		nodeMap[pkg.Name+"@"+pkg.Version] = node
		root.Children = append(root.Children, node)
	}

	return root
}

func (a *DependencyAnalysis) GetPackagesByLicense(license string) []Package {
	var result []Package
	for _, pkg := range a.Packages {
		if strings.EqualFold(pkg.License, license) {
			result = append(result, pkg)
		}
	}
	return result
}

func (a *DependencyAnalysis) GetHighRiskLicenses() []LicenseInfo {
	return a.LicenseRisks[string(LicenseRiskHigh)]
}

func (a *DependencyAnalysis) PrintDependencyTree(maxDepth int) string {
	var sb strings.Builder
	printTree(a.DependencyTree, 0, maxDepth, &sb)
	return sb.String()
}

func printTree(node *DependencyTree, depth, maxDepth int, sb *strings.Builder) {
	if depth > maxDepth && maxDepth > 0 {
		return
	}

	indent := strings.Repeat("  ", depth)
	if node.Name != "root" {
		sb.WriteString(fmt.Sprintf("%s%s@%s (%s)\n", indent, node.Name, node.Version, node.License))
	}

	for _, child := range node.Children {
		printTree(child, depth+1, maxDepth, sb)
	}
}

func (a *DependencyAnalysis) Summary() string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("\n依赖分析汇总:\n"))
	sb.WriteString(fmt.Sprintf("  软件包总数: %d\n", a.TotalPackages))
	sb.WriteString(fmt.Sprintf("  许可证种类: %d\n", a.UniqueLicenses))
	sb.WriteString(fmt.Sprintf("  高风险许可证: %d\n", a.HighRiskLicenses))

	sb.WriteString("\n  许可证分布:\n")
	for license, count := range a.LicenseSummary {
		info := getLicenseInfo(license)
		riskMarker := ""
		switch info.RiskLevel {
		case LicenseRiskHigh:
			riskMarker = " ⚠️"
		case LicenseRiskMedium:
			riskMarker = " 📝"
		}
		sb.WriteString(fmt.Sprintf("    %s: %d%s\n", license, count, riskMarker))
	}

	return sb.String()
}

func (a *DependencyAnalysis) LicenseComplianceReport() []string {
	var issues []string
	
	if a.HighRiskLicenses > 0 {
		issues = append(issues, fmt.Sprintf("发现 %d 个高风险许可证，需立即审查", a.HighRiskLicenses))
		for _, lic := range a.GetHighRiskLicenses() {
			issues = append(issues, fmt.Sprintf("  - %s: %s", lic.SPDXID, lic.Restrictions))
		}
	}

	if a.LicenseRisks[string(LicenseRiskUnknown)] != nil {
		issues = append(issues, fmt.Sprintf("发现 %d 个未知许可证，需人工审查", 
			len(a.LicenseRisks[string(LicenseRiskUnknown)])))
	}

	return issues
}
