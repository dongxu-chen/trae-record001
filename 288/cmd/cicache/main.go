package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"cicache/configs"
	"cicache/pkg/analyzer"
	"cicache/pkg/cache"
	"cicache/pkg/fingerprint"
	"cicache/pkg/storage"
	"cicache/pkg/watcher"

	"github.com/spf13/cobra"
)

var (
	cfgFile      string
	verbose      bool
	cacheKey     string
	cachePrefix  string
	includeDirs  []string
	excludeDirs  []string
	storageType  string
	storageEndpoint string
	storageBucket string
	storageRegion string
	storageAccessKey string
	storageSecretKey string
)

var rootCmd = &cobra.Command{
	Use:   "cicache",
	Short: "CI Pipeline Cache Accelerator",
	Long:  `A tool to accelerate CI pipelines by caching dependencies and build artifacts with intelligent fingerprinting.`,
	PersistentPreRun: func(cmd *cobra.Command, args []string) {
		if verbose {
			log.SetFlags(log.LstdFlags | log.Lshortfile)
		}
	},
}

var analyzeCmd = &cobra.Command{
	Use:   "analyze",
	Short: "Analyze project and detect cacheable directories",
	Run:   runAnalyze,
}

var saveCmd = &cobra.Command{
	Use:   "save [path]",
	Short: "Save directory to cache",
	Args:  cobra.ExactArgs(1),
	Run:   runSave,
}

var restoreCmd = &cobra.Command{
	Use:   "restore [target]",
	Short: "Restore cache to directory",
	Args:  cobra.MaximumNArgs(1),
	Run:   runRestore,
}

var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List all cached items",
	Run:   runList,
}

var deleteCmd = &cobra.Command{
	Use:   "delete [key]",
	Short: "Delete a cached item",
	Args:  cobra.ExactArgs(1),
	Run:   runDelete,
}

var clearCmd = &cobra.Command{
	Use:   "clear",
	Short: "Clear all local cache",
	Run:   runClear,
}

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show cache status",
	Run:   runStatus,
}

var watchCmd = &cobra.Command{
	Use:   "watch",
	Short: "Watch for file changes and prewarm cache",
	Run:   runWatch,
}

var fingerprintCmd = &cobra.Command{
	Use:   "fingerprint [files...]",
	Short: "Calculate fingerprint for files",
	Args:  cobra.MinimumNArgs(1),
	Run:   runFingerprint,
}

var analyticsCmd = &cobra.Command{
	Use:   "analytics",
	Short: "Show cache hit analytics",
	Run:   runAnalytics,
}

var prefetchCmd = &cobra.Command{
	Use:   "prefetch",
	Short: "Predict and prefetch cache items",
	Run:   runPrefetch,
}

var shareFindCmd = &cobra.Command{
	Use:   "find",
	Short: "Find similar cache entries for sharing",
	Run:   runShareFind,
}

var shareRegisterCmd = &cobra.Command{
	Use:   "register [cacheKey]",
	Short: "Register cache for cross-project sharing",
	Args:  cobra.ExactArgs(1),
	Run:   runShareRegister,
}

var shareCmd = &cobra.Command{
	Use:   "share",
	Short: "Cross-project cache sharing commands",
}

