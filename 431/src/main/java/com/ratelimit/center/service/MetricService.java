package com.ratelimit.center.service;

import com.alibaba.csp.sentinel.node.ClusterNode;
import com.alibaba.csp.sentinel.slotchain.ResourceWrapper;
import com.alibaba.csp.sentinel.slots.clusterbuilder.ClusterBuilderSlot;
import com.alibaba.fastjson.JSON;
import com.ratelimit.center.common.RateLimitConstants;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
public class MetricService {

    @Autowired
    private MeterRegistry meterRegistry;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    private final Map<String, Counter> passCounters = new ConcurrentHashMap<>();
    private final Map<String, Counter> blockCounters = new ConcurrentHashMap<>();
    private final Map<String, Counter> exceptionCounters = new ConcurrentHashMap<>();
    private final Map<String, Timer> rtTimers = new ConcurrentHashMap<>();
    private final Map<String, Gauge> currentQpsGauges = new ConcurrentHashMap<>();

    private final Map<String, MetricAccumulator> minuteAccumulators = new ConcurrentHashMap<>();
    private final Map<String, MetricAccumulator> hourAccumulators = new ConcurrentHashMap<>();

    private static final DateTimeFormatter MINUTE_FORMAT = DateTimeFormatter.ofPattern("yyyyMMddHHmm");
    private static final DateTimeFormatter HOUR_FORMAT = DateTimeFormatter.ofPattern("yyyyMMddHH");

    @Data
    public static class MetricAccumulator {
        private String resource;
        private String serviceName;
        private AtomicLong passCount = new AtomicLong(0);
        private AtomicLong blockCount = new AtomicLong(0);
        private AtomicLong exceptionCount = new AtomicLong(0);
        private AtomicLong rtSum = new AtomicLong(0);
        private AtomicLong rtCount = new AtomicLong(0);
        private AtomicLong maxRt = new AtomicLong(0);
        private AtomicLong minRt = new AtomicLong(Long.MAX_VALUE);
        private String timestamp;

        public void recordPass() {
            passCount.incrementAndGet();
        }

        public void recordBlock() {
            blockCount.incrementAndGet();
        }

        public void recordException() {
            exceptionCount.incrementAndGet();
        }

        public void recordRt(long rtMs) {
            rtSum.addAndGet(rtMs);
            rtCount.incrementAndGet();
            maxRt.accumulateAndGet(rtMs, Math::max);
            minRt.accumulateAndGet(rtMs, Math::min);
        }

        public double getAvgRt() {
            long count = rtCount.get();
            return count > 0 ? (double) rtSum.get() / count : 0;
        }

        public Map<String, Object> toMap() {
            Map<String, Object> map = new LinkedHashMap<>();
            map.put("resource", resource);
            map.put("serviceName", serviceName);
            map.put("passCount", passCount.get());
            map.put("blockCount", blockCount.get());
            map.put("exceptionCount", exceptionCount.get());
            map.put("rtSum", rtSum.get());
            map.put("rtCount", rtCount.get());
            map.put("avgRt", getAvgRt());
            map.put("maxRt", maxRt.get());
            long min = minRt.get();
            map.put("minRt", min == Long.MAX_VALUE ? 0 : min);
            map.put("timestamp", timestamp);
            map.put("aggregateTime", System.currentTimeMillis());
            return map;
        }
    }

    @Data
    public static class AggregatedMetric {
        private String resource;
        private String serviceName;
        private long passCount;
        private long blockCount;
        private long exceptionCount;
        private double avgRt;
        private long maxRt;
        private long minRt;
        private String period;
        private String granularity;
        private long timestamp;

        public double getBlockRate() {
            long total = passCount + blockCount;
            return total > 0 ? (double) blockCount / total : 0;
        }
    }

    @PostConstruct
    public void init() {
        log.info("Metric service initialized with pre-aggregation (minute/hour)");
    }

    private MetricAccumulator getOrCreateAccumulator(Map<String, MetricAccumulator> accumulators,
                                                      String key, String resource, String serviceName,
                                                      String timestamp) {
        return accumulators.computeIfAbsent(key, k -> {
            MetricAccumulator acc = new MetricAccumulator();
            acc.setResource(resource);
            acc.setServiceName(serviceName);
            acc.setTimestamp(timestamp);
            return acc;
        });
    }

    private String getMinuteKey(String resource, String serviceName) {
        String minute = LocalDateTime.now().format(MINUTE_FORMAT);
        return serviceName + ":" + resource + ":" + minute;
    }

    private String getHourKey(String resource, String serviceName) {
        String hour = LocalDateTime.now().format(HOUR_FORMAT);
        return serviceName + ":" + resource + ":" + hour;
    }

