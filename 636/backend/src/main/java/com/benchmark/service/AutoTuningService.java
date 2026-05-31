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

@Slf4j
@Service
public class AutoTuningService {

    private final SimpMessagingTemplate messagingTemplate;
    private final BaselineService baselineService;
    private final Map<String, AutoTuningReport> reportStore = new ConcurrentHashMap<>();
    private final Map<String, AtomicBoolean> runningTuning = new ConcurrentHashMap<>();

    public AutoTuningService(SimpMessagingTemplate messagingTemplate, BaselineService baselineService) {
        this.messagingTemplate = messagingTemplate;
        this.baselineService = baselineService;
    }

    public String startAutoTuning(AutoTuningConfig config) {
        String tuningId = UUID.randomUUID().toString();
        AtomicBoolean running = new AtomicBoolean(true);
        runningTuning.put(tuningId, running);

        Thread.ofVirtual().start(() -> runAutoTuning(tuningId, config, running));

        return tuningId;
    }

    private void runAutoTuning(String tuningId, AutoTuningConfig config, AtomicBoolean running) {
        long startTime = System.currentTimeMillis();
        List<AutoTuningReport.TuningRoundResult> roundResults = Collections.synchronizedList(new ArrayList<>());
        List<AutoTuningReport.ParamSuggestion> suggestions = new ArrayList<>();

        List<ParamCombination> combinations = generateParamCombinations(config);
        int totalRounds = Math.min(combinations.size(), config.getMaxRounds());

        BayesianOptimizer optimizer = new BayesianOptimizer();

        for (int round = 0; round < totalRounds && running.get(); round++) {
            ParamCombination params;
            if (round < 3) {
                params = combinations.get(round);
            } else {
                params = optimizer.suggestNext(roundResults, config);
                if (params == null) {
                    params = combinations.get(round % combinations.size());
                }
            }

            TestConfig testConfig = buildTestConfig(config, params);

            AutoTuningReport.TuningRoundResult result = runSingleRound(round, testConfig, config.getTestDurationSeconds(), running);
            if (result != null) {
                roundResults.add(result);

                optimizer.observe(params, result.getScore());

                messagingTemplate.convertAndSend("/topic/tuning/" + tuningId + "/round", result);
                log.info("Tuning round {} completed: score={}", round, result.getScore());
            }
        }

        AutoTuningReport.TuningRoundResult bestRound = roundResults.stream()
            .max(Comparator.comparingDouble(AutoTuningReport.TuningRoundResult::getScore))
            .orElse(null);

        Map<String, Object> bestParams = new HashMap<>();
        if (bestRound != null) {
            bestParams.put("threadCount", bestRound.getConfig().getThreadCount());
            if (bestRound.getConfig().getSnowflakeConfig() != null) {
                bestParams.put("workerId", bestRound.getConfig().getSnowflakeConfig().getWorkerId());
                bestParams.put("datacenterId", bestRound.getConfig().getSnowflakeConfig().getDatacenterId());
            }
            if (bestRound.getConfig().getSegmentConfig() != null) {
                bestParams.put("segmentSize", bestRound.getConfig().getSegmentConfig().getSegmentSize());
            }
        }

        generateSuggestions(roundResults, suggestions);

        AutoTuningReport report = AutoTuningReport.builder()
            .id(tuningId)
            .config(config)
            .startTime(startTime)
            .endTime(System.currentTimeMillis())
            .status(running.get() ? "COMPLETED" : "STOPPED")
            .completedRounds(roundResults.size())
            .totalRounds(totalRounds)
            .bestResult(bestRound != null ? AutoTuningReport.TuningResult.builder()
                .bestConfig(bestRound.getConfig())
                .bestScore(bestRound.getScore())
                .bestAvgQps(bestRound.getAvgQps())
                .bestAvgLatency(bestRound.getAvgLatency())
                .bestP99Latency(bestRound.getP99Latency())
                .bestParams(bestParams)
                .build() : null)
            .roundResults(roundResults)
            .suggestions(suggestions)
            .build();

        reportStore.put(tuningId, report);
        runningTuning.remove(tuningId);

        if (bestRound != null) {
            TestReport bestReport = TestReport.builder()
                .id("tuning-" + tuningId)
                .config(bestRound.getConfig())
                .summary(TestReport.SummaryStats.builder()
                    .avgQps(bestRound.getAvgQps())
                    .totalGenerated(bestRound.getTotalGenerated())
                    .build())
                .latencyStats(TestReport.LatencyStats.builder()
                    .avg(bestRound.getAvgLatency())
                    .p99(bestRound.getP99Latency())
                    .build())
                .build();
            baselineService.createBaseline(bestReport);
        }

        messagingTemplate.convertAndSend("/topic/tuning/" + tuningId + "/complete", report);
    }

