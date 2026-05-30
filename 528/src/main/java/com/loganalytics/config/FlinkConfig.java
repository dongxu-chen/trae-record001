package com.loganalytics.config;

import java.io.Serializable;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

public class FlinkConfig implements Serializable {
    private String kafkaBrokers = "localhost:9092";
    private String kafkaTopic = "nginx-logs";
    private String kafkaGroupId = "nginx-log-analyzer";
    private String redisHost = "localhost";
    private int redisPort = 6379;
    private String clickhouseUrl = "jdbc:clickhouse://localhost:8123/default";
    private String clickhouseUser = "default";
    private String clickhousePassword = "";
    private int windowSizeSeconds = 60;
    private int slideSizeSeconds = 10;

    private double tDigestCompression = 100.0;
    private double sigmaMultiplier = 3.0;
    private int historyWindowSize = 30;

    private Set<String> enabledDimensions = new HashSet<>(Arrays.asList(
            "all", "api", "status", "api_status", "api_method", "host", "method"
    ));
    private Set<String> apiWhitelist = new HashSet<>();
    private boolean enableApiWhitelist = false;

    private double errorRateThreshold = 5.0;
    private double latencyP99Threshold = 1000.0;
    private long qpsAlertThreshold = 10000;

    private double slowRequestThresholdMs = 1000.0;
    private double upstreamRatioThreshold = 0.7;
    private int slowRequestProfileSize = 100;

    private int forecastHistorySize = 60;
    private double forecastMinConfidence = 0.3;

    private String customMetricDefinitions = "";

    public FlinkConfig() {
    }

    public static FlinkConfig fromEnv() {
        FlinkConfig config = new FlinkConfig();
        config.kafkaBrokers = System.getenv().getOrDefault("KAFKA_BROKERS", config.kafkaBrokers);
        config.kafkaTopic = System.getenv().getOrDefault("KAFKA_TOPIC", config.kafkaTopic);
        config.kafkaGroupId = System.getenv().getOrDefault("KAFKA_GROUP_ID", config.kafkaGroupId);
        config.redisHost = System.getenv().getOrDefault("REDIS_HOST", config.redisHost);
        config.redisPort = Integer.parseInt(System.getenv().getOrDefault("REDIS_PORT", String.valueOf(config.redisPort)));
        config.clickhouseUrl = System.getenv().getOrDefault("CLICKHOUSE_URL", config.clickhouseUrl);
        config.clickhouseUser = System.getenv().getOrDefault("CLICKHOUSE_USER", config.clickhouseUser);
        config.clickhousePassword = System.getenv().getOrDefault("CLICKHOUSE_PASSWORD", config.clickhousePassword);
        config.windowSizeSeconds = Integer.parseInt(System.getenv().getOrDefault("WINDOW_SIZE_SECONDS", String.valueOf(config.windowSizeSeconds)));
        config.slideSizeSeconds = Integer.parseInt(System.getenv().getOrDefault("SLIDE_SIZE_SECONDS", String.valueOf(config.slideSizeSeconds)));

        config.tDigestCompression = Double.parseDouble(System.getenv().getOrDefault("TDIGEST_COMPRESSION", String.valueOf(config.tDigestCompression)));
        config.sigmaMultiplier = Double.parseDouble(System.getenv().getOrDefault("SIGMA_MULTIPLIER", String.valueOf(config.sigmaMultiplier)));
        config.historyWindowSize = Integer.parseInt(System.getenv().getOrDefault("HISTORY_WINDOW_SIZE", String.valueOf(config.historyWindowSize)));

        String enabledDimsStr = System.getenv().getOrDefault("ENABLED_DIMENSIONS", "");
        if (!enabledDimsStr.isEmpty()) {
            config.enabledDimensions = new HashSet<>(Arrays.asList(enabledDimsStr.split(",")));
        }

        String apiWhitelistStr = System.getenv().getOrDefault("API_WHITELIST", "");
        if (!apiWhitelistStr.isEmpty()) {
            config.apiWhitelist = new HashSet<>(Arrays.asList(apiWhitelistStr.split(",")));
            config.enableApiWhitelist = true;
        }

        config.errorRateThreshold = Double.parseDouble(System.getenv().getOrDefault("ERROR_RATE_THRESHOLD", String.valueOf(config.errorRateThreshold)));
        config.latencyP99Threshold = Double.parseDouble(System.getenv().getOrDefault("LATENCY_P99_THRESHOLD", String.valueOf(config.latencyP99Threshold)));
        config.qpsAlertThreshold = Long.parseLong(System.getenv().getOrDefault("QPS_ALERT_THRESHOLD", String.valueOf(config.qpsAlertThreshold)));

        config.slowRequestThresholdMs = Double.parseDouble(System.getenv().getOrDefault("SLOW_REQUEST_THRESHOLD_MS", String.valueOf(config.slowRequestThresholdMs)));
        config.upstreamRatioThreshold = Double.parseDouble(System.getenv().getOrDefault("UPSTREAM_RATIO_THRESHOLD", String.valueOf(config.upstreamRatioThreshold)));
        config.slowRequestProfileSize = Integer.parseInt(System.getenv().getOrDefault("SLOW_REQUEST_PROFILE_SIZE", String.valueOf(config.slowRequestProfileSize)));

        config.forecastHistorySize = Integer.parseInt(System.getenv().getOrDefault("FORECAST_HISTORY_SIZE", String.valueOf(config.forecastHistorySize)));
        config.forecastMinConfidence = Double.parseDouble(System.getenv().getOrDefault("FORECAST_MIN_CONFIDENCE", String.valueOf(config.forecastMinConfidence)));

        config.customMetricDefinitions = System.getenv().getOrDefault("CUSTOM_METRIC_DEFINITIONS", config.customMetricDefinitions);

        return config;
    }