    public void recordPass(String resource, String serviceName) {
        String key = serviceName + ":" + resource;
        Counter counter = passCounters.computeIfAbsent(key, k ->
                Counter.builder("sentinel_pass_total")
                        .description("Total number of passed requests")
                        .tag("resource", resource)
                        .tag("service", serviceName)
                        .register(meterRegistry)
        );
        counter.increment();

        String minuteKey = getMinuteKey(resource, serviceName);
        String minute = LocalDateTime.now().format(MINUTE_FORMAT);
        getOrCreateAccumulator(minuteAccumulators, minuteKey, resource, serviceName, minute).recordPass();

        String hourKey = getHourKey(resource, serviceName);
        String hour = LocalDateTime.now().format(HOUR_FORMAT);
        getOrCreateAccumulator(hourAccumulators, hourKey, resource, serviceName, hour).recordPass();
    }

    public void recordBlock(String resource, String serviceName, String ruleType) {
        String key = serviceName + ":" + resource;
        Counter counter = blockCounters.computeIfAbsent(key, k ->
                Counter.builder("sentinel_block_total")
                        .description("Total number of blocked requests")
                        .tag("resource", resource)
                        .tag("service", serviceName)
                        .tag("rule_type", ruleType)
                        .register(meterRegistry)
        );
        counter.increment();

        String minuteKey = getMinuteKey(resource, serviceName);
        String minute = LocalDateTime.now().format(MINUTE_FORMAT);
        getOrCreateAccumulator(minuteAccumulators, minuteKey, resource, serviceName, minute).recordBlock();

        String hourKey = getHourKey(resource, serviceName);
        String hour = LocalDateTime.now().format(HOUR_FORMAT);
        getOrCreateAccumulator(hourAccumulators, hourKey, resource, serviceName, hour).recordBlock();
    }

    public void recordException(String resource, String serviceName, String exceptionType) {
        String key = serviceName + ":" + resource;
        Counter counter = exceptionCounters.computeIfAbsent(key, k ->
                Counter.builder("sentinel_exception_total")
                        .description("Total number of exceptions")
                        .tag("resource", resource)
                        .tag("service", serviceName)
                        .tag("exception_type", exceptionType)
                        .register(meterRegistry)
        );
        counter.increment();

        String minuteKey = getMinuteKey(resource, serviceName);
        String minute = LocalDateTime.now().format(MINUTE_FORMAT);
        getOrCreateAccumulator(minuteAccumulators, minuteKey, resource, serviceName, minute).recordException();

        String hourKey = getHourKey(resource, serviceName);
        String hour = LocalDateTime.now().format(HOUR_FORMAT);
        getOrCreateAccumulator(hourAccumulators, hourKey, resource, serviceName, hour).recordException();
    }

    public void recordRt(String resource, String serviceName, long rtMs) {
        String key = serviceName + ":" + resource;
        Timer timer = rtTimers.computeIfAbsent(key, k ->
                Timer.builder("sentinel_rt_seconds")
                        .description("Request response time")
                        .tag("resource", resource)
                        .tag("service", serviceName)
                        .publishPercentiles(0.5, 0.9, 0.95, 0.99)
                        .register(meterRegistry)
        );
        timer.record(rtMs, TimeUnit.MILLISECONDS);

        String minuteKey = getMinuteKey(resource, serviceName);
        String minute = LocalDateTime.now().format(MINUTE_FORMAT);
        getOrCreateAccumulator(minuteAccumulators, minuteKey, resource, serviceName, minute).recordRt(rtMs);

        String hourKey = getHourKey(resource, serviceName);
        String hour = LocalDateTime.now().format(HOUR_FORMAT);
        getOrCreateAccumulator(hourAccumulators, hourKey, resource, serviceName, hour).recordRt(rtMs);
    }

    @Scheduled(fixedRate = 5000)
    public void updateResourceMetrics() {
        try {
            Map<ResourceWrapper, ClusterNode> clusterNodeMap = ClusterBuilderSlot.getClusterNodeMap();
            if (clusterNodeMap == null) {
                return;
            }

            clusterNodeMap.forEach((resourceWrapper, clusterNode) -> {
                String resource = resourceWrapper.getName();
                updateGauge(resource, "default", clusterNode);
            });
        } catch (Exception e) {
            log.warn("Failed to update resource metrics", e);
        }
    }

    @Scheduled(fixedRate = 60000)
    public void aggregateAndFlushMinuteMetrics() {
        try {
            String currentMinute = LocalDateTime.now().format(MINUTE_FORMAT);
            List<MetricAccumulator> completed = new ArrayList<>();

            Iterator<Map.Entry<String, MetricAccumulator>> it = minuteAccumulators.entrySet().iterator();
            while (it.hasNext()) {
                Map.Entry<String, MetricAccumulator> entry = it.next();
                if (!entry.getKey().endsWith(currentMinute)) {
                    completed.add(entry.getValue());
                    it.remove();
                }
            }

            if (!completed.isEmpty()) {
                flushToRedis(completed, "minute");
                log.debug("Flushed {} minute metric records to Redis", completed.size());
            }
        } catch (Exception e) {
            log.error("Failed to aggregate minute metrics", e);
        }
    }

