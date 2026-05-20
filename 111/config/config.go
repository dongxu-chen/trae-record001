package config

const (
	MinIOEndpoint   = "localhost:9000"
	MinIOAccessKey  = "minioadmin"
	MinIOSecretKey  = "minioadmin"
	MinIOUseSSL     = false
	MinIOBucketName = "file-storage"

	SeaweedFSMasterURL   = "http://localhost:9333"
	SeaweedFSVolumeURL   = "http://localhost:8080"
	SeaweedFSFilerURL    = "http://localhost:8888"
	SeaweedFSS3Endpoint  = "http://localhost:8333"
	SeaweedFSAccessKey   = "admin"
	SeaweedFSSecretKey   = "secret"
	SeaweedFSUseSSL      = false
	SeaweedFSBucketName  = "file-storage"

	RedisAddr     = "localhost:6379"
	RedisPassword = ""
	RedisDB       = 0

	ChunkSize      = 5 * 1024 * 1024
	MaxFileSize    = 5 * 1024 * 1024 * 1024
	MaxChunkNumber = MaxFileSize / ChunkSize

	ServerPort = ":8080"

	EnableReplication      = false
	ReplicationWorkerCount = 3
	ReplicationMaxRetries  = 5

	EnableSmallFileMerge   = true
	SmallFileThresholdSize = 64 * 1024
	SmallFileMaxFiles     = 1000
)

var ReplicationPeers []ReplicationPeerConfig

type ReplicationPeerConfig struct {
	Name       string
	MasterURL  string
	FilerURL   string
	S3Endpoint string
	AccessKey  string
	SecretKey  string
}

func InitConfig() {
	ReplicationPeers = []ReplicationPeerConfig{
		{
			Name:       "peer-beijing",
			MasterURL:  "http://beijing-master:9333",
			FilerURL:   "http://beijing-filer:8888",
			S3Endpoint: "http://beijing-s3:8333",
			AccessKey:  "admin",
			SecretKey:  "secret",
		},
		{
			Name:       "peer-shanghai",
			MasterURL:  "http://shanghai-master:9333",
			FilerURL:   "http://shanghai-filer:8888",
			S3Endpoint: "http://shanghai-s3:8333",
			AccessKey:  "admin",
			SecretKey:  "secret",
		},
	}
}

