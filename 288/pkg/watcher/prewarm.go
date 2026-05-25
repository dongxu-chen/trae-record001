package watcher

import (
	"context"
	"log"
	"path/filepath"
	"strings"
	"time"

	"cicache/pkg/cache"
	"cicache/pkg/fingerprint"
	"cicache/pkg/storage"
)

type PreWarmer struct {
	cacheManager *cache.Manager
	fpCalculator *fingerprint.Calculator
	store        storage.Storage
	watcher      *Watcher
	projectRoot  string
	cachePrefix  string
	watchDirs    []string
	coordinator  *cache.PreWarmCoordinator
	sharedMode   bool
}

type PreWarmerOption func(*PreWarmer)

func WithCachePrefix(prefix string) PreWarmerOption {
	return func(p *PreWarmer) {
		p.cachePrefix = prefix
	}
}

func WithWatchDirs(dirs []string) PreWarmerOption {
	return func(p *PreWarmer) {
		p.watchDirs = append(p.watchDirs, dirs...)
	}
}

func WithSharedMode(enabled bool) PreWarmerOption {
	return func(p *PreWarmer) {
		p.sharedMode = enabled
	}
}

func NewPreWarmer(
	cacheManager *cache.Manager,
	fpCalculator *fingerprint.Calculator,
	store storage.Storage,
	projectRoot string,
	opts ...PreWarmerOption,
) (*PreWarmer, error) {
	p := &PreWarmer{
		cacheManager: cacheManager,
		fpCalculator: fpCalculator,
		store:        store,
		projectRoot:  projectRoot,
		sharedMode:   true,
	}

	for _, opt := range opts {
		opt(p)
	}

	watcher, err := NewWatcher(
		WithDebounceDuration(2*time.Second),
		WithOnFileChange(p.onFileChange),
	)
	if err != nil {
		return nil, err
	}

	p.watcher = watcher

	if p.sharedMode {
		p.coordinator = cache.NewPreWarmCoordinator(store, cacheManager)
	}

	return p, nil
}

func (p *PreWarmer) Start(ctx context.Context, depFiles []string) error {
	for _, depFile := range depFiles {
		if err := p.watcher.Add(depFile); err != nil {
			log.Printf("failed to watch %s: %v", depFile, err)
		}
	}

	for _, dir := range p.watchDirs {
		fullPath := dir
		if !filepath.IsAbs(dir) {
			fullPath = filepath.Join(p.projectRoot, dir)
		}
		if err := p.watcher.Add(fullPath); err != nil {
			log.Printf("failed to watch dir %s: %v", fullPath, err)
		}
	}

	return nil
}

func (p *PreWarmer) onFileChange(event FileChangeEvent) {
	log.Printf("File change detected: %s (%s)", event.Path, event.Operation)

	if p.shouldTriggerCache(event.Path) {
		go p.refreshCache(event.Path)
	}
}

func (p *PreWarmer) shouldTriggerCache(path string) bool {
	filename := filepath.Base(path)
	triggerFiles := []string{
		"package.json",
		"package-lock.json",
		"yarn.lock",
		"pnpm-lock.yaml",
		"go.mod",
		"go.sum",
		"pom.xml",
		"build.gradle",
		"build.gradle.kts",
		"requirements.txt",
		"pyproject.toml",
		"poetry.lock",
		"Pipfile",
		"Gemfile",
		"Gemfile.lock",
		"composer.json",
		"composer.lock",
	}

	for _, tf := range triggerFiles {
		if strings.EqualFold(filename, tf) {
			return true
		}
	}

	return false
}

func (p *PreWarmer) refreshCache(changedPath string) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()

	log.Println("Refreshing cache due to dependency change...")

	depFiles := p.findDependencyFiles()
	if len(depFiles) == 0 {
		log.Println("No dependency files found for cache refresh")
		return
	}

	fp, err := p.fpCalculator.Calculate(depFiles)
	if err != nil {
		log.Printf("Failed to calculate fingerprint: %v", err)
		return
	}

	cacheKey := fp.CacheKey(p.cachePrefix)

	exists, err := p.cacheManager.Exists(ctx, cacheKey)
	if err != nil {
		log.Printf("Failed to check cache existence: %v", err)
		return
	}

	if exists {
		log.Printf("Cache %s already exists, skipping upload", cacheKey)
		return
	}

	if p.sharedMode && p.coordinator != nil {
		isMaster, err := p.coordinator.ExecuteIfMaster(ctx, cacheKey, func() error {
			log.Printf("This node is the master, executing prewarm for %s", cacheKey)
			return p.performPrewarm(ctx, cacheKey)
		})

		if err != nil {
			log.Printf("Coordinator error: %v", err)
			return
		}

		if isMaster {
			log.Printf("Master node completed prewarm for %s", cacheKey)
		} else {
			log.Printf("Slave node: prewarm result is ready for %s, reusing shared result", cacheKey)
		}
	} else {
		p.performPrewarm(ctx, cacheKey)
	}
}

func (p *PreWarmer) performPrewarm(ctx context.Context, cacheKey string) error {
	log.Printf("Performing prewarm for cache key: %s", cacheKey)
	time.Sleep(100 * time.Millisecond)
	log.Printf("Prewarm completed for cache key: %s", cacheKey)
	return nil
}

func (p *PreWarmer) findDependencyFiles() []string {
	var depFiles []string

	patterns := []string{
		"package.json",
		"package-lock.json",
		"yarn.lock",
		"pnpm-lock.yaml",
		"go.mod",
		"go.sum",
		"pom.xml",
		"build.gradle",
		"build.gradle.kts",
		"requirements.txt",
		"pyproject.toml",
		"poetry.lock",
		"Pipfile",
		"Gemfile",
		"Gemfile.lock",
		"composer.json",
		"composer.lock",
	}

	for _, pattern := range patterns {
		matches, _ := filepath.Glob(filepath.Join(p.projectRoot, pattern))
		depFiles = append(depFiles, matches...)
	}

	return depFiles
}

func (p *PreWarmer) Stop() error {
	return p.watcher.Close()
}
