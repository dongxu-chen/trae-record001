package com.mqmonitor.collector;

import com.mqmonitor.common.config.AlertConfig;
import com.mqmonitor.common.config.MQClusterConfig;
import com.mqmonitor.common.config.PredictionConfig;
import com.mqmonitor.common.model.QueueMetrics;
import com.mqmonitor.common.model.TimeSeriesPoint;

import java.util.List;
import java.util.Set;

public class MetricsManager {
    private static MetricsManager instance;
    private final MetricsCollectorService collectorService;
    private AlertConfig alertConfig;
    private PredictionConfig predictionConfig;

    private MetricsManager() {
        this.collectorService = new MetricsCollectorService();
        this.alertConfig = new AlertConfig();
        this.predictionConfig = new PredictionConfig();
    }

    public static synchronized MetricsManager getInstance() {
        if (instance == null) {
            instance = new MetricsManager();
        }
        return instance;
    }

    public void initialize(List<MQClusterConfig> clusterConfigs, long collectionIntervalMs) {
        for (MQClusterConfig config : clusterConfigs) {
            switch (config.getMqType()) {
                case KAFKA:
                    collectorService.addKafkaCluster(config);
                    break;
                case RABBITMQ:
                    collectorService.addRabbitMQCluster(config);
                    break;
                case ROCKETMQ:
                    collectorService.addRocketMQCluster(config);
                    break;
            }
        }
        collectorService.startCollection(collectionIntervalMs);
    }

    public MetricsCollectorService getCollectorService() {
        return collectorService;
    }

    public List<QueueMetrics> getAllMetrics() {
        return collectorService.getAllLatestMetrics();
    }

    public List<QueueMetrics> getMetrics(String clusterName, String topic, String consumerGroup) {
        return collectorService.getLatestMetrics(clusterName, topic, consumerGroup);
    }

    public List<TimeSeriesPoint> getBacklogHistory(String clusterName, String topic, String consumerGroup,
                                                   long startTime, long endTime) {
        return collectorService.getBacklogHistory(clusterName, topic, consumerGroup, startTime, endTime);
    }

    public List<TimeSeriesPoint> getLatencyHistory(String clusterName, String topic, String consumerGroup,
                                                   long startTime, long endTime) {
        return collectorService.getLatencyHistory(clusterName, topic, consumerGroup, startTime, endTime);
    }

    public Set<String> getKafkaTopics(String clusterName) {
        return collectorService.getKafkaClients().get(clusterName).listTopics();
    }

    public Set<String> getKafkaConsumerGroups(String clusterName) {
        return collectorService.getKafkaClients().get(clusterName).listConsumerGroups();
    }

    public AlertConfig getAlertConfig() { return alertConfig; }
    public void setAlertConfig(AlertConfig alertConfig) { this.alertConfig = alertConfig; }
    public PredictionConfig getPredictionConfig() { return predictionConfig; }
    public void setPredictionConfig(PredictionConfig predictionConfig) { this.predictionConfig = predictionConfig; }

    public void shutdown() {
        collectorService.shutdown();
    }
}
