package com.drill.platform.engine;

import com.drill.platform.model.DrillResult;
import com.drill.platform.model.TrafficProfile;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
public class TrafficSimulator {

    private final TrafficProfile profile;
    private final ExecutorService executor;
    private final RequestExecutor requestExecutor;
    private volatile boolean running;
    private final AtomicInteger totalRequests = new AtomicInteger(0);
    private final AtomicInteger successRequests = new AtomicInteger(0);
    private final AtomicInteger blockedRequests = new AtomicInteger(0);
    private final AtomicInteger failedRequests = new AtomicInteger(0);
    private final AtomicInteger degradedRequests = new AtomicInteger(0);
    private final List<Long> responseTimes = Collections.synchronizedList(new ArrayList<>());
    private final List<DrillResult.MetricPoint> metricPoints = Collections.synchronizedList(new ArrayList<>());
    private final List<Double> errorRates = Collections.synchronizedList(new ArrayList<>());
    private final List<DrillResult.TimeBucketDetail> timeBuckets = Collections.synchronizedList(new ArrayList<>());
    private final AtomicLong startTime = new AtomicLong(0);
    private final AtomicLong peakTime = new AtomicLong(0);
    private final AtomicInteger bucketSuccess = new AtomicInteger(0);
    private final AtomicInteger bucketBlocked = new AtomicInteger(0);
    private final AtomicInteger bucketFailed = new AtomicInteger(0);
    private final List<Long> bucketResponseTimes = Collections.synchronizedList(new ArrayList<>());

    public TrafficSimulator(TrafficProfile profile, RequestExecutor requestExecutor) {
        this.profile = profile;
        this.requestExecutor = requestExecutor;
        this.executor = Executors.newFixedThreadPool(profile.getConcurrentUsers());
    }

