package com.benchmark.service;

import com.benchmark.dto.*;
import com.benchmark.generator.IdGenerator;
import com.benchmark.generator.IdGeneratorFactory;
import com.benchmark.generator.SamplingUniquenessChecker;
import com.benchmark.generator.SnowflakeIdGenerator;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
public class TestEngineService {

    private final SimpMessagingTemplate messagingTemplate;
    private final Map<String, TestReport> reportStore = new ConcurrentHashMap<>();
    private final Map<String, AtomicBoolean> runningTests = new ConcurrentHashMap<>();

    private static final int METRICS_HISTORY_MAX_SIZE = 120;
    private static final int SAMPLED_METRICS_MAX_SIZE = 60;

    public TestEngineService(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    public String startTest(TestConfig config) {
        String testId = UUID.randomUUID().toString();
        AtomicBoolean running = new AtomicBoolean(true);
        runningTests.put(testId, running);

        Thread.ofVirtual().start(() -> runTest(testId, config, running));

        return testId;
    }

    private void runTest(String testId, TestConfig config, AtomicBoolean running) {
        IdGenerator generator = IdGeneratorFactory.createGenerator(config.getAlgorithm(), config);
        int threadCount = config.getThreadCount();
        int durationSeconds = config.getDurationSeconds();
        Long targetCount = config.getIdCount();

        TestConfig.UniquenessCheckConfig uniquenessConfig = config.getUniquenessConfig();
        if (uniquenessConfig == null) {
            uniquenessConfig = new TestConfig.UniquenessCheckConfig();
        }

        long expectedInsertions = (long) threadCount * durationSeconds * 50000;
        SamplingUniquenessChecker uniquenessChecker = new SamplingUniquenessChecker(
            expectedInsertions,
            uniquenessConfig.getSampleSize(),
            uniquenessConfig.getFalsePositiveProbability()
        );

        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch startLatch = new CountDownLatch(1);
        CountDownLatch endLatch = new CountDownLatch(threadCount);

        AtomicLong totalCount = new AtomicLong(0);
        AtomicLong errorCount = new AtomicLong(0);
        List<Long> latencies = new CopyOnWriteArrayList<>();
        List<RealtimeMetrics> metricsHistory = Collections.synchronizedList(new ArrayList<>());
        List<TestReport.SampledMetrics> sampledMetrics = Collections.synchronizedList(new ArrayList<>());
        List<Long> qpsHistory = Collections.synchronizedList(new ArrayList<>());
        List<Long> memoryHistory = Collections.synchronizedList(new ArrayList<>());

        long startTime = System.currentTimeMillis();
        long endTime = startTime + (durationSeconds * 1000L);
        long peakMemoryBytes = 0;
        long totalMemoryBytes = 0;
        int memorySamples = 0;

        for (int i = 0; i < threadCount; i++) {
            executor.submit(() -> {
                try {
                    startLatch.await();
                    while (running.get() && System.currentTimeMillis() < endTime
                            && (targetCount == null || totalCount.get() < targetCount)) {
                        long startNano = System.nanoTime();
                        try {
                            String id = generator.nextId();
                            long latency = (System.nanoTime() - startNano) / 1000;

                            uniquenessChecker.checkAndRecord(id);
                            latencies.add(latency);
                            totalCount.incrementAndGet();
                        } catch (Exception e) {
                            errorCount.incrementAndGet();
                            log.debug("ID generation error", e);
                        }
                    }
                } catch (Exception e) {
                    log.error("Worker thread error", e);
                } finally {
                    endLatch.countDown();
                }
            });
        }

        long metricsStart = System.currentTimeMillis();
        startLatch.countDown();

        Thread metricsReporter = new Thread(() -> {
            long lastCount = 0;
            long lastTime = metricsStart;

            while (running.get() && System.currentTimeMillis() < endTime) {
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }

                long currentCount = totalCount.get();
                long currentTime = System.currentTimeMillis();
                long interval = currentTime - lastTime;

                long qps = interval > 0 ? ((currentCount - lastCount) * 1000) / interval : 0;
                qpsHistory.add(qps);

                int progress = targetCount != null
                        ? (int) ((currentCount * 100) / targetCount)
                        : (int) (((currentTime - startTime) * 100) / (durationSeconds * 1000L));

                List<Long> currentLatencies = new ArrayList<>(latencies);
                RealtimeMetrics metrics = RealtimeMetrics.builder()
                        .timestamp(currentTime)
                        .qps(qps)
                        .avgLatency(calculateAvg(currentLatencies))
                        .p50Latency(calculatePercentile(currentLatencies, 50))
                        .p95Latency(calculatePercentile(currentLatencies, 95))
                        .p99Latency(calculatePercentile(currentLatencies, 99))
                        .generatedCount(currentCount)
                        .progress(Math.min(progress, 100))
                        .build();

                metricsHistory.add(metrics);

                if (metricsHistory.size() > METRICS_HISTORY_MAX_SIZE) {
                    metricsHistory.remove(0);
                }

                if (metricsHistory.size() % 2 == 0 && sampledMetrics.size() < SAMPLED_METRICS_MAX_SIZE) {
                    sampledMetrics.add(TestReport.SampledMetrics.builder()
                            .timestamp(metrics.getTimestamp())
                            .qps(metrics.getQps())
                            .avgLatency(metrics.getAvgLatency())
                            .p50Latency(metrics.getP50Latency())
                            .p95Latency(metrics.getP95Latency())
                            .p99Latency(metrics.getP99Latency())
                            .generatedCount(metrics.getGeneratedCount())
                            .progress(metrics.getProgress())
                            .build());
                }

                long usedMemory = Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory();
                peakMemoryBytes = Math.max(peakMemoryBytes, usedMemory);
                totalMemoryBytes += usedMemory;
                memorySamples++;
                memoryHistory.add(usedMemory);

                messagingTemplate.convertAndSend("/topic/test/" + testId + "/metrics", metrics);

                lastCount = currentCount;
                lastTime = currentTime;
            }
        });
        metricsReporter.start();

        try {
            endLatch.await(durationSeconds + 5, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            running.set(false);
            executor.shutdownNow();
            try {
                metricsReporter.join();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }

        long testEndTime = System.currentTimeMillis();
        long totalGenerated = totalCount.get();
        long errors = errorCount.get();

        SamplingUniquenessChecker.UniquenessResult uniquenessResult = uniquenessChecker.getResult();

        List<Long> allLatencies = new ArrayList<>(latencies);
        Collections.sort(allLatencies);

        SnowflakeIdGenerator.ClockStatistics clockStats = null;
        if (generator instanceof SnowflakeIdGenerator) {
            clockStats = ((SnowflakeIdGenerator) generator).getStatistics();
        }

        long qpsSum = qpsHistory.stream().mapToLong(Long::longValue).sum();
        double avgQps = qpsHistory.isEmpty() ? 0 : (double) qpsSum / qpsHistory.size();
        long peakQps = qpsHistory.stream().mapToLong(Long::longValue).max().orElse(0);
        long minQps = qpsHistory.stream().mapToLong(Long::longValue).min().orElse(0);
        double stdDevQps = calculateStdDev(qpsHistory, avgQps);

        double avgMemory = memorySamples > 0 ? (double) totalMemoryBytes / memorySamples : 0;
        long originalMemoryNeeded = totalGenerated * 24;
        long estimatedMemorySaved = originalMemoryNeeded - uniquenessResult.getMemoryUsageBytes();

        TestReport report = TestReport.builder()
                .id(testId)
                .config(config)
                .startTime(startTime)
                .endTime(testEndTime)
                .summary(TestReport.SummaryStats.builder()
                        .totalGenerated(totalGenerated)
                        .successCount(totalGenerated - errors)
                        .errorCount(errors)
                        .avgQps(avgQps)
                        .peakQps(peakQps)
                        .minQps(minQps)
                        .stdDevQps(stdDevQps)
                        .durationSeconds(durationSeconds)
                        .build())
                .latencyStats(TestReport.LatencyStats.builder()
                        .avg(calculateAvg(allLatencies))
                        .min(allLatencies.isEmpty() ? 0 : allLatencies.get(0))
                        .max(allLatencies.isEmpty() ? 0 : allLatencies.get(allLatencies.size() - 1))
                        .p50(calculatePercentile(allLatencies, 50))
                        .p90(calculatePercentile(allLatencies, 90))
                        .p95(calculatePercentile(allLatencies, 95))
                        .p99(calculatePercentile(allLatencies, 99))
                        .p999(calculatePercentile(allLatencies, 99.9))
                        .stdDev(calculateStdDevFromList(allLatencies))
                        .build())
                .uniquenessCheck(TestReport.UniquenessCheck.builder()
                        .isUnique(uniquenessResult.isUnique())
                        .bloomFilterDuplicates(uniquenessResult.getBloomFilterDuplicates())
                        .sampleDuplicates(uniquenessResult.getSampleDuplicates())
                        .sampleSize(uniquenessResult.getSampleSize())
                        .falsePositives(uniquenessResult.getFalsePositives())
                        .estimatedDuplicateRate(uniquenessResult.getEstimatedDuplicateRate())
                        .sampleDuplicateRate(uniquenessResult.getSampleDuplicateRate())
                        .adjustedDuplicateRate(uniquenessResult.getAdjustedDuplicateRate())
                        .memoryUsageBytes(uniquenessResult.getMemoryUsageBytes())
                        .duplicateDetails(uniquenessResult.getDuplicateDetails())
                        .sampleIds(uniquenessResult.getSampledIds().subList(0, Math.min(100, uniquenessResult.getSampledIds().size())))
                        .build())
                .clockStats(buildClockStats(clockStats))
                .memoryStats(TestReport.MemoryUsageStats.builder()
                        .peakMemoryBytes(peakMemoryBytes)
                        .avgMemoryBytes((long) avgMemory)
                        .estimatedMemorySavedBytes(Math.max(0, estimatedMemorySaved))
                        .build())
                .sampledMetrics(sampledMetrics)
                .build();

        reportStore.put(testId, report);
        runningTests.remove(testId);

        messagingTemplate.convertAndSend("/topic/test/" + testId + "/complete", report);
    }

    private TestReport.ClockSimulationStats buildClockStats(SnowflakeIdGenerator.ClockStatistics stats) {
        if (stats == null || stats.getClockMode() == SnowflakeIdGenerator.ClockSimulator.Mode.NORMAL) {
            return TestReport.ClockSimulationStats.builder()
                    .enabled(false)
                    .mode(SnowflakeIdGenerator.ClockSimulator.Mode.NORMAL)
                    .build();
        }

        return TestReport.ClockSimulationStats.builder()
                .enabled(true)
                .mode(stats.getClockMode())
                .clockDriftCount(stats.getClockDriftCount())
                .clockBackwardCount(stats.getClockBackwardCount())
                .forcedWaitCount(stats.getForcedWaitCount())
                .totalWaitTimeMs(stats.getTotalWaitTimeMs())
                .totalDriftApplied(stats.getTotalDriftApplied())
                .totalBackwardApplied(stats.getTotalBackwardApplied())
                .build();
    }

    private double calculateAvg(List<Long> values) {
        if (values.isEmpty()) return 0;
        return values.stream().mapToLong(Long::longValue).average().orElse(0);
    }

    private double calculatePercentile(List<Long> values, double percentile) {
        if (values.isEmpty()) return 0;
        List<Long> sorted = new ArrayList<>(values);
        Collections.sort(sorted);
        int index = (int) Math.ceil(percentile / 100.0 * sorted.size()) - 1;
        return sorted.get(Math.max(0, Math.min(index, sorted.size() - 1)));
    }

    private double calculateStdDev(List<Long> values, double mean) {
        if (values.isEmpty()) return 0;
        double sumSquaredDiff = values.stream()
                .mapToDouble(v -> Math.pow(v - mean, 2))
                .sum();
        return Math.sqrt(sumSquaredDiff / values.size());
    }

    private double calculateStdDevFromList(List<Long> values) {
        if (values.isEmpty()) return 0;
        double mean = calculateAvg(values);
        return calculateStdDev(values, mean);
    }

    public boolean stopTest(String testId) {
        AtomicBoolean running = runningTests.get(testId);
        if (running != null) {
            running.set(false);
            return true;
        }
        return false;
    }

    public TestReport getReport(String testId) {
        return reportStore.get(testId);
    }

    public List<TestReport> listReports() {
        return new ArrayList<>(reportStore.values());
    }
}
