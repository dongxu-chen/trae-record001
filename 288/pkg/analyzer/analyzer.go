package analyzer

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

type ProjectType string

const (
	ProjectTypeNodeJS ProjectType = "nodejs"
	ProjectTypeMaven  ProjectType = "maven"
	ProjectTypeGradle ProjectType = "gradle"
	ProjectTypePython ProjectType = "python"
	ProjectTypeGo     ProjectType = "go"
	ProjectTypeRuby   ProjectType = "ruby"
	ProjectTypePHP    ProjectType = "php"
	ProjectTypeUnknown ProjectType = "unknown"
)

type CacheableDir struct {
	Path        string
	Description string
	IsGlobal    bool
}

type DependencyFile struct {
	Path      string
	Priority  int
	IsLockFile bool
}

type ProjectInfo struct {
	Type          ProjectType
	RootDir       string
	CacheableDirs []CacheableDir
	DepFiles      []DependencyFile
}

type Analyzer struct {
	workDir string
}

func NewAnalyzer(workDir string) *Analyzer {
	return &Analyzer{workDir: workDir}
}

func (a *Analyzer) Analyze() (*ProjectInfo, error) {
	info := &ProjectInfo{
		RootDir: a.workDir,
		Type:    ProjectTypeUnknown,
	}

	detectors := []func() bool{
		func() bool { return a.detectNodeJS(info) },
		func() bool { return a.detectMaven(info) },
		func() bool { return a.detectGradle(info) },
		func() bool { return a.detectPython(info) },
		func() bool { return a.detectGo(info) },
		func() bool { return a.detectRuby(info) },
		func() bool { return a.detectPHP(info) },
	}

	for _, detect := range detectors {
		if detect() {
			break
		}
	}

	return info, nil
}

func (a *Analyzer) detectNodeJS(info *ProjectInfo) bool {
	packageJSON := filepath.Join(a.workDir, "package.json")
	if _, err := os.Stat(packageJSON); err != nil {
		return false
	}

	info.Type = ProjectTypeNodeJS
	info.CacheableDirs = []CacheableDir{
		{
			Path:        filepath.Join(a.workDir, "node_modules"),
			Description: "Node.js dependencies",
			IsGlobal:    false,
		},
		{
			Path:        getNPMCacheDir(),
			Description: "NPM global cache",
			IsGlobal:    true,
		},
		{
			Path:        getYarnCacheDir(),
			Description: "Yarn global cache",
			IsGlobal:    true,
		},
	}

	info.DepFiles = []DependencyFile{
		{Path: packageJSON, Priority: 1, IsLockFile: false},
	}

	packageLock := filepath.Join(a.workDir, "package-lock.json")
	if _, err := os.Stat(packageLock); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: packageLock, Priority: 0, IsLockFile: true})
	}

	yarnLock := filepath.Join(a.workDir, "yarn.lock")
	if _, err := os.Stat(yarnLock); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: yarnLock, Priority: 0, IsLockFile: true})
	}

	pnpmLock := filepath.Join(a.workDir, "pnpm-lock.yaml")
	if _, err := os.Stat(pnpmLock); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: pnpmLock, Priority: 0, IsLockFile: true})
	}

	return true
}

func (a *Analyzer) detectMaven(info *ProjectInfo) bool {
	pomXML := filepath.Join(a.workDir, "pom.xml")
	if _, err := os.Stat(pomXML); err != nil {
		return false
	}

	info.Type = ProjectTypeMaven
	info.CacheableDirs = []CacheableDir{
		{
			Path:        filepath.Join(a.workDir, "target"),
			Description: "Maven build output",
			IsGlobal:    false,
		},
		{
			Path:        getMavenRepoDir(),
			Description: "Maven local repository",
			IsGlobal:    true,
		},
	}

	info.DepFiles = []DependencyFile{
		{Path: pomXML, Priority: 1, IsLockFile: false},
	}

	dependencyLock := filepath.Join(a.workDir, "dependency-reduced-pom.xml")
	if _, err := os.Stat(dependencyLock); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: dependencyLock, Priority: 0, IsLockFile: true})
	}

	return true
}