    @Scheduled(fixedRate = 3600000)
    public void aggregateAndFlushHourMetrics() {
        try {
            String currentHour = LocalDateTime.now().format(HOUR_FORMAT);
            List<MetricAccumulator> completed = new ArrayList<>();

            Iterator<Map.Entry<String, MetricAccumulator>> it = hourAccumulators.entrySet().iterator();
            while (it.hasNext()) {
                Map.Entry<String, MetricAccumulator> entry = it.next();
                if (!entry.getKey().endsWith(currentHour)) {
                    completed.add(entry.getValue());
                    it.remove();
                }
            }

            if (!completed.isEmpty()) {
                flushToRedis(completed, "hour");
                log.debug("Flushed {} hour metric records to Redis", completed.size());
            }
        } catch (Exception e) {
            log.error("Failed to aggregate hour metrics", e);
        }
    }

    private void flushToRedis(List<MetricAccumulator> accumulators, String granularity) {
        try {
            String key = granularity.equals("minute")
                    ? RateLimitConstants.REDIS_METRIC_AGGREGATE_MINUTE
                    : RateLimitConstants.REDIS_METRIC_AGGREGATE_HOUR;

            for (MetricAccumulator acc : accumulators) {
                String hashKey = acc.getServiceName() + ":" + acc.getResource() + ":" + acc.getTimestamp();
                String json = JSON.toJSONString(acc.toMap());
                stringRedisTemplate.opsForHash().put(key, hashKey, json);
            }

            Calendar cal = Calendar.getInstance();
            if (granularity.equals("minute")) {
                cal.add(Calendar.HOUR, 2);
            } else {
                cal.add(Calendar.DAY_OF_MONTH, 7);
            }
            stringRedisTemplate.expireAt(key, cal.getTime());

        } catch (Exception e) {
            log.error("Failed to flush metrics to Redis", e);
        }
    }

    private void updateGauge(String resource, String serviceName, ClusterNode node) {
        String key = serviceName + ":" + resource;
        try {
            currentQpsGauges.computeIfAbsent(key + ":pass", k ->
                    Gauge.builder("sentinel_pass_qps", node, ClusterNode::passQps)
                            .description("Current pass QPS")
                            .tag("resource", resource)
                            .tag("service", serviceName)
                            .strongReference(true)
                            .register(meterRegistry)
            );

            currentQpsGauges.computeIfAbsent(key + ":block", k ->
                    Gauge.builder("sentinel_block_qps", node, ClusterNode::blockQps)
                            .description("Current block QPS")
                            .tag("resource", resource)
                            .tag("service", serviceName)
                            .strongReference(true)
                            .register(meterRegistry)
            );

            currentQpsGauges.computeIfAbsent(key + ":exception", k ->
                    Gauge.builder("sentinel_exception_qps", node, ClusterNode::exceptionQps)
                            .description("Current exception QPS")
                            .tag("resource", resource)
                            .tag("service", serviceName)
                            .strongReference(true)
                            .register(meterRegistry)
            );

            currentQpsGauges.computeIfAbsent(key + ":rt", k ->
                    Gauge.builder("sentinel_rt_avg", node, ClusterNode::avgRt)
                            .description("Average response time")
                            .tag("resource", resource)
                            .tag("service", serviceName)
                            .strongReference(true)
                            .register(meterRegistry)
            );

            currentQpsGauges.computeIfAbsent(key + ":thread", k ->
                    Gauge.builder("sentinel_thread_count", node, ClusterNode::curThreadNum)
                            .description("Current thread count")
                            .tag("resource", resource)
                            .tag("service", serviceName)
                            .strongReference(true)
                            .register(meterRegistry)
            );
        } catch (Exception e) {
            log.warn("Failed to update gauge for resource: {}", resource, e);
        }
    }

    public Map<String, Object> getResourceMetrics(String resource) {
        ClusterNode node = ClusterBuilderSlot.getClusterNode(resource);
        if (node == null) {
            return null;
        }

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("resource", resource);
        metrics.put("passQps", node.passQps());
        metrics.put("blockQps", node.blockQps());
        metrics.put("exceptionQps", node.exceptionQps());
        metrics.put("totalQps", node.totalQps());
        metrics.put("avgRt", node.avgRt());
        metrics.put("minRt", node.minRt());
        metrics.put("curThreadNum", node.curThreadNum());
        metrics.put("totalPass", node.totalPass());
        metrics.put("totalBlock", node.totalBlock());
        metrics.put("totalException", node.totalException());

        return metrics;
    }

