package com.tracking.flink.function;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.AnomalyAlert;
import com.tracking.common.model.TrackEvent;
import com.tracking.common.util.IdGenerator;
import org.apache.flink.api.common.state.*;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

import java.util.*;

public class AnomalyDetectionFunction extends KeyedProcessFunction<String, TrackEvent, TrackEvent> {

    private static final Logger LOG = LoggerFactory.getLogger(AnomalyDetectionFunction.class);
    private static final long CHECK_INTERVAL_MS = 60 * 1000L;
    private static final int MAX_HISTORY_WINDOWS = 12;

    private final String redisHost;
    private final int redisPort;
    private final String redisPassword;
    private final int windowMinutes;
    private final int baselineMinutes;

    private transient JedisPool jedisPool;
    private transient MapState<Long, Long> eventCountState;
    private transient ValueState<Long> lastCheckTimeState;
    private transient ValueState<Double> meanState;
    private transient ValueState<Double> stdDevState;
    private transient ListState<Long> historyCountsState;
    private transient ValueState<Long> lastAlertTimeState;

    public AnomalyDetectionFunction(String redisHost, int redisPort, String redisPassword,
                                    int windowMinutes, int baselineMinutes) {
        this.redisHost = redisHost;
        this.redisPort = redisPort;
        this.redisPassword = redisPassword;
        this.windowMinutes = windowMinutes;
        this.baselineMinutes = baselineMinutes;
    }

    @Override
    public void open(Configuration parameters) {
        JedisPoolConfig poolConfig = new JedisPoolConfig();
        poolConfig.setMaxTotal(128);
        poolConfig.setMaxIdle(64);
        poolConfig.setMinIdle(16);
        if (redisPassword != null && !redisPassword.isEmpty()) {
            jedisPool = new JedisPool(poolConfig, redisHost, redisPort, 2000, redisPassword);
        } else {
            jedisPool = new JedisPool(poolConfig, redisHost, redisPort, 2000);
        }

        MapStateDescriptor<Long, Long> countDescriptor = new MapStateDescriptor<>(
            "event-counts", Long.class, Long.class);
        eventCountState = getRuntimeContext().getMapState(countDescriptor);

        ValueStateDescriptor<Long> lastCheckDescriptor = new ValueStateDescriptor<>(
            "last-check-time", Long.class);
        lastCheckTimeState = getRuntimeContext().getState(lastCheckDescriptor);

        ValueStateDescriptor<Double> meanDescriptor = new ValueStateDescriptor<>(
            "baseline-mean", Double.class);
        meanState = getRuntimeContext().getState(meanDescriptor);

        ValueStateDescriptor<Double> stdDevDescriptor = new ValueStateDescriptor<>(
            "baseline-stddev", Double.class);
        stdDevState = getRuntimeContext().getState(stdDevDescriptor);

        ListStateDescriptor<Long> historyDescriptor = new ListStateDescriptor<>(
            "history-counts", Long.class);
        historyCountsState = getRuntimeContext().getListState(historyDescriptor);

        ValueStateDescriptor<Long> lastAlertDescriptor = new ValueStateDescriptor<>(
            "last-alert-time", Long.class);
        lastAlertTimeState = getRuntimeContext().getState(lastAlertDescriptor);
    }

    @Override
    public void processElement(TrackEvent event, Context context, Collector<TrackEvent> collector) throws Exception {
        long windowStart = getWindowStart(event.getTimestamp());
        eventCountState.put(windowStart, eventCountState.contains(windowStart) ? 
            eventCountState.get(windowStart) + 1 : 1L);

        long currentTime = context.timerService().currentProcessingTime();
        Long lastCheckTime = lastCheckTimeState.value();

        if (lastCheckTime == null || (currentTime - lastCheckTime) >= CHECK_INTERVAL_MS) {
            checkAnomaly(currentTime, context, event);
            lastCheckTimeState.update(currentTime);
        }

        context.timerService().registerProcessingTimeTimer(currentTime + CHECK_INTERVAL_MS);

        collector.collect(event);
    }

