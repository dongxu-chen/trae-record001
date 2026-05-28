package com.mqmonitor.exporter;

import com.mqmonitor.common.model.QueueMetrics;
import com.mqmonitor.collector.MetricsManager;
import io.micrometer.core.instrument.*;
import io.micrometer.prometheus.PrometheusConfig;
import io.micrometer.prometheus.PrometheusMeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class PrometheusExporter {
    private static final Logger logger = LoggerFactory.getLogger(PrometheusExporter.class);

    private final PrometheusMeterRegistry registry;
    private final MetricsManager metricsManager;
    private final MessageTraceManager traceManager;
    private final MessageTypeAnalyzer typeAnalyzer;
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(3);

    private final ConcurrentHashMap<String, Gauge> gaugeCache = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Counter> counterCache = new ConcurrentHashMap<>();

    public PrometheusExporter() {
        this.metricsManager = MetricsManager.getInstance();
        this.traceManager = MessageTraceManager.getInstance();
        this.typeAnalyzer = MessageTypeAnalyzer.getInstance();
        this.registry = new PrometheusMeterRegistry(PrometheusConfig.DEFAULT);
        initializeMetrics();
    }

    private void initializeMetrics() {
        logger.info("Initializing Prometheus exporter...");
    }

    public void startExport(long intervalMs) {
        scheduler.scheduleAtFixedRate(this::exportMetrics, 0, intervalMs, TimeUnit.MILLISECONDS);
        logger.info("Started Prometheus export with interval: {}ms", intervalMs);
    }

    public void exportMetrics() {
        List<QueueMetrics> allMetrics = metricsManager.getAllMetrics();
        for (QueueMetrics metric : allMetrics) {
            exportQueueMetrics(metric);
        }
        exportTraceMetrics();
        exportAnalysisMetrics();
    }

    private void exportTraceMetrics() {
        Map<String, Object> stats = traceManager.getStats();

        Tags baseTags = Tags.empty();

        gauge("mq_trace_active", "Number of active message traces", baseTags,
                ((Number) stats.getOrDefault("activeTraces", 0)).doubleValue());
        gauge("mq_trace_completed", "Number of completed message traces", baseTags,
                ((Number) stats.getOrDefault("completedTraces", 0)).doubleValue());
        gauge("mq_trace_total", "Total number of message traces", baseTags,
                ((Number) stats.getOrDefault("totalTraces", 0)).doubleValue());
        gauge("mq_trace_sample_rate", "Message trace sampling rate", baseTags,
                ((Number) stats.getOrDefault("sampleRate", 0)).doubleValue());
        gauge("mq_trace_enabled", "Whether message tracing is enabled", baseTags,
                (Boolean) stats.getOrDefault("enabled", false) ? 1 : 0);
        gauge("mq_trace_avg_latency_ms", "Average end-to-end latency of traced messages", baseTags,
                ((Number) stats.getOrDefault("averageEndToEndLatencyMs", 0)).doubleValue());
        gauge("mq_trace_success_rate", "Message trace success rate", baseTags,
                ((Number) stats.getOrDefault("successRate", 0)).doubleValue());
        gauge("mq_trace_failed", "Number of failed message traces", baseTags,
                ((Number) stats.getOrDefault("failureCount", 0)).doubleValue());
    }

    private void exportAnalysisMetrics() {
        Map<String, Object> stats = typeAnalyzer.getStats();

        Tags baseTags = Tags.empty();

        gauge("mq_analysis_types", "Number of distinct message types being analyzed", baseTags,
                ((Number) stats.getOrDefault("messageTypes", 0)).doubleValue());
        gauge("mq_analysis_slow_threshold_ms", "Slow message threshold in milliseconds", baseTags,
                ((Number) stats.getOrDefault("slowThresholdMs", 0)).doubleValue());
        gauge("mq_analysis_sampling_rate", "Message analysis sampling rate", baseTags,
                ((Number) stats.getOrDefault("samplingRate", 0)).doubleValue());
        gauge("mq_analysis_enabled", "Whether message type analysis is enabled", baseTags,
                (Boolean) stats.getOrDefault("enabled", false) ? 1 : 0);
        gauge("mq_analysis_total_messages", "Total messages sampled for analysis", baseTags,
                ((Number) stats.getOrDefault("totalMessagesSampled", 0)).doubleValue());
        gauge("mq_analysis_slow_messages_estimated", "Estimated number of slow messages", baseTags,
                ((Number) stats.getOrDefault("estimatedSlowMessages", 0)).doubleValue());
        gauge("mq_analysis_critical_types", "Number of message types with CRITICAL severity", baseTags,
                ((Number) stats.getOrDefault("criticalTypes", 0)).doubleValue());
        gauge("mq_analysis_warning_types", "Number of message types with WARNING severity", baseTags,
                ((Number) stats.getOrDefault("warningTypes", 0)).doubleValue());
        gauge("mq_analysis_notice_types", "Number of message types with NOTICE severity", baseTags,
                ((Number) stats.getOrDefault("noticeTypes", 0)).doubleValue());
        gauge("mq_analysis_global_avg_processing_ms", "Global average processing time", baseTags,
                ((Number) stats.getOrDefault("globalAverageProcessingMs", 0)).doubleValue());

        List<MessageTypeAnalysis> slowTypes = typeAnalyzer.getSlowMessageTypes(10);
        for (MessageTypeAnalysis analysis : slowTypes) {
            if (analysis.getMessageType() == null || analysis.getMessageType().isEmpty()) continue;

            Tags typeTags = Tags.of(
                    "mq_type", analysis.getMqType() != null ? analysis.getMqType().name().toLowerCase() : "unknown",
                    "cluster", analysis.getClusterName() != null ? analysis.getClusterName() : "unknown",
                    "topic", analysis.getTopic() != null ? analysis.getTopic() : "unknown",
                    "consumer_group", analysis.getConsumerGroup() != null ? analysis.getConsumerGroup() : "unknown",
                    "message_type", analysis.getMessageType()
            );

            gauge("mq_analysis_type_avg_processing_ms", "Average processing time by message type", typeTags,
                    analysis.getAverageProcessingTimeMs());
            gauge("mq_analysis_type_p99_processing_ms", "P99 processing time by message type", typeTags,
                    analysis.getP99ProcessingTimeMs());
            gauge("mq_analysis_type_slow_ratio", "Slow message ratio by message type", typeTags,
                    analysis.getSlowMessageRatio());
            gauge("mq_analysis_type_anomaly_score", "Anomaly score by message type", typeTags,
                    analysis.getAnomalyScore());
            gauge("mq_analysis_type_total_messages", "Total messages by type", typeTags,
                    analysis.getTotalMessages());
            gauge("mq_analysis_type_failure_rate", "Failure rate by message type", typeTags,
                    analysis.getFailureRate());
        }
    }

    private void exportQueueMetrics(QueueMetrics metric) {
        String cluster = metric.getClusterName();
        String topic = metric.getTopic();
        String group = metric.getConsumerGroup();
        String mqType = metric.getMqType().name().toLowerCase();

        Tags baseTags = Tags.of(
                "mq_type", mqType,
                "cluster", cluster,
                "topic", topic
        );

        if (group != null && !group.isEmpty()) {
            baseTags = baseTags.and("consumer_group", group);
        }

        gauge("mq_latency_produce_ms", "Produce latency in milliseconds", baseTags, metric.getProduceLatencyMs());
        gauge("mq_latency_consume_ms", "Consume latency in milliseconds", baseTags, metric.getConsumeLatencyMs());
        gauge("mq_latency_end_to_end_ms", "End-to-end latency in milliseconds", baseTags, metric.getEndToEndLatencyMs());
        gauge("mq_latency_p50_ms", "P50 (median) end-to-end latency in milliseconds", baseTags, metric.getP50LatencyMs());
        gauge("mq_latency_p95_ms", "P95 end-to-end latency in milliseconds", baseTags, metric.getP95LatencyMs());
        gauge("mq_latency_p99_ms", "P99 end-to-end latency in milliseconds", baseTags, metric.getP99LatencyMs());
        gauge("mq_backlog_size", "Current backlog size", baseTags, metric.getBacklogSize());
        gauge("mq_consumer_lag", "Consumer lag", baseTags, metric.getConsumerLag());
        gauge("mq_throughput_produce", "Produce throughput messages per second", baseTags, metric.getProduceThroughput());
        gauge("mq_throughput_consume", "Consume throughput messages per second", baseTags, metric.getConsumeThroughput());
        gauge("mq_monotonic_clock_enabled", "Whether monotonic clock is used for latency measurement",
                baseTags, metric.isUseMonotonicClock() ? 1 : 0);
        gauge("mq_clock_offset_ns", "Clock offset in nanoseconds for end-to-end latency", baseTags,
                metric.getClockOffsetNs());
        counter("mq_messages_produced_total", "Total messages produced", baseTags, metric.getMessagesProduced());
        counter("mq_messages_consumed_total", "Total messages consumed", baseTags, metric.getMessagesConsumed());
    }

    private void gauge(String name, String description, Tags tags, double value) {
        String key = name + tags.toString();
        Gauge gauge = gaugeCache.computeIfAbsent(key, k ->
                Gauge.builder(name, () -> value)
                        .description(description)
                        .tags(tags)
                        .register(registry)
        );
    }

    private void counter(String name, String description, Tags tags, double value) {
        String key = name + tags.toString();
        Counter counter = counterCache.computeIfAbsent(key, k ->
                Counter.builder(name)
                        .description(description)
                        .tags(tags)
                        .register(registry)
        );
        double current = counter.count();
        if (value > current) {
            counter.increment(value - current);
        }
    }

    public String scrape() {
        return registry.scrape();
    }

    public PrometheusMeterRegistry getRegistry() {
        return registry;
    }

    public void shutdown() {
        scheduler.shutdown();
        registry.close();
    }
}
