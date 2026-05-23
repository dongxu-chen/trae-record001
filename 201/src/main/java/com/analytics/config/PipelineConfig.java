package com.analytics.config;

import java.io.Serializable;

public class PipelineConfig implements Serializable {

    private String kafkaBrokers;
    private String kafkaTopic;
    private String kafkaGroupId;
    private String clickhouseUrl;
    private String clickhouseUser;
    private String clickhousePassword;
    private long checkpointIntervalMs;
    private int checkpointTimeoutMin;
    private int allowedLatenessMin;
    private int windowSizeMin;
    private int stateTtlHours;
    private int bloomFilterExpectedInsertions;
    private double bloomFilterFpp;

    public PipelineConfig() {
        this.kafkaBrokers = System.getenv().getOrDefault("KAFKA_BROKERS", "localhost:9092");
        this.kafkaTopic = System.getenv().getOrDefault("KAFKA_TOPIC", "user_behavior_events");
        this.kafkaGroupId = System.getenv().getOrDefault("KAFKA_GROUP_ID", "user_behavior_pipeline");
        this.clickhouseUrl = System.getenv().getOrDefault("CLICKHOUSE_URL", "jdbc:clickhouse://localhost:8123/default");
        this.clickhouseUser = System.getenv().getOrDefault("CLICKHOUSE_USER", "default");
        this.clickhousePassword = System.getenv().getOrDefault("CLICKHOUSE_PASSWORD", "");
        this.checkpointIntervalMs = Long.parseLong(System.getenv().getOrDefault("CHECKPOINT_INTERVAL_MS", "180000"));
        this.checkpointTimeoutMin = Integer.parseInt(System.getenv().getOrDefault("CHECKPOINT_TIMEOUT_MIN", "10"));
        this.allowedLatenessMin = Integer.parseInt(System.getenv().getOrDefault("ALLOWED_LATENESS_MIN", "5"));
        this.windowSizeMin = Integer.parseInt(System.getenv().getOrDefault("WINDOW_SIZE_MIN", "1"));
        this.stateTtlHours = Integer.parseInt(System.getenv().getOrDefault("STATE_TTL_HOURS", "24"));
        this.bloomFilterExpectedInsertions = Integer.parseInt(System.getenv().getOrDefault("BLOOM_FILTER_EXPECTED_INSERTIONS", "10000000"));
        this.bloomFilterFpp = Double.parseDouble(System.getenv().getOrDefault("BLOOM_FILTER_FPP", "0.001"));
    }

    public String getKafkaBrokers() { return kafkaBrokers; }
    public String getKafkaTopic() { return kafkaTopic; }
    public String getKafkaGroupId() { return kafkaGroupId; }
    public String getClickhouseUrl() { return clickhouseUrl; }
    public String getClickhouseUser() { return clickhouseUser; }
    public String getClickhousePassword() { return clickhousePassword; }
    public long getCheckpointIntervalMs() { return checkpointIntervalMs; }
    public int getCheckpointTimeoutMin() { return checkpointTimeoutMin; }
    public int getAllowedLatenessMin() { return allowedLatenessMin; }
    public int getWindowSizeMin() { return windowSizeMin; }
    public int getStateTtlHours() { return stateTtlHours; }
    public int getBloomFilterExpectedInsertions() { return bloomFilterExpectedInsertions; }
    public double getBloomFilterFpp() { return bloomFilterFpp; }
}
