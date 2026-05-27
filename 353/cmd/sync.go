package cmd

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/cloud-migration-tool/config"
	"github.com/cloud-migration-tool/pkg/sync"
	"github.com/spf13/cobra"
)

var syncCmd = &cobra.Command{
	Use:   "sync",
	Short: "Rsync-based file synchronization",
	Long:  `Continuous file synchronization using rsync between source and destination.`,
	Run:   runSync,
}

func init() {
	rootCmd.AddCommand(syncCmd)
	syncCmd.Flags().String("source", "", "Source path")
	syncCmd.Flags().String("dest", "", "Destination path")
	syncCmd.Flags().String("ssh-user", "", "SSH username")
	syncCmd.Flags().String("ssh-host", "", "SSH host")
	syncCmd.Flags().Int("ssh-port", 22, "SSH port")
	syncCmd.Flags().String("ssh-key", "", "SSH private key path")
	syncCmd.Flags().Bool("continuous", false, "Run continuous synchronization")
	syncCmd.Flags().Int("interval", 300, "Sync interval in seconds (for continuous mode)")
	syncCmd.Flags().Bool("dry-run", false, "Perform a dry run")
	syncCmd.Flags().String("log", "", "Save sync log to file")
}

func runSync(cmd *cobra.Command, args []string) {
	if !sync.CheckRsyncAvailable() {
		fmt.Println("Error: rsync command not found. Please install rsync first.")
		return
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	cfg := loadRsyncConfig(cmd)
	rm := sync.NewRsyncManager(cfg)

	dryRun, _ := cmd.Flags().GetBool("dry-run")
	if dryRun {
		fmt.Println("[Dry Run] rsync command preview:")
		output, err := rm.DryRun(ctx)
		if err != nil {
			fmt.Printf("Dry run error: %v\n", err)
		}
		fmt.Println(output)
		return
	}

	continuous, _ := cmd.Flags().GetBool("continuous")

	fmt.Println("=== Rsync Synchronization ===")
	fmt.Printf("Source: %s\n", cfg.SourcePath)
	fmt.Printf("Destination: %s@%s:%s\n", cfg.SSHUser, cfg.SSHHost, cfg.DestPath)
	if continuous {
		fmt.Printf("Mode: Continuous (interval: %ds)\n", cfg.SyncInterval)
	} else {
		fmt.Println("Mode: One-time sync")
	}
	fmt.Println("============================")

	go func() {
		<-sigChan
		fmt.Println("\nStopping synchronization...")
		rm.StopContinuousSync()
		cancel()
	}()

	if continuous {
		if err := rm.StartContinuousSync(ctx); err != nil && err != context.Canceled {
			fmt.Printf("Sync error: %v\n", err)
		}
	} else {
		result, err := rm.SyncOnce(ctx)
		if err != nil {
			fmt.Printf("Sync failed: %v\n", err)
		} else {
			fmt.Printf("\nSync completed in %v\n", result.ElapsedTime)
			fmt.Printf("Files transferred: %d\n", result.FilesTransferred)
			if result.Success {
				fmt.Println("Status: SUCCESS")
			} else {
				fmt.Println("Status: FAILED")
			}
		}
	}

	logPath, _ := cmd.Flags().GetString("log")
	if logPath != "" {
		if err := rm.SaveLogToFile(logPath); err != nil {
			fmt.Printf("Failed to save log: %v\n", err)
		} else {
			fmt.Printf("Log saved to: %s\n", logPath)
		}
	}

	stats := rm.GetStatistics()
	fmt.Println("\n=== Statistics ===")
	for k, v := range stats {
		fmt.Printf("%s: %v\n", k, v)
	}
}

func loadRsyncConfig(cmd *cobra.Command) config.RsyncConfig {
	sourcePath, _ := cmd.Flags().GetString("source")
	destPath, _ := cmd.Flags().GetString("dest")
	sshUser, _ := cmd.Flags().GetString("ssh-user")
	sshHost, _ := cmd.Flags().GetString("ssh-host")
	sshPort, _ := cmd.Flags().GetInt("ssh-port")
	sshKey, _ := cmd.Flags().GetString("ssh-key")
	continuous, _ := cmd.Flags().GetBool("continuous")
	interval, _ := cmd.Flags().GetInt("interval")

	return config.RsyncConfig{
		SourcePath:     sourcePath,
		DestPath:       destPath,
		SSHUser:        sshUser,
		SSHHost:        sshHost,
		SSHPort:        sshPort,
		SSHKeyPath:     sshKey,
		ContinuousSync: continuous,
		SyncInterval:   interval,
	}
}
