package com.benchmark.service;

import com.benchmark.dto.*;
import com.benchmark.generator.IdGenerator;
import com.benchmark.generator.IdGeneratorFactory;
import com.benchmark.generator.SamplingUniquenessChecker;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.DoubleAdder;

@Slf4j
@Service
public class StabilityTestService {

    private final SimpMessagingTemplate messagingTemplate;
    private final BaselineService baselineService;
    private final Map<String, StabilityTestReport> reportStore = new ConcurrentHashMap<>();
    private final Map<String, AtomicBoolean> runningTests = new ConcurrentHashMap<>();
    private final Map<String, StabilityTestConfig> activeConfigs = new ConcurrentHashMap<>();

    public StabilityTestService(SimpMessagingTemplate messagingTemplate, BaselineService baselineService) {
        this.messagingTemplate = messagingTemplate;
        this.baselineService = baselineService;
    }

    public String startStabilityTest(StabilityTestConfig config) {
        String testId = UUID.randomUUID().toString();
        AtomicBoolean running = new AtomicBoolean(true);
        runningTests.put(testId, running);
        activeConfigs.put(testId, config);

        Thread.ofVirtual().start(() -> runStabilityTest(testId, config, running));

        return testId;
    }

    private void runStabilityTest(String testId, StabilityTestConfig config, AtomicBoolean running) {
        long totalDurationMs = config.getDurationHours() * 3600 * 1000L;
        long checkpointIntervalMs = config.getCheckpointIntervalMinutes() * 60 * 1000L;
        long startTime = System.currentTimeMillis();

        List<StabilityTestReport.Checkpoint> checkpoints = Collections.synchronizedList(new ArrayList<>());
        List<StabilityTestReport.AnomalyEvent> anomalies = Collections.synchronizedList(new ArrayList<>());

        AtomicLong totalGenerated = new AtomicLong(0);
        AtomicLong totalErrors = new AtomicLong(0);
        DoubleAdder totalQps = new DoubleAdder();
        DoubleAdder totalLatency = new DoubleAdder();
        long qpsSamples = 0;
        double peakQps = 0;

        long uniquenessExpectedInsertions = config.getThreadCount() * config.getDurationHours() * 3600L * 50000;
        TestConfig.UniquenessCheckConfig uc = config.getUniquenessConfig();
        if (uc == null) uc = new TestConfig.UniquenessCheckConfig();
        SamplingUniquenessChecker globalUniquenessChecker = new SamplingUniquenessChecker(
            uniquenessExpectedInsertions, uc.getSampleSize(), uc.getFalsePositiveProbability());

        double baselineQps = 0;
        double baselineLatency = 0;
        PerformanceBaseline baseline = baselineService.getBestBaseline(config.getAlgorithm());
        if (baseline != null) {
            baselineQps = baseline.getAvgQps();
            baselineLatency = baseline.getAvgLatency();
        }

        long lastCheckpointTime = startTime;
        long lastCheckpointCount = 0;
        long currentPhaseStart = startTime;

        while (running.get() && System.currentTimeMillis() - startTime < totalDurationMs) {
            long phaseElapsed = System.currentTimeMillis() - currentPhaseStart;
            long phaseDuration = Math.min(checkpointIntervalMs, totalDurationMs - (System.currentTimeMillis() - startTime));

            if (phaseDuration <= 0) break;

            TestConfig phaseConfig = config.toTestConfig();
            phaseConfig.setDurationSeconds((int) (phaseDuration / 1000));

            IdGenerator generator = IdGeneratorFactory.createGenerator(config.getAlgorithm(), phaseConfig);
            ExecutorService executor = Executors.newFixedThreadPool(config.getThreadCount());
            CountDownLatch startLatch = new CountDownLatch(1);
            CountDownLatch endLatch = new CountDownLatch(config.getThreadCount());

            AtomicLong phaseCount = new AtomicLong(0);
            AtomicLong phaseErrors = new AtomicLong(0);
            List<Long> phaseLatencies = new CopyOnWriteArrayList<>();

            long phaseEnd = System.currentTimeMillis() + phaseDuration;

            for (int i = 0; i < config.getThreadCount(); i++) {
                executor.submit(() -> {
                    try {
                        startLatch.await();
                        while (running.get() && System.currentTimeMillis() < phaseEnd) {
                            long startNano = System.nanoTime();
                            try {
                                String id = generator.nextId();
                                long latency = (System.nanoTime() - startNano) / 1000;
                                globalUniquenessChecker.checkAndRecord(id);
                                phaseLatencies.add(latency);
                                phaseCount.incrementAndGet();
                            } catch (Exception e) {
                                phaseErrors.incrementAndGet();
                            }
                        }
                    } catch (Exception e) {
                        log.error("Stability test worker error", e);
                    } finally {
                        endLatch.countDown();
                    }
                });
            }

            startLatch.countDown();

            try {
                endLatch.await(phaseDuration / 1000 + 5, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } finally {
                running.set(false);
                executor.shutdownNow();
            }

            long now = System.currentTimeMillis();
            long phaseGenerated = phaseCount.get();
            long phaseErrorCount = phaseErrors.get();
            double phaseQps = phaseDuration > 0 ? (phaseGenerated * 1000.0 / phaseDuration) : 0;
            double phaseAvgLatency = phaseLatencies.isEmpty() ? 0 :
                phaseLatencies.stream().mapToLong(Long::longValue).average().orElse(0);
            double phaseP99Latency = calculatePercentile(new ArrayList<>(phaseLatencies), 99);

            totalGenerated.addAndGet(phaseGenerated);
            totalErrors.addAndGet(phaseErrorCount);
            totalQps.add(phaseQps);
            totalLatency.add(phaseAvgLatency);
            if (phaseQps > peakQps) peakQps = phaseQps;
            qpsSamples++;

            boolean isHealthy = true;
            String healthMessage = "健康";

            if (baselineQps > 0 && phaseQps < baselineQps * (1 - config.getQpsDegradationThreshold())) {
                isHealthy = false;
                healthMessage = String.format("QPS下降 %.1f%%, 低于基线阈值", (1 - phaseQps / baselineQps) * 100);
                anomalies.add(StabilityTestReport.AnomalyEvent.builder()
                    .timestamp(now)
                    .type("QPS_DEGRADATION")
                    .severity("WARNING")
                    .message(healthMessage)
                    .observedValue(phaseQps)
                    .thresholdValue(baselineQps * (1 - config.getQpsDegradationThreshold()))
                    .build());
            }

            if (baselineLatency > 0 && phaseAvgLatency > baselineLatency * (1 + config.getLatencySpikeThreshold())) {
                isHealthy = false;
                healthMessage = String.format("延迟升高 %.1f%%, 超过基线阈值", (phaseAvgLatency / baselineLatency - 1) * 100);
                anomalies.add(StabilityTestReport.AnomalyEvent.builder()
                    .timestamp(now)
                    .type("LATENCY_SPIKE")
                    .severity("WARNING")
                    .message(healthMessage)
                    .observedValue(phaseAvgLatency)
                    .thresholdValue(baselineLatency * (1 + config.getLatencySpikeThreshold()))
                    .build());
            }

            double errorRate = phaseGenerated > 0 ? (double) phaseErrorCount / phaseGenerated : 0;
            if (errorRate > config.getErrorRateThreshold()) {
                isHealthy = false;
                healthMessage = String.format("错误率 %.2f%% 超过阈值", errorRate * 100);
                anomalies.add(StabilityTestReport.AnomalyEvent.builder()
                    .timestamp(now)
                    .type("HIGH_ERROR_RATE")
                    .severity("CRITICAL")
                    .message(healthMessage)
                    .observedValue(errorRate)
                    .thresholdValue(config.getErrorRateThreshold())
                    .build());
            }

            if (!isHealthy && config.isAutoRecovery()) {
                log.info("Auto-recovery triggered for test {}", testId);
                try {
                    Thread.sleep(5000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }

            StabilityTestReport.Checkpoint checkpoint = StabilityTestReport.Checkpoint.builder()
                .timestamp(now)
                .elapsedMs(now - startTime)
                .generatedCount(totalGenerated.get())
                .errorCount(totalErrors.get())
                .avgQps(phaseQps)
                .avgLatency(phaseAvgLatency)
                .p99Latency(phaseP99Latency)
                .isHealthy(isHealthy)
                .healthMessage(healthMessage)
                .build();

            checkpoints.add(checkpoint);

            messagingTemplate.convertAndSend("/topic/stability/" + testId + "/checkpoint", checkpoint);

            running.set(true);
            currentPhaseStart = now;
            lastCheckpointTime = now;
            lastCheckpointCount = totalGenerated.get();
        }

        long endTime = System.currentTimeMillis();
        SamplingUniquenessChecker.UniquenessResult uniquenessResult = globalUniquenessChecker.getResult();

        double qpsTrendSlope = calculateTrendSlope(checkpoints.stream().mapToDouble(StabilityTestReport.Checkpoint::getAvgQps).toArray());
        double latencyTrendSlope = calculateTrendSlope(checkpoints.stream().mapToDouble(StabilityTestReport.Checkpoint::getAvgLatency).toArray());
        double qpsVariability = calculateCV(checkpoints.stream().mapToDouble(StabilityTestReport.Checkpoint::getAvgQps).toArray());
        double latencyVariability = calculateCV(checkpoints.stream().mapToDouble(StabilityTestReport.Checkpoint::getAvgLatency).toArray());

        StabilityTestReport report = StabilityTestReport.builder()
            .id(testId)
            .config(config)
            .startTime(startTime)
            .endTime(endTime)
            .status("COMPLETED")
            .totalDurationMs(endTime - startTime)
            .checkpointCount(checkpoints.size())
            .totalGenerated(totalGenerated.get())
            .totalErrors(totalErrors.get())
            .overallAvgQps(qpsSamples > 0 ? totalQps.sum() / qpsSamples : 0)
            .overallPeakQps(peakQps)
            .overallAvgLatency(qpsSamples > 0 ? totalLatency.sum() / qpsSamples : 0)
            .overallP99Latency(checkpoints.isEmpty() ? 0 : checkpoints.stream().mapToDouble(StabilityTestReport.Checkpoint::getP99Latency).max().orElse(0))
            .uniquenessPassed(uniquenessResult.isUnique())
            .checkpoints(checkpoints)
            .anomalies(anomalies)
            .performanceTrend(StabilityTestReport.PerformanceTrend.builder()
                .qpsTrendSlope(qpsTrendSlope)
                .latencyTrendSlope(latencyTrendSlope)
                .qpsDegraded(qpsTrendSlope < -0.05)
                .latencyDegraded(latencyTrendSlope > 0.05)
                .qpsVariability(qpsVariability)
                .latencyVariability(latencyVariability)
                .build())
            .build();

        reportStore.put(testId, report);
        runningTests.remove(testId);
        activeConfigs.remove(testId);

        messagingTemplate.convertAndSend("/topic/stability/" + testId + "/complete", report);

        baselineService.updateBaseline(config.getAlgorithm(), config.getThreadCount(), report);
    }

    private double calculateTrendSlope(double[] values) {
        if (values.length < 2) return 0;
        int n = values.length;
        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
        for (int i = 0; i < n; i++) {
            sumX += i;
            sumY += values[i];
            sumXY += i * values[i];
            sumX2 += (double) i * i;
        }
        double denominator = n * sumX2 - sumX * sumX;
        return denominator == 0 ? 0 : (n * sumXY - sumX * sumY) / denominator;
    }

    private double calculateCV(double[] values) {
        if (values.length == 0) return 0;
        double mean = Arrays.stream(values).average().orElse(0);
        if (mean == 0) return 0;
        double stdDev = Math.sqrt(Arrays.stream(values).map(v -> Math.pow(v - mean, 2)).average().orElse(0));
        return stdDev / mean;
    }

    private double calculatePercentile(List<Long> values, double percentile) {
        if (values.isEmpty()) return 0;
        List<Long> sorted = new ArrayList<>(values);
        Collections.sort(sorted);
        int index = (int) Math.ceil(percentile / 100.0 * sorted.size()) - 1;
        return sorted.get(Math.max(0, Math.min(index, sorted.size() - 1)));
    }

    public boolean stopStabilityTest(String testId) {
        AtomicBoolean running = runningTests.get(testId);
        if (running != null) {
            running.set(false);
            return true;
        }
        return false;
    }

    public StabilityTestReport getStabilityReport(String testId) {
        return reportStore.get(testId);
    }

    public List<StabilityTestReport> listStabilityReports() {
        return new ArrayList<>(reportStore.values());
    }

    public boolean isRunning(String testId) {
        AtomicBoolean running = runningTests.get(testId);
        return running != null && running.get();
    }
}