    public DrillResult simulate() {
        running = true;
        startTime.set(System.currentTimeMillis());
        resetCounters();

        try {
            List<Future<?>> futures = new ArrayList<>();
            TrafficCurveGenerator curveGenerator = new TrafficCurveGenerator(profile);

            while (running) {
                int elapsed = (int) ((System.currentTimeMillis() - startTime.get()) / 1000);
                int totalDuration = profile.getRampUpSeconds() + profile.getSustainSeconds() + profile.getRampDownSeconds();

                if (elapsed >= totalDuration) {
                    break;
                }

                int currentQps = curveGenerator.getQpsAtSecond(elapsed);
                int intervalMs = currentQps > 0 ? 1000 / currentQps : 1000;

                for (int i = 0; i < currentQps && running; i++) {
                    final int second = elapsed;
                    futures.add(executor.submit(() -> {
                        if (!running) return;
                        executeRequest(second);
                    }));
                    if (i < currentQps - 1) {
                        Thread.sleep(intervalMs);
                    }
                }

                collectMetrics(elapsed);
                Thread.sleep(1000);
            }

            for (Future<?> future : futures) {
                try {
                    future.get(30, TimeUnit.SECONDS);
                } catch (Exception e) {
                    log.warn("Future task exception", e);
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            running = false;
            executor.shutdown();
        }

        return buildResult();
    }

    private void executeRequest(int second) {
        long requestStart = System.currentTimeMillis();
        try {
            RequestResult result = requestExecutor.execute(profile);
            long responseTime = System.currentTimeMillis() - requestStart;
            responseTimes.add(responseTime);
            bucketResponseTimes.add(responseTime);
            totalRequests.incrementAndGet();

            switch (result.getStatus()) {
                case SUCCESS:
                    successRequests.incrementAndGet();
                    bucketSuccess.incrementAndGet();
                    break;
                case BLOCKED:
                    blockedRequests.incrementAndGet();
                    bucketBlocked.incrementAndGet();
                    break;
                case DEGRADED:
                    degradedRequests.incrementAndGet();
                    bucketSuccess.incrementAndGet();
                    break;
                case FAILED:
                    failedRequests.incrementAndGet();
                    bucketFailed.incrementAndGet();
                    break;
            }
        } catch (Exception e) {
            long responseTime = System.currentTimeMillis() - requestStart;
            responseTimes.add(responseTime);
            bucketResponseTimes.add(responseTime);
            totalRequests.incrementAndGet();
            failedRequests.incrementAndGet();
            bucketFailed.incrementAndGet();
            log.debug("Request failed: {}", e.getMessage());
        }
    }

    private void collectMetrics(int second) {
        long timestamp = System.currentTimeMillis();
        long elapsed = timestamp - startTime.get();
        double currentQps = totalRequests.get() > 0 ? totalRequests.get() * 1000.0 / elapsed : 0;

        int bucketTotal = bucketSuccess.get() + bucketBlocked.get() + bucketFailed.get();
        double currentErrorRate = bucketTotal > 0 ? bucketFailed.get() * 100.0 / bucketTotal : 0;
        double currentBlockRate = bucketTotal > 0 ? bucketBlocked.get() * 100.0 / bucketTotal : 0;

        String phase = determinePhase(second);

        DrillResult.MetricPoint point = new DrillResult.MetricPoint();
        point.setTimestamp(timestamp);
        point.setQps(currentQps);
        point.setResponseTimeMs(bucketResponseTimes.isEmpty() ? 0 :
                bucketResponseTimes.stream().mapToLong(Long::longValue).average().orElse(0));
        point.setBlockRate(currentBlockRate);
        point.setErrorRate(currentErrorRate);
        point.setSecondOffset(second);
        point.setPhase(phase);
        point.setSuccessCount(bucketSuccess.get());
        point.setBlockedCount(bucketBlocked.get());
        point.setFailedCount(bucketFailed.get());
        metricPoints.add(point);
        errorRates.add(currentErrorRate);

        DrillResult.TimeBucketDetail bucket = new DrillResult.TimeBucketDetail();
        bucket.setBucketId(second);
        bucket.setStartTime(timestamp - 1000);
        bucket.setEndTime(timestamp);
        bucket.setTotalRequests(bucketTotal);
        bucket.setSuccessRequests(bucketSuccess.get());
        bucket.setBlockedRequests(bucketBlocked.get());
        bucket.setFailedRequests(bucketFailed.get());
        bucket.setAvgResponseTimeMs(point.getResponseTimeMs());
        bucket.setErrorRate(currentErrorRate);
        bucket.setBlockRate(currentBlockRate);
        bucket.setPhase(phase);
        timeBuckets.add(bucket);

        if (currentQps > profile.getPeakQps() * 0.8 && peakTime.get() == 0) {
            peakTime.set(timestamp);
        }

        bucketSuccess.set(0);
        bucketBlocked.set(0);
        bucketFailed.set(0);
        bucketResponseTimes.clear();
    }

    private String determinePhase(int second) {
        int rampUp = profile.getRampUpSeconds();
        int sustain = profile.getSustainSeconds();
        if (second < rampUp) return "RAMP_UP";
        if (second < rampUp + sustain) return "SUSTAIN";
        return "RAMP_DOWN";
    }

    private double averageLastN(List<Long> values, int n) {
        int start = Math.max(0, values.size() - n);
        return values.subList(start, values.size()).stream()
                .mapToLong(Long::longValue).average().orElse(0);
    }

    private DrillResult buildResult() {
        DrillResult result = new DrillResult();
        result.setTotalRequests(totalRequests.get());
        result.setSuccessRequests(successRequests.get());
        result.setBlockedRequests(blockedRequests.get());
        result.setFailedRequests(failedRequests.get());
        result.setDegradedRequests(degradedRequests.get());

        if (!responseTimes.isEmpty()) {
            List<Long> sorted = new ArrayList<>(responseTimes);
            Collections.sort(sorted);
            result.setAvgResponseTimeMs((long) sorted.stream().mapToLong(Long::longValue).average().orElse(0));
            result.setMaxResponseTimeMs(sorted.get(sorted.size() - 1));
            result.setMinResponseTimeMs(sorted.get(0));
            result.setP50ResponseTimeMs(percentile(sorted, 0.50));
            result.setP90ResponseTimeMs(percentile(sorted, 0.90));
            result.setP95ResponseTimeMs(percentile(sorted, 0.95));
            result.setP99ResponseTimeMs(percentile(sorted, 0.99));
            result.setResponseTimeStdDev(calculateStdDev(sorted));
        }

        long totalDuration = System.currentTimeMillis() - startTime.get();
        result.setTotalDurationMs(totalDuration);
        result.setActualQps(totalRequests.get() * 1000.0 / totalDuration);
        result.setBlockRate(totalRequests.get() > 0 ? blockedRequests.get() * 100.0 / totalRequests.get() : 0);
        result.setErrorRate(totalRequests.get() > 0 ? failedRequests.get() * 100.0 / totalRequests.get() : 0);
        result.setDegradationRate(totalRequests.get() > 0 ? degradedRequests.get() * 100.0 / totalRequests.get() : 0);
        result.setThroughput(successRequests.get() * 1000.0 / totalDuration);
        result.setRealtimeMetrics(metricPoints);
        result.setTimeBuckets(timeBuckets);

        double peakBlock = 0;
        double peakError = 0;
        int overThreshold = 0;
        long recoveryTime = 0;
        boolean recovered = false;
        List<DrillResult.MetricPoint> recoveryMetrics = new ArrayList<>();

        for (int i = 0; i < metricPoints.size(); i++) {
            DrillResult.MetricPoint p = metricPoints.get(i);
            peakBlock = Math.max(peakBlock, p.getBlockRate());
            peakError = Math.max(peakError, p.getErrorRate());
            if (p.getErrorRate() > 5) overThreshold++;

            if (peakTime.get() > 0 && p.getTimestamp() > peakTime.get() && p.getErrorRate() <= 5 && !recovered) {
                recoveryTime = p.getTimestamp() - peakTime.get();
                recovered = true;
            }

            if (peakTime.get() > 0 && p.getTimestamp() > peakTime.get()) {
                recoveryMetrics.add(p);
            }
        }

        result.setPeakBlockRate(peakBlock);
        result.setPeakErrorRate(peakError);
        result.setOverThresholdSeconds(overThreshold);
        result.setRecoveryTimeMs(recoveryTime);
        result.setAutoRecovered(recovered);
        result.setErrorRateJitter(calculateStdDevDouble(errorRates));
        result.setRecoveryPhaseMetrics(recoveryMetrics);

        return result;
    }

    private double calculateStdDev(List<Long> values) {
        if (values.size() < 2) return 0;
        double mean = values.stream().mapToLong(Long::longValue).average().orElse(0);
        double variance = values.stream()
                .mapToDouble(v -> Math.pow(v - mean, 2))
                .sum() / values.size();
        return Math.sqrt(variance);
    }

    private double calculateStdDevDouble(List<Double> values) {
        if (values.size() < 2) return 0;
        double mean = values.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double variance = values.stream()
                .mapToDouble(v -> Math.pow(v - mean, 2))
                .sum() / values.size();
        return Math.sqrt(variance);
    }

    private long percentile(List<Long> sorted, double pct) {
        int index = (int) Math.ceil(pct * sorted.size()) - 1;
        return sorted.get(Math.max(0, index));
    }

    public void stop() {
        running = false;
    }

    private void resetCounters() {
        totalRequests.set(0);
        successRequests.set(0);
        blockedRequests.set(0);
        failedRequests.set(0);
        degradedRequests.set(0);
        responseTimes.clear();
        metricPoints.clear();
        errorRates.clear();
        timeBuckets.clear();
        peakTime.set(0);
        bucketSuccess.set(0);
        bucketBlocked.set(0);
        bucketFailed.set(0);
        bucketResponseTimes.clear();
    }

    public interface RequestExecutor {
        RequestResult execute(TrafficProfile profile);
    }

    @Data
    public static class RequestResult {
        private RequestStatus status;
        private long responseTimeMs;
        private String responseBody;
        private int httpStatus;

        public enum RequestStatus {
            SUCCESS, BLOCKED, DEGRADED, FAILED
        }

        public static RequestResult success(int httpStatus, String body) {
            RequestResult r = new RequestResult();
            r.setStatus(RequestStatus.SUCCESS);
            r.setHttpStatus(httpStatus);
            r.setResponseBody(body);
            return r;
        }

        public static RequestResult blocked(int httpStatus, String body) {
            RequestResult r = new RequestResult();
            r.setStatus(RequestStatus.BLOCKED);
            r.setHttpStatus(httpStatus);
            r.setResponseBody(body);
            return r;
        }

        public static RequestResult degraded(String body) {
            RequestResult r = new RequestResult();
            r.setStatus(RequestStatus.DEGRADED);
            r.setHttpStatus(200);
            r.setResponseBody(body);
            return r;
        }

        public static RequestResult failed(Exception e) {
            RequestResult r = new RequestResult();
            r.setStatus(RequestStatus.FAILED);
            r.setHttpStatus(500);
            r.setResponseBody(e.getMessage());
            return r;
        }
    }
}
