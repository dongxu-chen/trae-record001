package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

type CloudConfig struct {
	Provider string `yaml:"provider"`
	Region   string `yaml:"region"`
}

type AWSConfig struct {
	CloudConfig `yaml:",inline"`
	AccessKey string `yaml:"access_key"`
	SecretKey string `yaml:"secret_key"`
}

type AliyunConfig struct {
	CloudConfig `yaml:",inline"`
	AccessKeyID     string `yaml:"access_key_id"`
	AccessKeySecret string `yaml:"access_key_secret"`
}

type TencentConfig struct {
	CloudConfig `yaml:",inline"`
	SecretID  string `yaml:"secret_id"`
	SecretKey string `yaml:"secret_key"`
}

type MigrationConfig struct {
	Source      CloudConfig   `yaml:"source"`
	Destination CloudConfig  `yaml:"destination"`
	Resources   ResourceConfig `yaml:"resources"`
	Rsync     RsyncConfig    `yaml:"rsync"`
}

type ResourceConfig struct {
	EC2 []EC2Resource `yaml:"ec2"`
	RDS []RDSResource `yaml:"rds"`
	S3  []S3Resource  `yaml:"s3"`
}

type EC2Resource struct {
	InstanceID     string `yaml:"instance_id"`
	Name         string `yaml:"name"`
	InstanceType string `yaml:"instance_type"`
	TargetZone   string `yaml:"target_zone"`
}

type RDSResource struct {
	DBInstanceID string `yaml:"db_instance_id"`
	TargetDBName  string `yaml:"target_db_name"`
	DBType        string `yaml:"db_type"`
}

type S3Resource struct {
	Bucket      string `yaml:"bucket"`
	TargetBucket  string `yaml:"target_bucket"`
	Prefix       string `yaml:"prefix"`
}

type RsyncConfig struct {
	SourcePath      string   `yaml:"source_path"`
	DestPath        string   `yaml:"dest_path"`
	SSHUser         string   `yaml:"ssh_user"`
	SSHHost         string   `yaml:"ssh_host"`
	SSHPort         int      `yaml:"ssh_port"`
	SSHKeyPath      string   `yaml:"ssh_key_path"`
	ExcludePatterns []string `yaml:"exclude_patterns"`
	BandwidthLimit  string   `yaml:"bandwidth_limit"`
	ContinuousSync   bool     `yaml:"continuous_sync"`
	SyncInterval     int      `yaml:"sync_interval"`
}

func LoadConfig(path string) (*MigrationConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var config MigrationConfig
	err = yaml.Unmarshal(data, &config)
	if err != nil {
		return nil, err
	}

	return &config, nil
}