    public Map<String, Map<String, Object>> getAllResourceMetrics() {
        Map<ResourceWrapper, ClusterNode> clusterNodeMap = ClusterBuilderSlot.getClusterNodeMap();
        if (clusterNodeMap == null) {
            return new LinkedHashMap<>();
        }

        Map<String, Map<String, Object>> allMetrics = new LinkedHashMap<>();
        clusterNodeMap.forEach((resourceWrapper, clusterNode) -> {
            String resource = resourceWrapper.getName();
            allMetrics.put(resource, getResourceMetrics(resource));
        });

        return allMetrics;
    }

    public List<AggregatedMetric> queryMinuteMetrics(String serviceName, String resource,
                                                      LocalDateTime startTime, LocalDateTime endTime) {
        return queryAggregatedMetrics(serviceName, resource, startTime, endTime, "minute");
    }

    public List<AggregatedMetric> queryHourMetrics(String serviceName, String resource,
                                                    LocalDateTime startTime, LocalDateTime endTime) {
        return queryAggregatedMetrics(serviceName, resource, startTime, endTime, "hour");
    }

    public List<AggregatedMetric> queryAggregatedMetrics(String serviceName, String resource,
                                                          LocalDateTime startTime, LocalDateTime endTime,
                                                          String granularity) {
        List<AggregatedMetric> result = new ArrayList<>();
        try {
            String key = granularity.equals("minute")
                    ? RateLimitConstants.REDIS_METRIC_AGGREGATE_MINUTE
                    : RateLimitConstants.REDIS_METRIC_AGGREGATE_HOUR;

            String prefix = (serviceName != null ? serviceName : "*") + ":"
                    + (resource != null ? resource : "*") + ":";

            Map<Object, Object> entries = stringRedisTemplate.opsForHash().entries(key);
            DateTimeFormatter formatter = granularity.equals("minute") ? MINUTE_FORMAT : HOUR_FORMAT;

            for (Map.Entry<Object, Object> entry : entries.entrySet()) {
                String hashKey = (String) entry.getKey();
                if (!hashKey.startsWith(prefix.replace("*", ""))) continue;

                AggregatedMetric metric = JSON.parseObject((String) entry.getValue(), AggregatedMetric.class);
                if (metric == null) continue;

                if (startTime != null) {
                    LocalDateTime metricTime = LocalDateTime.parse(metric.getPeriod(), formatter);
                    if (metricTime.isBefore(startTime)) continue;
                }
                if (endTime != null) {
                    LocalDateTime metricTime = LocalDateTime.parse(metric.getPeriod(), formatter);
                    if (metricTime.isAfter(endTime)) continue;
                }

                metric.setGranularity(granularity);
                result.add(metric);
            }

            result.sort(Comparator.comparing(AggregatedMetric::getPeriod));

        } catch (Exception e) {
            log.error("Failed to query aggregated metrics", e);
        }
        return result;
    }

    public Map<String, Object> getAggregatedStats(String serviceName, String granularity,
                                                   LocalDateTime startTime, LocalDateTime endTime) {
        List<AggregatedMetric> metrics = queryAggregatedMetrics(
                serviceName, null, startTime, endTime, granularity);

        long totalPass = metrics.stream().mapToLong(AggregatedMetric::getPassCount).sum();
        long totalBlock = metrics.stream().mapToLong(AggregatedMetric::getBlockCount).sum();
        long totalException = metrics.stream().mapToLong(AggregatedMetric::getExceptionCount).sum();
        double avgRt = metrics.stream().mapToDouble(AggregatedMetric::getAvgRt).average().orElse(0);

        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("granularity", granularity);
        stats.put("totalRecords", metrics.size());
        stats.put("totalPass", totalPass);
        stats.put("totalBlock", totalBlock);
        stats.put("totalException", totalException);
        stats.put("avgRt", avgRt);
        stats.put("blockRate", totalPass + totalBlock > 0 ? (double) totalBlock / (totalPass + totalBlock) : 0);

        Map<String, List<AggregatedMetric>> byResource = new LinkedHashMap<>();
        for (AggregatedMetric m : metrics) {
            byResource.computeIfAbsent(m.getResource(), k -> new ArrayList<>()).add(m);
        }
        stats.put("byResource", byResource);

        return stats;
    }

    public Map<String, Object> getCurrentAccumulatorStatus() {
        Map<String, Object> status = new LinkedHashMap<>();
        status.put("minuteAccumulatorCount", minuteAccumulators.size());
        status.put("hourAccumulatorCount", hourAccumulators.size());
        status.put("minuteAccumulators", new ArrayList<>(minuteAccumulators.values()));
        return status;
    }
}
