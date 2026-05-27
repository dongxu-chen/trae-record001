package config

type Config struct {
	MongoURI           string
	SecondaryMongoURI  string
	Database           string
	Collection         string
	SlowQueryLogPath   string
	ThresholdMS        int
	MaxRecommendations int
	CompressionFactor  float64
	UseSecondary       bool
}

func DefaultConfig() *Config {
	return &Config{
		MongoURI:           "mongodb://localhost:27017",
		SecondaryMongoURI:  "",
		ThresholdMS:        100,
		MaxRecommendations: 10,
		CompressionFactor:  1.0,
		UseSecondary:       false,
	}
}