func (a *Analyzer) detectGradle(info *ProjectInfo) bool {
	buildGradle := filepath.Join(a.workDir, "build.gradle")
	buildGradleKTS := filepath.Join(a.workDir, "build.gradle.kts")
	
	if _, err := os.Stat(buildGradle); err != nil {
		if _, err := os.Stat(buildGradleKTS); err != nil {
			return false
		}
	}

	info.Type = ProjectTypeGradle
	info.CacheableDirs = []CacheableDir{
		{
			Path:        filepath.Join(a.workDir, ".gradle"),
			Description: "Gradle project cache",
			IsGlobal:    false,
		},
		{
			Path:        filepath.Join(a.workDir, "build"),
			Description: "Gradle build output",
			IsGlobal:    false,
		},
		{
			Path:        getGradleHomeDir(),
			Description: "Gradle home cache",
			IsGlobal:    true,
		},
	}

	info.DepFiles = []DependencyFile{}
	if _, err := os.Stat(buildGradle); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: buildGradle, Priority: 1, IsLockFile: false})
	}
	if _, err := os.Stat(buildGradleKTS); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: buildGradleKTS, Priority: 1, IsLockFile: false})
	}

	gradleLock := filepath.Join(a.workDir, "gradle.lockfile")
	if _, err := os.Stat(gradleLock); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: gradleLock, Priority: 0, IsLockFile: true})
	}

	settingsGradle := filepath.Join(a.workDir, "settings.gradle")
	if _, err := os.Stat(settingsGradle); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: settingsGradle, Priority: 2, IsLockFile: false})
	}

	return true
}

func (a *Analyzer) detectPython(info *ProjectInfo) bool {
	requirements := filepath.Join(a.workDir, "requirements.txt")
	pyproject := filepath.Join(a.workDir, "pyproject.toml")
	poetryLock := filepath.Join(a.workDir, "poetry.lock")
	pipefile := filepath.Join(a.workDir, "Pipfile")

	hasPythonFile := false
	if _, err := os.Stat(requirements); err == nil {
		hasPythonFile = true
	}
	if _, err := os.Stat(pyproject); err == nil {
		hasPythonFile = true
	}
	if _, err := os.Stat(poetryLock); err == nil {
		hasPythonFile = true
	}
	if _, err := os.Stat(pipefile); err == nil {
		hasPythonFile = true
	}

	if !hasPythonFile {
		return false
	}

	info.Type = ProjectTypePython
	info.CacheableDirs = []CacheableDir{
		{
			Path:        filepath.Join(a.workDir, "__pycache__"),
			Description: "Python bytecode cache",
			IsGlobal:    false,
		},
		{
			Path:        filepath.Join(a.workDir, ".venv"),
			Description: "Python virtual environment",
			IsGlobal:    false,
		},
		{
			Path:        getPipCacheDir(),
			Description: "Pip cache",
			IsGlobal:    true,
		},
	}

	info.DepFiles = []DependencyFile{}
	if _, err := os.Stat(requirements); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: requirements, Priority: 1, IsLockFile: false})
	}
	if _, err := os.Stat(pyproject); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: pyproject, Priority: 1, IsLockFile: false})
	}
	if _, err := os.Stat(poetryLock); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: poetryLock, Priority: 0, IsLockFile: true})
	}
	if _, err := os.Stat(pipefile); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: pipefile, Priority: 1, IsLockFile: false})
	}

	pipefileLock := filepath.Join(a.workDir, "Pipfile.lock")
	if _, err := os.Stat(pipefileLock); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: pipefileLock, Priority: 0, IsLockFile: true})
	}

	requirementsLock := filepath.Join(a.workDir, "requirements-lock.txt")
	if _, err := os.Stat(requirementsLock); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: requirementsLock, Priority: 0, IsLockFile: true})
	}

	return true
}

func (a *Analyzer) detectGo(info *ProjectInfo) bool {
	goMod := filepath.Join(a.workDir, "go.mod")
	if _, err := os.Stat(goMod); err != nil {
		return false
	}

	info.Type = ProjectTypeGo
	info.CacheableDirs = []CacheableDir{
		{
			Path:        getGoModCacheDir(),
			Description: "Go module cache",
			IsGlobal:    true,
		},
		{
			Path:        getGoBuildCacheDir(),
			Description: "Go build cache",
			IsGlobal:    true,
		},
	}

	info.DepFiles = []DependencyFile{
		{Path: goMod, Priority: 1, IsLockFile: false},
	}

	goSum := filepath.Join(a.workDir, "go.sum")
	if _, err := os.Stat(goSum); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: goSum, Priority: 0, IsLockFile: true})
	}

	return true
}

func (a *Analyzer) detectRuby(info *ProjectInfo) bool {
	gemfile := filepath.Join(a.workDir, "Gemfile")
	if _, err := os.Stat(gemfile); err != nil {
		return false
	}

	info.Type = ProjectTypeRuby
	info.CacheableDirs = []CacheableDir{
		{
			Path:        filepath.Join(a.workDir, "vendor", "bundle"),
			Description: "Ruby bundle vendor",
			IsGlobal:    false,
		},
	}

	info.DepFiles = []DependencyFile{
		{Path: gemfile, Priority: 1, IsLockFile: false},
	}

	gemfileLock := filepath.Join(a.workDir, "Gemfile.lock")
	if _, err := os.Stat(gemfileLock); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: gemfileLock, Priority: 0, IsLockFile: true})
	}

	return true
}

