package com.mqmonitor.collector;

import com.mqmonitor.common.config.MQClusterConfig;
import com.mqmonitor.common.model.QueueMetrics;
import com.mqmonitor.common.model.TimeSeriesPoint;
import com.mqmonitor.common.util.TimeWindow;
import com.mqmonitor.kafka.KafkaMonitorClient;
import com.mqmonitor.rabbitmq.RabbitMQMonitorClient;
import com.mqmonitor.rocketmq.RocketMQMonitorClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class MetricsCollectorService {
    private static final Logger logger = LoggerFactory.getLogger(MetricsCollectorService.class);

    private final Map<String, KafkaMonitorClient> kafkaClients = new ConcurrentHashMap<>();
    private final Map<String, RabbitMQMonitorClient> rabbitMQClients = new ConcurrentHashMap<>();
    private final Map<String, RocketMQMonitorClient> rocketMQClients = new ConcurrentHashMap<>();

    private final Map<String, List<QueueMetrics>> latestMetrics = new ConcurrentHashMap<>();
    private final Map<String, TimeWindow<Double>> backlogHistory = new ConcurrentHashMap<>();
    private final Map<String, TimeWindow<Double>> latencyHistory = new ConcurrentHashMap<>();

    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(4);
    private final long historyWindowMs = TimeUnit.HOURS.toMillis(24);

    public void addKafkaCluster(MQClusterConfig config) {
        KafkaMonitorClient client = new KafkaMonitorClient(config);
        kafkaClients.put(config.getClusterName(), client);
        logger.info("Added Kafka cluster: {}", config.getClusterName());
    }

    public void addRabbitMQCluster(MQClusterConfig config) {
        RabbitMQMonitorClient client = new RabbitMQMonitorClient(config);
        rabbitMQClients.put(config.getClusterName(), client);
        logger.info("Added RabbitMQ cluster: {}", config.getClusterName());
    }

    public void addRocketMQCluster(MQClusterConfig config) {
        RocketMQMonitorClient client = new RocketMQMonitorClient(config);
        rocketMQClients.put(config.getClusterName(), client);
        logger.info("Added RocketMQ cluster: {}", config.getClusterName());
    }

    public void startCollection(long intervalMs) {
        scheduler.scheduleAtFixedRate(this::collectAllMetrics, 0, intervalMs, TimeUnit.MILLISECONDS);
        logger.info("Started metrics collection with interval: {}ms", intervalMs);
    }

    public void collectAllMetrics() {
        logger.debug("Collecting metrics from all clusters...");
        collectKafkaMetrics();
        collectRabbitMQMetrics();
        collectRocketMQMetrics();
    }

    private void collectKafkaMetrics() {
        for (Map.Entry<String, KafkaMonitorClient> entry : kafkaClients.entrySet()) {
            String clusterName = entry.getKey();
            KafkaMonitorClient client = entry.getValue();
            try {
                Set<String> topics = client.listTopics();
                Set<String> consumerGroups = client.listConsumerGroups();

                for (String topic : topics) {
                    for (String consumerGroup : consumerGroups) {
                        List<QueueMetrics> metrics = client.collectMetrics(topic, consumerGroup);
                        updateMetricsCache(clusterName, topic, consumerGroup, metrics);
                    }
                }
            } catch (Exception e) {
                logger.error("Error collecting Kafka metrics from cluster {}: {}", clusterName, e.getMessage());
            }
        }
    }

    private void collectRabbitMQMetrics() {
        for (Map.Entry<String, RabbitMQMonitorClient> entry : rabbitMQClients.entrySet()) {
            String clusterName = entry.getKey();
            RabbitMQMonitorClient client = entry.getValue();
            try {
                List<String> queues = client.listQueues();
                for (String queue : queues) {
                    List<QueueMetrics> metrics = client.collectMetrics(queue);
                    updateMetricsCache(clusterName, queue, null, metrics);
                }
            } catch (Exception e) {
                logger.error("Error collecting RabbitMQ metrics from cluster {}: {}", clusterName, e.getMessage());
            }
        }
    }

    private void collectRocketMQMetrics() {
        for (Map.Entry<String, RocketMQMonitorClient> entry : rocketMQClients.entrySet()) {
            String clusterName = entry.getKey();
            RocketMQMonitorClient client = entry.getValue();
            try {
                Set<String> topics = client.listTopics();
                Set<String> consumerGroups = client.listConsumerGroups();

                for (String topic : topics) {
                    for (String consumerGroup : consumerGroups) {
                        List<QueueMetrics> metrics = client.collectMetrics(topic, consumerGroup);
                        updateMetricsCache(clusterName, topic, consumerGroup, metrics);
                    }
                }
            } catch (Exception e) {
                logger.error("Error collecting RocketMQ metrics from cluster {}: {}", clusterName, e.getMessage());
            }
        }
    }

    private void updateMetricsCache(String clusterName, String topic, String consumerGroup, List<QueueMetrics> metrics) {
        String key = buildKey(clusterName, topic, consumerGroup);
        latestMetrics.put(key, metrics);

        for (QueueMetrics metric : metrics) {
            long timestamp = Instant.now().toEpochMilli();

            getBacklogWindow(key).add((double) metric.getBacklogSize(), timestamp);
            getLatencyWindow(key).add((double) metric.getEndToEndLatencyMs(), timestamp);
        }
    }

    private String buildKey(String clusterName, String topic, String consumerGroup) {
        return clusterName + ":" + topic + (consumerGroup != null ? ":" + consumerGroup : "");
    }

    private TimeWindow<Double> getBacklogWindow(String key) {
        return backlogHistory.computeIfAbsent(key, k -> new TimeWindow<>(historyWindowMs));
    }

    private TimeWindow<Double> getLatencyWindow(String key) {
        return latencyHistory.computeIfAbsent(key, k -> new TimeWindow<>(historyWindowMs));
    }

    public List<QueueMetrics> getLatestMetrics(String clusterName, String topic, String consumerGroup) {
        String key = buildKey(clusterName, topic, consumerGroup);
        return latestMetrics.getOrDefault(key, Collections.emptyList());
    }

    public List<QueueMetrics> getAllLatestMetrics() {
        List<QueueMetrics> allMetrics = new ArrayList<>();
        for (List<QueueMetrics> metrics : latestMetrics.values()) {
            allMetrics.addAll(metrics);
        }
        return allMetrics;
    }

    public List<TimeSeriesPoint> getBacklogHistory(String clusterName, String topic, String consumerGroup, long startTime, long endTime) {
        String key = buildKey(clusterName, topic, consumerGroup);
        TimeWindow<Double> window = backlogHistory.get(key);
        return window != null ? convertToTimeSeries(window.getValues(), startTime, endTime) : Collections.emptyList();
    }

    public List<TimeSeriesPoint> getLatencyHistory(String clusterName, String topic, String consumerGroup, long startTime, long endTime) {
        String key = buildKey(clusterName, topic, consumerGroup);
        TimeWindow<Double> window = latencyHistory.get(key);
        return window != null ? convertToTimeSeries(window.getValues(), startTime, endTime) : Collections.emptyList();
    }

    private List<TimeSeriesPoint> convertToTimeSeries(List<Double> values, long startTime, long endTime) {
        List<TimeSeriesPoint> points = new ArrayList<>();
        long interval = (endTime - startTime) / Math.max(1, values.size() - 1);
        for (int i = 0; i < values.size(); i++) {
            long timestamp = startTime + i * interval;
            points.add(new TimeSeriesPoint(timestamp, values.get(i)));
        }
        return points;
    }

    public Map<String, KafkaMonitorClient> getKafkaClients() { return kafkaClients; }
    public Map<String, RabbitMQMonitorClient> getRabbitMQClients() { return rabbitMQClients; }
    public Map<String, RocketMQMonitorClient> getRocketMQClients() { return rocketMQClients; }
    public Map<String, TimeWindow<Double>> getBacklogHistoryMap() { return backlogHistory; }
    public Map<String, TimeWindow<Double>> getLatencyHistoryMap() { return latencyHistory; }

    public void shutdown() {
        scheduler.shutdown();
        kafkaClients.values().forEach(KafkaMonitorClient::close);
        rabbitMQClients.values().forEach(RabbitMQMonitorClient::close);
        rocketMQClients.values().forEach(RocketMQMonitorClient::close);
    }
}