    @Override
    public void onTimer(long timestamp, OnTimerContext ctx, Collector<TrackEvent> out) throws Exception {
        Long lastCheckTime = lastCheckTimeState.value();
        if (lastCheckTime == null || (timestamp - lastCheckTime) >= CHECK_INTERVAL_MS) {
            checkAnomaly(timestamp, ctx, null);
            lastCheckTimeState.update(timestamp);
        }

        ctx.timerService().registerProcessingTimeTimer(timestamp + CHECK_INTERVAL_MS);
    }

    private long getWindowStart(long timestamp) {
        return (timestamp / (windowMinutes * 60 * 1000L)) * windowMinutes * 60 * 1000L;
    }

    private void checkAnomaly(long currentTime, Context context, TrackEvent sampleEvent) throws Exception {
        long windowEnd = getWindowStart(currentTime);
        long windowStart = windowEnd - windowMinutes * 60 * 1000L;
        long baselineStart = windowEnd - baselineMinutes * 60 * 1000L;

        long currentCount = getCountInRange(windowStart, windowEnd);
        List<Long> baselineCounts = getBaselineCounts(baselineStart, windowStart);

        if (baselineCounts.size() < 5 || currentCount < TrackingConstants.ANOMALY_MIN_EVENTS) {
            updateHistoryState(currentCount);
            return;
        }

        double[] stats = calculateStats(baselineCounts);
        double mean = stats[0];
        double stdDev = stats[1];

        if (stdDev == 0) {
            return;
        }

        double zScore = (currentCount - mean) / stdDev;

        Long lastAlertTime = lastAlertTimeState.value();
        if (lastAlertTime != null && (currentTime - lastAlertTime) < 5 * 60 * 1000L) {
            return;
        }

        String metricName = context.getCurrentKey();
        String[] keyParts = metricName.split(":");
        String dimension = keyParts.length > 1 ? keyParts[0] : "event";
        String dimensionValue = keyParts.length > 1 ? keyParts[1] : metricName;

        AnomalyAlert alert = null;

        if (Math.abs(zScore) >= TrackingConstants.ANOMALY_THRESHOLD_CRITICAL) {
            alert = createAlert(metricName, dimension, dimensionValue, currentCount, mean, zScore,
                windowStart, windowEnd, TrackingConstants.ANOMALY_SEVERITY_CRITICAL);
        } else if (Math.abs(zScore) >= TrackingConstants.ANOMALY_THRESHOLD_HIGH) {
            alert = createAlert(metricName, dimension, dimensionValue, currentCount, mean, zScore,
                windowStart, windowEnd, TrackingConstants.ANOMALY_SEVERITY_HIGH);
        } else if (Math.abs(zScore) >= TrackingConstants.ANOMALY_THRESHOLD_MEDIUM) {
            alert = createAlert(metricName, dimension, dimensionValue, currentCount, mean, zScore,
                windowStart, windowEnd, TrackingConstants.ANOMALY_SEVERITY_MEDIUM);
        } else if (Math.abs(zScore) >= TrackingConstants.ANOMALY_THRESHOLD_LOW) {
            alert = createAlert(metricName, dimension, dimensionValue, currentCount, mean, zScore,
                windowStart, windowEnd, TrackingConstants.ANOMALY_SEVERITY_LOW);
        }

        if (alert != null) {
            saveAlertToRedis(alert);
            if (sampleEvent != null) {
                context.output(new org.apache.flink.util.OutputTag<AnomalyAlert>("anomaly-alerts") {}, alert);
            }
            lastAlertTimeState.update(currentTime);
            LOG.info("Anomaly detected: {} {} zScore={}, mean={}, current={}",
                alert.getAnomalyType(), alert.getSeverity(), zScore, mean, currentCount);
        }

        updateHistoryState(currentCount);
        updateBaselineStats(mean, stdDev);
    }