func (a *Analyzer) detectPHP(info *ProjectInfo) bool {
	composerJSON := filepath.Join(a.workDir, "composer.json")
	if _, err := os.Stat(composerJSON); err != nil {
		return false
	}

	info.Type = ProjectTypePHP
	info.CacheableDirs = []CacheableDir{
		{
			Path:        filepath.Join(a.workDir, "vendor"),
			Description: "PHP Composer dependencies",
			IsGlobal:    false,
		},
		{
			Path:        getComposerCacheDir(),
			Description: "Composer cache",
			IsGlobal:    true,
		},
	}

	info.DepFiles = []DependencyFile{
		{Path: composerJSON, Priority: 1, IsLockFile: false},
	}

	composerLock := filepath.Join(a.workDir, "composer.lock")
	if _, err := os.Stat(composerLock); err == nil {
		info.DepFiles = append(info.DepFiles, DependencyFile{Path: composerLock, Priority: 0, IsLockFile: true})
	}

	return true
}

func getNPMCacheDir() string {
	if runtime.GOOS == "windows" {
		return filepath.Join(os.Getenv("APPDATA"), "npm-cache")
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".npm")
}

func getYarnCacheDir() string {
	if runtime.GOOS == "windows" {
		return filepath.Join(os.Getenv("LOCALAPPDATA"), "Yarn", "Cache")
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".cache", "yarn")
}

func getMavenRepoDir() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".m2", "repository")
}

func getGradleHomeDir() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".gradle", "caches")
}

func getPipCacheDir() string {
	if runtime.GOOS == "windows" {
		return filepath.Join(os.Getenv("LOCALAPPDATA"), "pip", "Cache")
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".cache", "pip")
}

func getGoModCacheDir() string {
	if gopath := os.Getenv("GOPATH"); gopath != "" {
		return filepath.Join(gopath, "pkg", "mod")
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, "go", "pkg", "mod")
}

func getGoBuildCacheDir() string {
	if gocache := os.Getenv("GOCACHE"); gocache != "" {
		return gocache
	}
	if runtime.GOOS == "windows" {
		return filepath.Join(os.Getenv("LOCALAPPDATA"), "go-build")
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".cache", "go-build")
}

func getComposerCacheDir() string {
	if runtime.GOOS == "windows" {
		return filepath.Join(os.Getenv("LOCALAPPDATA"), "Composer")
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".composer", "cache")
}

func (pt ProjectType) String() string {
	return string(pt)
}

func (cd CacheableDir) String() string {
	return fmt.Sprintf("%s (%s)", cd.Path, cd.Description)
}

func (info *ProjectInfo) GetSortedDepFiles() []string {
	sorted := make([]DependencyFile, len(info.DepFiles))
	copy(sorted, info.DepFiles)
	
	for i := 0; i < len(sorted); i++ {
		for j := i + 1; j < len(sorted); j++ {
			if sorted[j].Priority < sorted[i].Priority {
				sorted[i], sorted[j] = sorted[j], sorted[i]
			}
		}
	}

	result := make([]string, len(sorted))
	for i, df := range sorted {
		result[i] = df.Path
	}
	return result
}

func (info *ProjectInfo) GetLockFiles() []string {
	lockFiles := make([]string, 0)
	for _, df := range info.DepFiles {
		if df.IsLockFile {
			lockFiles = append(lockFiles, df.Path)
		}
	}
	return lockFiles
}

func (info *ProjectInfo) GetFingerprintFiles() []string {
	lockFiles := info.GetLockFiles()
	if len(lockFiles) > 0 {
		return lockFiles
	}
	return info.GetSortedDepFiles()
}

func (info *ProjectInfo) String() string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Project Type: %s\n", info.Type))
	sb.WriteString(fmt.Sprintf("Root Dir: %s\n", info.RootDir))
	sb.WriteString("Cacheable Directories:\n")
	for _, dir := range info.CacheableDirs {
		globalTag := ""
		if dir.IsGlobal {
			globalTag = " [global]"
		}
		sb.WriteString(fmt.Sprintf("  - %s: %s%s\n", dir.Description, dir.Path, globalTag))
	}
	sb.WriteString("Dependency Files:\n")
	for _, df := range info.DepFiles {
		sb.WriteString(fmt.Sprintf("  - %s (priority: %d)\n", df.Path, df.Priority))
	}
	return sb.String()
}