    private AutoTuningReport.TuningRoundResult runSingleRound(int round, TestConfig testConfig, int durationSeconds, AtomicBoolean running) {
        IdGenerator generator = IdGeneratorFactory.createGenerator(testConfig.getAlgorithm(), testConfig);
        int threadCount = testConfig.getThreadCount();

        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch startLatch = new CountDownLatch(1);
        CountDownLatch endLatch = new CountDownLatch(threadCount);

        AtomicLong totalCount = new AtomicLong(0);
        AtomicLong errorCount = new AtomicLong(0);
        List<Long> latencies = new CopyOnWriteArrayList<>();

        SamplingUniquenessChecker checker = new SamplingUniquenessChecker(
            (long) threadCount * durationSeconds * 50000, 5000, 0.001);

        long startTime = System.currentTimeMillis();
        long endTime = startTime + (durationSeconds * 1000L);

        for (int i = 0; i < threadCount; i++) {
            executor.submit(() -> {
                try {
                    startLatch.await();
                    while (running.get() && System.currentTimeMillis() < endTime) {
                        long startNano = System.nanoTime();
                        try {
                            String id = generator.nextId();
                            long latency = (System.nanoTime() - startNano) / 1000;
                            checker.checkAndRecord(id);
                            latencies.add(latency);
                            totalCount.incrementAndGet();
                        } catch (Exception e) {
                            errorCount.incrementAndGet();
                        }
                    }
                } catch (Exception e) {
                    log.error("Tuning round worker error", e);
                } finally {
                    endLatch.countDown();
                }
            });
        }

        startLatch.countDown();

        try {
            endLatch.await(durationSeconds + 5, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            executor.shutdownNow();
        }

        long totalGenerated = totalCount.get();
        long errors = errorCount.get();
        double elapsedSeconds = (System.currentTimeMillis() - startTime) / 1000.0;
        double avgQps = elapsedSeconds > 0 ? totalGenerated / elapsedSeconds : 0;
        double avgLatency = latencies.isEmpty() ? 0 : latencies.stream().mapToLong(Long::longValue).average().orElse(0);
        double p99Latency = calculatePercentile(new ArrayList<>(latencies), 99);
        double errorRate = totalGenerated > 0 ? (double) errors / totalGenerated : 0;
        boolean uniquenessPassed = checker.getResult().isUnique();

        double score = calculateScore(avgQps, avgLatency, p99Latency, errorRate, uniquenessPassed);

        return AutoTuningReport.TuningRoundResult.builder()
            .round(round)
            .config(testConfig)
            .score(score)
            .avgQps(avgQps)
            .avgLatency(avgLatency)
            .p99Latency(p99Latency)
            .errorRate(errorRate)
            .uniquenessPassed(uniquenessPassed)
            .totalGenerated(totalGenerated)
            .build();
    }

    private double calculateScore(double avgQps, double avgLatency, double p99Latency, double errorRate, boolean uniquenessPassed) {
        double qpsScore = Math.log1p(avgQps) * 10;
        double latencyScore = avgLatency > 0 ? 100.0 / Math.log1p(avgLatency) : 50;
        double p99Score = p99Latency > 0 ? 50.0 / Math.log1p(p99Latency) : 25;
        double uniquenessBonus = uniquenessPassed ? 20 : -50;
        double errorPenalty = errorRate * 1000;

        return qpsScore + latencyScore * 0.3 + p99Score * 0.2 + uniquenessBonus - errorPenalty;
    }

    private List<ParamCombination> generateParamCombinations(AutoTuningConfig config) {
        List<ParamCombination> combinations = new ArrayList<>();
        AutoTuningConfig.ParamRange threadRange = config.getThreadCountRange();

        List<Integer> threadCounts = new ArrayList<>();
        if (threadRange != null) {
            for (int t = threadRange.getMin(); t <= threadRange.getMax(); t += threadRange.getStep()) {
                threadCounts.add(t);
            }
        } else {
            threadCounts.addAll(Arrays.asList(1, 2, 4, 8, 16, 32, 64));
        }

        List<ParamCombination> algoCombinations = new ArrayList<>();
        if ("SNOWFLAKE".equals(config.getAlgorithm()) && config.getAlgorithmParamRanges() != null) {
            AutoTuningConfig.ParamRange workerRange = config.getAlgorithmParamRanges().get("workerId");
            AutoTuningConfig.ParamRange segmentRange = config.getAlgorithmParamRanges().get("segmentSize");

            for (int tc : threadCounts) {
                ParamCombination pc = new ParamCombination();
                pc.threadCount = tc;
                pc.workerId = workerRange != null ? (workerRange.getMin() + workerRange.getMax()) / 2 : 1;
                pc.datacenterId = 1;
                pc.segmentSize = segmentRange != null ? (segmentRange.getMin() + segmentRange.getMax()) / 2 : 1000;
                algoCombinations.add(pc);
            }
        } else if ("SEGMENT".equals(config.getAlgorithm()) && config.getAlgorithmParamRanges() != null) {
            AutoTuningConfig.ParamRange segmentRange = config.getAlgorithmParamRanges().get("segmentSize");
            List<Integer> segmentSizes = new ArrayList<>();
            if (segmentRange != null) {
                for (int s = segmentRange.getMin(); s <= segmentRange.getMax(); s += segmentRange.getStep()) {
                    segmentSizes.add(s);
                }
            } else {
                segmentSizes.addAll(Arrays.asList(100, 500, 1000, 5000, 10000));
            }

            for (int tc : threadCounts) {
                for (int seg : segmentSizes) {
                    ParamCombination pc = new ParamCombination();
                    pc.threadCount = tc;
                    pc.segmentSize = seg;
                    algoCombinations.add(pc);
                }
            }
        } else {
            for (int tc : threadCounts) {
                ParamCombination pc = new ParamCombination();
                pc.threadCount = tc;
                algoCombinations.add(pc);
            }
        }

        return algoCombinations;
    }

    private TestConfig buildTestConfig(AutoTuningConfig config, ParamCombination params) {
        TestConfig testConfig = new TestConfig();
        testConfig.setAlgorithm(config.getAlgorithm());
        testConfig.setThreadCount(params.threadCount);
        testConfig.setDurationSeconds(config.getTestDurationSeconds());

        if ("SNOWFLAKE".equals(config.getAlgorithm())) {
            TestConfig.SnowflakeConfig sf = new TestConfig.SnowflakeConfig();
            sf.setWorkerId(params.workerId);
            sf.setDatacenterId(params.datacenterId);
            testConfig.setSnowflakeConfig(sf);
        } else if ("SEGMENT".equals(config.getAlgorithm())) {
            TestConfig.SegmentConfig seg = new TestConfig.SegmentConfig();
            seg.setSegmentSize(params.segmentSize);
            testConfig.setSegmentConfig(seg);
        }

        return testConfig;
    }

    private void generateSuggestions(List<AutoTuningReport.TuningRoundResult> results, List<AutoTuningReport.ParamSuggestion> suggestions) {
        if (results.isEmpty()) return;

        Map<Integer, Double> threadScoreMap = new HashMap<>();
        for (AutoTuningReport.TuningRoundResult r : results) {
            int tc = r.getConfig().getThreadCount();
            threadScoreMap.merge(tc, r.getScore(), Double::max);
        }

        threadScoreMap.entrySet().stream()
            .max(Map.Entry.comparingByValue())
            .ifPresent(e -> suggestions.add(AutoTuningReport.ParamSuggestion.builder()
                .paramName("threadCount")
                .recommendedValue(e.getKey())
                .reason(String.format("线程数 %d 取得最高评分 %.2f", e.getKey(), e.getValue()))
                .impact(e.getValue())
                .build()));

        AutoTuningReport.TuningRoundResult best = results.stream()
            .max(Comparator.comparingDouble(AutoTuningReport.TuningRoundResult::getScore))
            .orElse(null);

        if (best != null) {
            suggestions.add(AutoTuningReport.ParamSuggestion.builder()
                .paramName("algorithm")
                .recommendedValue(best.getConfig().getAlgorithm())
                .reason(String.format("算法 %s 综合评分最高 %.2f (QPS=%.0f, AvgLatency=%.1fμs)",
                    best.getConfig().getAlgorithm(), best.getScore(), best.getAvgQps(), best.getAvgLatency()))
                .impact(best.getScore())
                .build());

            if (best.getConfig().getSegmentConfig() != null) {
                suggestions.add(AutoTuningReport.ParamSuggestion.builder()
                    .paramName("segmentSize")
                    .recommendedValue(best.getConfig().getSegmentConfig().getSegmentSize())
                    .reason(String.format("号段大小 %d 配合当前参数取得最佳性能",
                        best.getConfig().getSegmentConfig().getSegmentSize()))
                    .impact(best.getScore() * 0.3)
                    .build());
            }
        }
    }

    private double calculatePercentile(List<Long> values, double percentile) {
        if (values.isEmpty()) return 0;
        List<Long> sorted = new ArrayList<>(values);
        Collections.sort(sorted);
        int index = (int) Math.ceil(percentile / 100.0 * sorted.size()) - 1;
        return sorted.get(Math.max(0, Math.min(index, sorted.size() - 1)));
    }

    public boolean stopAutoTuning(String tuningId) {
        AtomicBoolean running = runningTuning.get(tuningId);
        if (running != null) {
            running.set(false);
            return true;
        }
        return false;
    }

    public AutoTuningReport getTuningReport(String tuningId) {
        return reportStore.get(tuningId);
    }

    public List<AutoTuningReport> listTuningReports() {
        return new ArrayList<>(reportStore.values());
    }

    private static class ParamCombination {
        int threadCount;
        long workerId = 1;
        long datacenterId = 1;
        long segmentSize = 1000;
    }

    private static class BayesianOptimizer {
        private final Map<ParamCombination, Double> observations = new ConcurrentHashMap<>();
        private final Random random = new Random();

        void observe(ParamCombination params, double score) {
            observations.put(params, score);
        }

        ParamCombination suggestNext(List<AutoTuningReport.TuningRoundResult> history, AutoTuningConfig config) {
            if (history.size() < 2) return null;

            AutoTuningReport.TuningRoundResult best = history.stream()
                .max(Comparator.comparingDouble(AutoTuningReport.TuningRoundResult::getScore))
                .orElse(null);
            if (best == null) return null;

            AutoTuningConfig.ParamRange threadRange = config.getThreadCountRange();
            int minThread = threadRange != null ? threadRange.getMin() : 1;
            int maxThread = threadRange != null ? threadRange.getMax() : 64;
            int stepThread = threadRange != null ? threadRange.getStep() : 1;

            double explorationRate = 0.3;
            if (random.nextDouble() < explorationRate) {
                ParamCombination pc = new ParamCombination();
                pc.threadCount = minThread + random.nextInt((maxThread - minThread) / stepThread + 1) * stepThread;
                pc.segmentSize = best.getConfig().getSegmentConfig() != null
                    ? best.getConfig().getSegmentConfig().getSegmentSize() : 1000;
                return pc;
            }

            int bestThread = best.getConfig().getThreadCount();
            int candidate1 = Math.max(minThread, bestThread - stepThread);
            int candidate2 = Math.min(maxThread, bestThread + stepThread);

            double score1 = getAverageScoreForThreadCount(history, candidate1);
            double score2 = getAverageScoreForThreadCount(history, candidate2);

            ParamCombination pc = new ParamCombination();
            pc.threadCount = score2 > score1 ? candidate2 : candidate1;
            pc.segmentSize = best.getConfig().getSegmentConfig() != null
                ? best.getConfig().getSegmentConfig().getSegmentSize() : 1000;
            return pc;
        }

        private double getAverageScoreForThreadCount(List<AutoTuningReport.TuningRoundResult> history, int tc) {
            return history.stream()
                .filter(r -> r.getConfig().getThreadCount() == tc)
                .mapToDouble(AutoTuningReport.TuningRoundResult::getScore)
                .average()
                .orElse(0);
        }
    }
}