func init() {
	rootCmd.PersistentFlags().StringVarP(&cfgFile, "config", "c", "", "config file path")
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")

	saveCmd.Flags().StringVarP(&cacheKey, "key", "k", "", "cache key (default: auto-generated fingerprint)")
	saveCmd.Flags().StringVarP(&cachePrefix, "prefix", "p", "", "cache key prefix")
	saveCmd.Flags().StringSliceVar(&includeDirs, "include", nil, "include directories")
	saveCmd.Flags().StringSliceVar(&excludeDirs, "exclude", nil, "exclude patterns")

	restoreCmd.Flags().StringVarP(&cacheKey, "key", "k", "", "cache key to restore")
	restoreCmd.Flags().StringVarP(&cachePrefix, "prefix", "p", "", "cache key prefix")

	deleteCmd.Flags().BoolP("force", "f", false, "force delete without confirmation")

	rootCmd.AddCommand(analyzeCmd)
	rootCmd.AddCommand(saveCmd)
	rootCmd.AddCommand(restoreCmd)
	rootCmd.AddCommand(listCmd)
	rootCmd.AddCommand(deleteCmd)
	rootCmd.AddCommand(clearCmd)
	rootCmd.AddCommand(statusCmd)
	rootCmd.AddCommand(watchCmd)
	rootCmd.AddCommand(fingerprintCmd)
	rootCmd.AddCommand(analyticsCmd)
	rootCmd.AddCommand(prefetchCmd)
	rootCmd.AddCommand(shareCmd)
	shareCmd.AddCommand(shareFindCmd)
	shareCmd.AddCommand(shareRegisterCmd)

	rootCmd.PersistentFlags().StringVar(&storageType, "storage-type", "", "storage type (local/s3)")
	rootCmd.PersistentFlags().StringVar(&storageEndpoint, "storage-endpoint", "", "storage endpoint")
	rootCmd.PersistentFlags().StringVar(&storageBucket, "storage-bucket", "", "storage bucket")
	rootCmd.PersistentFlags().StringVar(&storageRegion, "storage-region", "", "storage region")
	rootCmd.PersistentFlags().StringVar(&storageAccessKey, "storage-access-key", "", "storage access key")
	rootCmd.PersistentFlags().StringVar(&storageSecretKey, "storage-secret-key", "", "storage secret key")
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func loadConfig() *configs.Config {
	cfg := configs.DefaultConfig()

	if cfgFile != "" {
		loaded, err := configs.LoadConfig(cfgFile)
		if err == nil {
			cfg = loaded
		} else if verbose {
			log.Printf("Warning: could not load config: %v", err)
		}
	}

	if storageType != "" {
		cfg.Storage.Type = storageType
	}
	if storageEndpoint != "" {
		cfg.Storage.Endpoint = storageEndpoint
	}
	if storageBucket != "" {
		cfg.Storage.Bucket = storageBucket
	}
	if storageRegion != "" {
		cfg.Storage.Region = storageRegion
	}
	if storageAccessKey != "" {
		cfg.Storage.AccessKey = storageAccessKey
	}
	if storageSecretKey != "" {
		cfg.Storage.SecretKey = storageSecretKey
	}

	if cachePrefix != "" {
		cfg.Cache.KeyPrefix = cachePrefix
	}

	return cfg
}

func createStorage(cfg *configs.Config) (storage.Storage, error) {
	return storage.NewStorage(storage.Config{
		Type:      cfg.Storage.Type,
		Endpoint:  cfg.Storage.Endpoint,
		Bucket:    cfg.Storage.Bucket,
		Region:    cfg.Storage.Region,
		AccessKey: cfg.Storage.AccessKey,
		SecretKey: cfg.Storage.SecretKey,
		UseSSL:    cfg.Storage.UseSSL,
		BasePath:  cfg.Storage.BasePath,
	})
}

func createCacheManager(cfg *configs.Config, store storage.Storage, useTiered bool) (*cache.Manager, error) {
	maxSize := parseSize(cfg.Cache.MaxSize)
	opts := []cache.ManagerOption{
		cache.WithMaxCacheSize(maxSize),
		cache.WithTieredCache(useTiered),
	}
	if cfg.Cache.CacheDir != "" {
		opts = append(opts, cache.WithCacheDir(cfg.Cache.CacheDir))
	}
	return cache.NewManager(store, opts...)
}

func parseSize(sizeStr string) int64 {
	sizeStr = strings.ToUpper(sizeStr)
	multiplier := int64(1)

	if strings.HasSuffix(sizeStr, "GB") {
		multiplier = 1024 * 1024 * 1024
		sizeStr = strings.TrimSuffix(sizeStr, "GB")
	} else if strings.HasSuffix(sizeStr, "MB") {
		multiplier = 1024 * 1024
		sizeStr = strings.TrimSuffix(sizeStr, "MB")
	} else if strings.HasSuffix(sizeStr, "KB") {
		multiplier = 1024
		sizeStr = strings.TrimSuffix(sizeStr, "KB")
	}

	sizeStr = strings.TrimSpace(sizeStr)
	val, err := strconv.ParseInt(sizeStr, 10, 64)
	if err != nil {
		return 10 * 1024 * 1024 * 1024
	}
	return val * multiplier
}

func runAnalyze(cmd *cobra.Command, args []string) {
	workDir, _ := os.Getwd()
	
	analyzer := analyzer.NewAnalyzer(workDir)
	info, err := analyzer.Analyze()
	if err != nil {
		log.Fatalf("Analysis failed: %v", err)
	}

	fmt.Println(info.String())
}

func runSave(cmd *cobra.Command, args []string) {
	cfg := loadConfig()
	sourcePath := args[0]

	if _, err := os.Stat(sourcePath); err != nil {
		log.Fatalf("Source path does not exist: %v", err)
	}

	store, err := createStorage(cfg)
	if err != nil {
		log.Fatalf("Failed to create storage: %v", err)
	}
	defer store.Close()

	cm, err := createCacheManager(cfg, store, true)
	if err != nil {
		log.Fatalf("Failed to create cache manager: %v", err)
	}
	defer cm.Close()

	key := cacheKey
	if key == "" {
		fpCalc := fingerprint.NewCalculator(
			fingerprint.WithExcludePaths(excludeDirs),
		)

		workDir, _ := os.Getwd()
		analyzer := analyzer.NewAnalyzer(workDir)
		info, _ := analyzer.Analyze()
		
		var depFiles []string
		if len(info.DepFiles) > 0 {
			depFiles = info.GetFingerprintFiles()
		} else {
			depFiles = []string{sourcePath}
		}

		fp, err := fpCalc.Calculate(depFiles)
		if err != nil {
			log.Fatalf("Failed to calculate fingerprint: %v", err)
		}
		key = fp.CacheKey(cfg.Cache.KeyPrefix)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	fmt.Printf("Saving %s to cache with key: %s...\n", sourcePath, key)
	if err := cm.Upload(ctx, key, sourcePath); err != nil {
		log.Fatalf("Failed to save cache: %v", err)
	}

	fmt.Println("Cache saved successfully!")
}

func runRestore(cmd *cobra.Command, args []string) {
	cfg := loadConfig()
	targetPath := "."
	if len(args) > 0 {
		targetPath = args[0]
	}

	store, err := createStorage(cfg)
	if err != nil {
		log.Fatalf("Failed to create storage: %v", err)
	}
	defer store.Close()

	cm, err := createCacheManager(cfg, store, true)
	if err != nil {
		log.Fatalf("Failed to create cache manager: %v", err)
	}
	defer cm.Close()

	key := cacheKey
	if key == "" {
		fpCalc := fingerprint.NewCalculator(
			fingerprint.WithExcludePaths(excludeDirs),
		)

		workDir, _ := os.Getwd()
		analyzer := analyzer.NewAnalyzer(workDir)
		info, _ := analyzer.Analyze()
		
		if len(info.DepFiles) == 0 {
			log.Fatal("No dependency files found and no cache key specified")
		}

		depFiles := info.GetFingerprintFiles()
		fp, err := fpCalc.Calculate(depFiles)
		if err != nil {
			log.Fatalf("Failed to calculate fingerprint: %v", err)
		}
		key = fp.CacheKey(cfg.Cache.KeyPrefix)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	fmt.Printf("Restoring cache %s to %s...\n", key, targetPath)
	restored, err := cm.Download(ctx, key, targetPath)
	if err != nil {
		log.Fatalf("Failed to restore cache: %v", err)
	}

	if restored {
		fmt.Println("Cache restored successfully!")
	} else {
		fmt.Println("Cache not found, cache miss.")
		os.Exit(1)
	}
}

func runList(cmd *cobra.Command, args []string) {
	cfg := loadConfig()

	store, err := createStorage(cfg)
	if err != nil {
		log.Fatalf("Failed to create storage: %v", err)
	}
	defer store.Close()

	cm, err := createCacheManager(cfg, store, true)
	if err != nil {
		log.Fatalf("Failed to create cache manager: %v", err)
	}
	defer cm.Close()

	ctx := context.Background()
	keys, err := cm.List(ctx, "")
	if err != nil {
		log.Fatalf("Failed to list cache: %v", err)
	}

	if len(keys) == 0 {
		fmt.Println("No cached items found.")
		return
	}

	fmt.Println("Cached items:")
	for _, key := range keys {
		fmt.Printf("  - %s\n", key)
	}
}

func runDelete(cmd *cobra.Command, args []string) {
	cfg := loadConfig()
	key := args[0]

	force, _ := cmd.Flags().GetBool("force")
	if !force {
		fmt.Printf("Are you sure you want to delete cache '%s'? (y/N): ", key)
		var response string
		fmt.Scanln(&response)
		if strings.ToLower(response) != "y" {
			fmt.Println("Delete cancelled.")
			return
		}
	}

	store, err := createStorage(cfg)
	if err != nil {
		log.Fatalf("Failed to create storage: %v", err)
	}
	defer store.Close()

	cm, err := createCacheManager(cfg, store, true)
	if err != nil {
		log.Fatalf("Failed to create cache manager: %v", err)
	}
	defer cm.Close()

	ctx := context.Background()
	if err := cm.Delete(ctx, key); err != nil {
		log.Fatalf("Failed to delete cache: %v", err)
	}

	fmt.Printf("Cache '%s' deleted successfully.\n", key)
}

func runClear(cmd *cobra.Command, args []string) {
	cfg := loadConfig()

	store, err := createStorage(cfg)
	if err != nil {
		log.Fatalf("Failed to create storage: %v", err)
	}
	defer store.Close()

	cm, err := createCacheManager(cfg, store, true)
	if err != nil {
		log.Fatalf("Failed to create cache manager: %v", err)
	}
	defer cm.Close()

	if err := cm.Clear(); err != nil {
		log.Fatalf("Failed to clear cache: %v", err)
	}

	fmt.Println("Local cache cleared successfully.")
}

func runStatus(cmd *cobra.Command, args []string) {
	cfg := loadConfig()

	store, err := createStorage(cfg)
	if err != nil {
		log.Fatalf("Failed to create storage: %v", err)
	}
	defer store.Close()

	cm, err := createCacheManager(cfg, store, true)
	if err != nil {
		log.Fatalf("Failed to create cache manager: %v", err)
	}
	defer cm.Close()

	count, size := cm.GetStats()
	fmt.Println("Cache Status:")
	fmt.Printf("  Items: %d\n", count)
	fmt.Printf("  Size:  %s (%.2f GB)\n", formatSize(size), float64(size)/1024/1024/1024)
	fmt.Printf("  Storage Type: %s\n", cfg.Storage.Type)
	fmt.Printf("  Local Cache Dir: %s\n", cfg.Cache.CacheDir)

	tierStats := cm.GetTierStats()
	if tierStats != nil {
		fmt.Println("\nTiered Cache Stats:")
		for tier, stats := range tierStats {
			fmt.Printf("  %-6s: %3d items, %s\n", 
				tier, 
				stats["count"], 
				formatSize(stats["size"]))
		}
	}
}

func formatSize(size int64) string {
	const unit = 1024
	if size < unit {
		return fmt.Sprintf("%d B", size)
	}
	div, exp := int64(unit), 0
	for n := size / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(size)/float64(div), "KMGTPE"[exp])
}

func runWatch(cmd *cobra.Command, args []string) {
	cfg := loadConfig()
	workDir, _ := os.Getwd()

	store, err := createStorage(cfg)
	if err != nil {
		log.Fatalf("Failed to create storage: %v", err)
	}
	defer store.Close()

	cm, err := createCacheManager(cfg, store, true)
	if err != nil {
		log.Fatalf("Failed to create cache manager: %v", err)
	}
	defer cm.Close()

	fpCalc := fingerprint.NewCalculator(
		fingerprint.WithExcludePaths(excludeDirs),
	)

	analyzer := analyzer.NewAnalyzer(workDir)
	info, err := analyzer.Analyze()
	if err != nil {
		log.Fatalf("Failed to analyze project: %v", err)
	}

	fmt.Printf("Watching project: %s\n", info.Type)
	fmt.Println("Watching dependency files for changes...")

	pwOpts := []watcher.PreWarmerOption{
		watcher.WithCachePrefix(cfg.Cache.KeyPrefix),
		watcher.WithSharedMode(true),
	}
	if len(cfg.Watcher.WatchDirs) > 0 {
		pwOpts = append(pwOpts, watcher.WithWatchDirs(cfg.Watcher.WatchDirs))
	}

	pw, err := watcher.NewPreWarmer(cm, fpCalc, store, workDir, pwOpts...)
	if err != nil {
		log.Fatalf("Failed to create prewarmer: %v", err)
	}
	defer pw.Stop()

	ctx := context.Background()
	if err := pw.Start(ctx, info.GetSortedDepFiles()); err != nil {
		log.Fatalf("Failed to start watcher: %v", err)
	}

	fmt.Println("Press Ctrl+C to stop watching...")
	select {}
}

func runFingerprint(cmd *cobra.Command, args []string) {
	fpCalc := fingerprint.NewCalculator(
		fingerprint.WithExcludePaths(excludeDirs),
	)

	workDir, _ := os.Getwd()
	var files []string
	for _, arg := range args {
		if !filepath.IsAbs(arg) {
			files = append(files, filepath.Join(workDir, arg))
		} else {
			files = append(files, arg)
		}
	}

	fp, err := fpCalc.Calculate(files)
	if err != nil {
		log.Fatalf("Failed to calculate fingerprint: %v", err)
	}

	fmt.Printf("Fingerprint: %s\n", fp.String())
	fmt.Printf("Short Hash: %s\n", fp.Short())
	fmt.Printf("Cache Key: %s\n", fp.CacheKey(cachePrefix))
	fmt.Println("Files included:")
	for _, f := range fp.Files {
		fmt.Printf("  - %s\n", f)
	}
}

func runAnalytics(cmd *cobra.Command, args []string) {
	cfg := loadConfig()

	store, err := createStorage(cfg)
	if err != nil {
		log.Fatalf("Failed to create storage: %v", err)
	}
	defer store.Close()

	cm, err := createCacheManager(cfg, store, true)
	if err != nil {
		log.Fatalf("Failed to create cache manager: %v", err)
	}
	defer cm.Close()

	analytics := cm.GetAnalytics()
	stats := analytics.GetStats()

	fmt.Println("Cache Analytics:")
	fmt.Printf("  Total Hits:    %d\n", stats.TotalHits)
	fmt.Printf("  Total Misses:  %d\n", stats.TotalMisses)
	fmt.Printf("  Hit Rate:      %.2f%%\n", stats.HitRate*100)
	fmt.Printf("  Total Saved:   %s\n", formatDuration(stats.TotalSavedTime))

	fmt.Println("\nTop Cache Keys by Hits:")
	topKeys := analytics.GetTopKeys(10)
	for i, ks := range topKeys {
		fmt.Printf("  %2d. %s\n", i+1, ks.Key)
		fmt.Printf("       Hits: %d, Hit Rate: %.2f%%, Saved: %s\n", 
			ks.Hits, ks.HitRate*100, formatDuration(ks.TotalSavedTime))
	}

	if len(stats.ByProject) > 0 {
		fmt.Println("\nStats by Project:")
		for projID, projStats := range stats.ByProject {
			fmt.Printf("  %s (%s):\n", projID, projStats.ProjectType)
			fmt.Printf("    Hits: %d, Misses: %d, Hit Rate: %.2f%%, Saved: %s\n",
				projStats.Hits, projStats.Misses, projStats.HitRate*100, 
				formatDuration(projStats.TotalSavedTime))
		}
	}

	cm.SaveAnalytics()
}

func formatDuration(ns int64) string {
	d := time.Duration(ns)
	if d < time.Second {
		return d.String()
	}
	return fmt.Sprintf("%.1f seconds", d.Seconds())
}

func runPrefetch(cmd *cobra.Command, args []string) {
	cfg := loadConfig()
	workDir, _ := os.Getwd()

	store, err := createStorage(cfg)
	if err != nil {
		log.Fatalf("Failed to create storage: %v", err)
	}
	defer store.Close()

	cm, err := createCacheManager(cfg, store, true)
	if err != nil {
		log.Fatalf("Failed to create cache manager: %v", err)
	}
	defer cm.Close()

	analyzer := analyzer.NewAnalyzer(workDir)
	info, err := analyzer.Analyze()
	if err != nil {
		log.Fatalf("Failed to analyze project: %v", err)
	}

	cacheDir := cfg.Cache.CacheDir
	if cacheDir == "" {
		home, _ := os.UserHomeDir()
		cacheDir = filepath.Join(home, ".cicache", "local")
	}

	prefetchMgr := cache.NewPrefetchManager(cm, store, cacheDir, 3)

	fmt.Printf("Predicting cache needs for project: %s\n", info.Type)
	predictions := prefetchMgr.GetPredictions("", string(info.Type), "", 10)

	if len(predictions) == 0 {
		fmt.Println("No predictions available yet. Build some caches first!")
		return
	}

	fmt.Println("\nPredicted Cache Items:")
	for i, pred := range predictions {
		fmt.Printf("  %2d. %s\n", i+1, pred.CacheKey)
		fmt.Printf("       Probability: %.2f%%, Estimated Size: %s\n", 
			pred.Probability*100, formatSize(pred.EstimatedSize))
	}

	fmt.Println("\nStarting prefetch...")
	ctx := context.Background()
	prefetched, err := prefetchMgr.PredictAndPrefetch(ctx, "", string(info.Type), "", workDir)
	if err != nil {
		log.Fatalf("Prefetch failed: %v", err)
	}

	fmt.Printf("\nPrefetched %d items successfully!\n", len(prefetched))
}

func runShareFind(cmd *cobra.Command, args []string) {
	cfg := loadConfig()
	workDir, _ := os.Getwd()

	store, err := createStorage(cfg)
	if err != nil {
		log.Fatalf("Failed to create storage: %v", err)
	}
	defer store.Close()

	cacheDir := cfg.Cache.CacheDir
	if cacheDir == "" {
		home, _ := os.UserHomeDir()
		cacheDir = filepath.Join(home, ".cicache", "local")
	}

	sharingMgr := cache.NewCacheSharingManager(store, cacheDir)

	analyzer := analyzer.NewAnalyzer(workDir)
	info, err := analyzer.Analyze()
	if err != nil {
		log.Fatalf("Failed to analyze project: %v", err)
	}

	fmt.Printf("Finding shared caches for project type: %s\n", info.Type)
	
	ctx := context.Background()
	depFiles := info.GetSortedDepFiles()
	matches, err := sharingMgr.FindSimilarCaches(ctx, string(info.Type), depFiles)
	if err != nil {
		log.Fatalf("Failed to find shared caches: %v", err)
	}

	if len(matches) == 0 {
		fmt.Println("No shared caches found.")
		return
	}

	fmt.Printf("\nFound %d similar cache entries:\n", len(matches))
	for i, match := range matches {
		fmt.Printf("  %2d. %s\n", i+1, match.CacheKey)
		fmt.Printf("       Type: %s, Size: %s, Hits: %d\n", 
			match.ProjectType, formatSize(match.Size), match.HitCount)
		fmt.Printf("       Tags: %v\n", match.Tags)
	}
}

func runShareRegister(cmd *cobra.Command, args []string) {
	cfg := loadConfig()
	workDir, _ := os.Getwd()
	cacheKey := args[0]

	store, err := createStorage(cfg)
	if err != nil {
		log.Fatalf("Failed to create storage: %v", err)
	}
	defer store.Close()

	cm, err := createCacheManager(cfg, store, true)
	if err != nil {
		log.Fatalf("Failed to create cache manager: %v", err)
	}
	defer cm.Close()

	cacheDir := cfg.Cache.CacheDir
	if cacheDir == "" {
		home, _ := os.UserHomeDir()
		cacheDir = filepath.Join(home, ".cicache", "local")
	}

	sharingMgr := cache.NewCacheSharingManager(store, cacheDir)

	analyzer := analyzer.NewAnalyzer(workDir)
	info, err := analyzer.Analyze()
	if err != nil {
		log.Fatalf("Failed to analyze project: %v", err)
	}

	ctx := context.Background()
	depFiles := info.GetSortedDepFiles()

	ctxInfo := context.Background()
	keys, _ := cm.List(ctxInfo, "")
	var size int64 = 0
	for _, k := range keys {
		if k == cacheKey {
			size = 100 * 1024 * 1024
			break
		}
	}

	err = sharingMgr.RegisterCache(ctx, cacheKey, string(info.Type), depFiles, size)
	if err != nil {
		log.Fatalf("Failed to register cache: %v", err)
	}

	fmt.Printf("Cache '%s' registered for cross-project sharing!\n", cacheKey)
}
