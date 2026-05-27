package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var cfgFile string

var rootCmd = &cobra.Command{
	Use:   "cloud-migrate",
	Short: "Cross-cloud migration tool for AWS to Aliyun/Tencent Cloud",
	Long: `A comprehensive cloud migration tool that supports migrating resources from AWS to Aliyun or Tencent Cloud.
Features include:
- EC2/ECS instance migration via snapshots
- RDS database migration
- S3/OSS object storage migration (full + incremental)
- Rsync-based continuous file sync
- Migration drill (cutover, rollback testing)
- Detailed migration reports`,
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func init() {
	cobra.OnInitialize(initConfig)
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is ./config.yaml)")
	rootCmd.PersistentFlags().String("source-provider", "aws", "Source cloud provider (aws)")
	rootCmd.PersistentFlags().String("source-region", "us-east-1", "Source cloud region")
	rootCmd.PersistentFlags().String("dest-provider", "aliyun", "Destination cloud provider (aliyun/tencent)")
	rootCmd.PersistentFlags().String("dest-region", "cn-hangzhou", "Destination cloud region")

	viper.BindPFlag("source.provider", rootCmd.PersistentFlags().Lookup("source-provider"))
	viper.BindPFlag("source.region", rootCmd.PersistentFlags().Lookup("source-region"))
	viper.BindPFlag("destination.provider", rootCmd.PersistentFlags().Lookup("dest-provider"))
	viper.BindPFlag("destination.region", rootCmd.PersistentFlags().Lookup("dest-region"))
}

func initConfig() {
	if cfgFile != "" {
		viper.SetConfigFile(cfgFile)
	} else {
		viper.SetConfigName("config")
		viper.SetConfigType("yaml")
		viper.AddConfigPath(".")
	}

	viper.AutomaticEnv()

	if err := viper.ReadInConfig(); err == nil {
		fmt.Println("Using config file:", viper.ConfigFileUsed())
	}
}