    private AnomalyAlert createAlert(String metricName, String dimension, String dimensionValue,
                                      double currentCount, double mean, double zScore,
                                      long windowStart, long windowEnd, String severity) {
        String anomalyType = zScore > 0 ? TrackingConstants.ANOMALY_TYPE_SPIKE : TrackingConstants.ANOMALY_TYPE_DROP;
        double deviationPercent = ((currentCount - mean) / mean) * 100;

        Map<String, Object> details = new HashMap<>();
        details.put("window_minutes", windowMinutes);
        details.put("baseline_minutes", baselineMinutes);
        details.put("z_score", zScore);
        details.put("deviation_percent", deviationPercent);

        String description = String.format("%s detected for %s: current=%.0f, baseline=%.2f, deviation=%.2f%%, z-score=%.2f",
            anomalyType.equals(TrackingConstants.ANOMALY_TYPE_SPIKE) ? "Spike" : "Drop",
            metricName, currentCount, mean, deviationPercent, zScore);

        return AnomalyAlert.builder()
                .alertId(IdGenerator.generateEventId())
                .anomalyType(anomalyType)
                .severity(severity)
                .metricName(metricName)
                .dimension(dimension)
                .dimensionValue(dimensionValue)
                .currentValue(currentCount)
                .baselineValue(mean)
                .deviationPercent(deviationPercent)
                .zScore(zScore)
                .windowStartTime(windowStart)
                .windowEndTime(windowEnd)
                .detectionTime(System.currentTimeMillis())
                .description(description)
                .details(details)
                .status("open")
                .build();
    }

    private long getCountInRange(long start, long end) throws Exception {
        long count = 0;
        Iterator<Map.Entry<Long, Long>> iterator = eventCountState.iterator();
        while (iterator.hasNext()) {
            Map.Entry<Long, Long> entry = iterator.next();
            if (entry.getKey() >= start && entry.getKey() < end) {
                count += entry.getValue();
            }
        }
        return count;
    }

    private List<Long> getBaselineCounts(long start, long end) throws Exception {
        List<Long> counts = new ArrayList<>();
        Iterator<Map.Entry<Long, Long>> iterator = eventCountState.iterator();
        while (iterator.hasNext()) {
            Map.Entry<Long, Long> entry = iterator.next();
            if (entry.getKey() >= start && entry.getKey() < end) {
                counts.add(entry.getValue());
            }
        }

        for (Long count : historyCountsState.get()) {
            counts.add(count);
        }

        return counts;
    }

    private double[] calculateStats(List<Long> values) {
        if (values.isEmpty()) {
            return new double[]{0, 0};
        }

        double sum = 0;
        for (long value : values) {
            sum += value;
        }
        double mean = sum / values.size();

        double varianceSum = 0;
        for (long value : values) {
            varianceSum += Math.pow(value - mean, 2);
        }
        double variance = varianceSum / values.size();
        double stdDev = Math.sqrt(variance);

        return new double[]{mean, stdDev};
    }

    private void updateHistoryState(long currentCount) throws Exception {
        List<Long> history = new ArrayList<>();
        for (Long count : historyCountsState.get()) {
            history.add(count);
        }

        history.add(currentCount);
        if (history.size() > MAX_HISTORY_WINDOWS) {
            history = new ArrayList<>(history.subList(history.size() - MAX_HISTORY_WINDOWS, history.size()));
        }

        historyCountsState.clear();
        for (Long count : history) {
            historyCountsState.add(count);
        }
    }

    private void updateBaselineStats(double mean, double stdDev) throws Exception {
        meanState.update(mean);
        stdDevState.update(stdDev);
    }

    private void saveAlertToRedis(AnomalyAlert alert) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = "tracking:anomaly:alert:" + alert.getAlertId();
            jedis.setex(key, 24 * 3600, JSON.toJSONString(alert));

            String listKey = "tracking:anomaly:alerts:" + alert.getSeverity();
            jedis.lpush(listKey, alert.getAlertId());
            jedis.ltrim(listKey, 0, 99);

            String metricKey = "tracking:anomaly:metric:" + alert.getMetricName();
            jedis.setex(metricKey, 24 * 3600, JSON.toJSONString(alert));
        } catch (Exception e) {
            LOG.warn("Failed to save anomaly alert to Redis", e);
        }
    }

    @Override
    public void close() {
        if (jedisPool != null) {
            jedisPool.close();
        }
    }
}