    public String getKafkaBrokers() {
        return kafkaBrokers;
    }

    public void setKafkaBrokers(String kafkaBrokers) {
        this.kafkaBrokers = kafkaBrokers;
    }

    public String getKafkaTopic() {
        return kafkaTopic;
    }

    public void setKafkaTopic(String kafkaTopic) {
        this.kafkaTopic = kafkaTopic;
    }

    public String getKafkaGroupId() {
        return kafkaGroupId;
    }

    public void setKafkaGroupId(String kafkaGroupId) {
        this.kafkaGroupId = kafkaGroupId;
    }

    public String getRedisHost() {
        return redisHost;
    }

    public void setRedisHost(String redisHost) {
        this.redisHost = redisHost;
    }

    public int getRedisPort() {
        return redisPort;
    }

    public void setRedisPort(int redisPort) {
        this.redisPort = redisPort;
    }

    public String getClickhouseUrl() {
        return clickhouseUrl;
    }

    public void setClickhouseUrl(String clickhouseUrl) {
        this.clickhouseUrl = clickhouseUrl;
    }

    public String getClickhouseUser() {
        return clickhouseUser;
    }

    public void setClickhouseUser(String clickhouseUser) {
        this.clickhouseUser = clickhouseUser;
    }

    public String getClickhousePassword() {
        return clickhousePassword;
    }

    public void setClickhousePassword(String clickhousePassword) {
        this.clickhousePassword = clickhousePassword;
    }

    public int getWindowSizeSeconds() {
        return windowSizeSeconds;
    }

    public void setWindowSizeSeconds(int windowSizeSeconds) {
        this.windowSizeSeconds = windowSizeSeconds;
    }

    public int getSlideSizeSeconds() {
        return slideSizeSeconds;
    }

    public void setSlideSizeSeconds(int slideSizeSeconds) {
        this.slideSizeSeconds = slideSizeSeconds;
    }

    public double gettDigestCompression() {
        return tDigestCompression;
    }

    public void settDigestCompression(double tDigestCompression) {
        this.tDigestCompression = tDigestCompression;
    }

    public double getSigmaMultiplier() {
        return sigmaMultiplier;
    }

    public void setSigmaMultiplier(double sigmaMultiplier) {
        this.sigmaMultiplier = sigmaMultiplier;
    }

    public int getHistoryWindowSize() {
        return historyWindowSize;
    }

    public void setHistoryWindowSize(int historyWindowSize) {
        this.historyWindowSize = historyWindowSize;
    }

    public Set<String> getEnabledDimensions() {
        return enabledDimensions;
    }

    public void setEnabledDimensions(Set<String> enabledDimensions) {
        this.enabledDimensions = enabledDimensions;
    }

    public Set<String> getApiWhitelist() {
        return apiWhitelist;
    }

    public void setApiWhitelist(Set<String> apiWhitelist) {
        this.apiWhitelist = apiWhitelist;
    }

    public boolean isEnableApiWhitelist() {
        return enableApiWhitelist;
    }

    public void setEnableApiWhitelist(boolean enableApiWhitelist) {
        this.enableApiWhitelist = enableApiWhitelist;
    }

    public double getErrorRateThreshold() {
        return errorRateThreshold;
    }

    public void setErrorRateThreshold(double errorRateThreshold) {
        this.errorRateThreshold = errorRateThreshold;
    }

    public double getLatencyP99Threshold() {
        return latencyP99Threshold;
    }

    public void setLatencyP99Threshold(double latencyP99Threshold) {
        this.latencyP99Threshold = latencyP99Threshold;
    }

    public long getQpsAlertThreshold() {
        return qpsAlertThreshold;
    }

    public void setQpsAlertThreshold(long qpsAlertThreshold) {
        this.qpsAlertThreshold = qpsAlertThreshold;
    }

    public double getSlowRequestThresholdMs() {
        return slowRequestThresholdMs;
    }

    public void setSlowRequestThresholdMs(double slowRequestThresholdMs) {
        this.slowRequestThresholdMs = slowRequestThresholdMs;
    }

    public double getUpstreamRatioThreshold() {
        return upstreamRatioThreshold;
    }

    public void setUpstreamRatioThreshold(double upstreamRatioThreshold) {
        this.upstreamRatioThreshold = upstreamRatioThreshold;
    }

    public int getSlowRequestProfileSize() {
        return slowRequestProfileSize;
    }

    public void setSlowRequestProfileSize(int slowRequestProfileSize) {
        this.slowRequestProfileSize = slowRequestProfileSize;
    }

    public int getForecastHistorySize() {
        return forecastHistorySize;
    }

    public void setForecastHistorySize(int forecastHistorySize) {
        this.forecastHistorySize = forecastHistorySize;
    }

    public double getForecastMinConfidence() {
        return forecastMinConfidence;
    }

    public void setForecastMinConfidence(double forecastMinConfidence) {
        this.forecastMinConfidence = forecastMinConfidence;
    }

    public String getCustomMetricDefinitions() {
        return customMetricDefinitions;
    }

    public void setCustomMetricDefinitions(String customMetricDefinitions) {
        this.customMetricDefinitions = customMetricDefinitions;
    }
}
