package com.dbpool.optimizer.core;

import com.dbpool.optimizer.model.*;
import org.springframework.stereotype.Component;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class ConnectionPoolSimulator {

    private final QueueingTheoryAnalyzer queueingAnalyzer;
    private final Random random = new Random();

    public ConnectionPoolSimulator(QueueingTheoryAnalyzer queueingAnalyzer) {
        this.queueingAnalyzer = queueingAnalyzer;
    }

    public SimulationResult simulate(PoolConfig config, WorkloadProfile workload) {
        List<Double> waitTimeSamples = Collections.synchronizedList(new ArrayList<>());
        List<Double> shortQueryWaitTimes = Collections.synchronizedList(new ArrayList<>());
        List<Double> longQueryWaitTimes = Collections.synchronizedList(new ArrayList<>());
        List<Double> shortQueryServiceTimes = Collections.synchronizedList(new ArrayList<>());
        List<Double> longQueryServiceTimes = Collections.synchronizedList(new ArrayList<>());
        Map<Integer, Double> utilizationOverTime = new ConcurrentHashMap<>();
        AtomicInteger totalRequests = new AtomicInteger(0);
        AtomicInteger failedRequests = new AtomicInteger(0);
        AtomicInteger timeoutCount = new AtomicInteger(0);
        AtomicInteger activeConnections = new AtomicInteger(0);
        AtomicInteger peakActive = new AtomicInteger(0);
        AtomicInteger shortQueryCount = new AtomicInteger(0);
        AtomicInteger longQueryCount = new AtomicInteger(0);
        AtomicInteger shortQueryTimeouts = new AtomicInteger(0);
        AtomicInteger longQueryTimeouts = new AtomicInteger(0);

        List<Double> arrivalRateSamples = Collections.synchronizedList(new ArrayList<>());
        List<Double> interArrivalTimes = Collections.synchronizedList(new ArrayList<>();

        QueueMetrics queueMetrics = queueingAnalyzer.analyze(config, workload);

        long simulationDuration = workload.getSimulationDurationMs();
        long timeStep = 100;

        MarkovArrivalProcess markovProcess = null;
        if (workload.getMarkovArrivalConfig() != null && workload.getMarkovArrivalConfig().isEnabled()) {
            markovProcess = new MarkovArrivalProcess(workload.getMarkovArrivalConfig(), random);
        }

        MixedTransactionProfile mixedProfile = null;
        if (workload.getMixedTransactionConfig() != null && workload.getMixedTransactionConfig().isEnabled()) {
            mixedProfile = new MixedTransactionProfile(workload.getMixedTransactionConfig(), random);
        }

        double avgServiceTime = workload.getAvgServiceTimeMs();
        double serviceTimeStdDev = workload.getServiceTimeStdDevMs();

        ExecutorService executor = Executors.newFixedThreadPool(Math.max(1, config.getMaxPoolSize()));
        List<Future<?>> futures = new ArrayList<>();

        BlockingQueue<SimulationRequest> requestQueue = new LinkedBlockingQueue<>();

        long currentTime = 0;
        long lastRequestTime = 0;

        while (currentTime < simulationDuration) {
            int requestsThisStep;
            double currentArrivalRate;

            if (markovProcess != null) {
                currentArrivalRate = markovProcess.getCurrentArrivalRate();
                requestsThisStep = markovProcess.generateRequests(timeStep);
            } else {
                currentArrivalRate = workload.getArrivalRate();
                requestsThisStep = getPoissonRandom(currentArrivalRate * timeStep / 1000.0);
            }

            arrivalRateSamples.add(currentArrivalRate);

            for (int i = 0; i < requestsThisStep; i++) {
                boolean isShortQuery = true;
                double queryServiceTime;

                if (mixedProfile != null) {
                    isShortQuery = mixedProfile.isShortQuery();
                    queryServiceTime = mixedProfile.generateServiceTime(isShortQuery);
                } else {
                    queryServiceTime = getGaussianRandom(avgServiceTime, serviceTimeStdDev);
                }

                if (isShortQuery) {
                    shortQueryCount.incrementAndGet();
                } else {
                    longQueryCount.incrementAndGet();
                }

                long interArrival = currentTime - lastRequestTime;
                if (lastRequestTime > 0 && interArrival >= 0) {
                    interArrivalTimes.add((double) interArrival);
                }
                lastRequestTime = currentTime;

                requestQueue.offer(new SimulationRequest(currentTime, isShortQuery, queryServiceTime));
                totalRequests.incrementAndGet();
            }

            processQueue(config, requestQueue, executor, futures,
                    waitTimeSamples, activeConnections, peakActive,
                    timeoutCount, failedRequests,
                    shortQueryWaitTimes, longQueryWaitTimes,
                    shortQueryServiceTimes, longQueryServiceTimes,
                    shortQueryTimeouts, longQueryTimeouts);

            int second = (int) (currentTime / 1000);
            double utilization = config.getMaxPoolSize() > 0 ?
                    (double) activeConnections.get() / config.getMaxPoolSize() : 0;
            utilizationOverTime.merge(second, utilization, (a, b) -> (a + b) / 2);

            if (markovProcess != null) {
                markovProcess.transition();
            }

            currentTime += timeStep;
            sleepUninterruptibly(timeStep / 10);
        }

        executor.shutdownNow();

        MixedTransactionMetrics mixedMetrics = buildMixedTransactionMetrics(
                shortQueryCount.get(), longQueryCount.get(),
                shortQueryWaitTimes, longQueryWaitTimes,
                shortQueryServiceTimes, longQueryServiceTimes,
                shortQueryTimeouts.get(), longQueryTimeouts.get(),
                totalRequests.get(), workload);

        BurstinessMetrics burstinessMetrics = buildBurstinessMetrics(
                arrivalRateSamples, interArrivalTimes, workload, markovProcess);

        return buildSimulationResult(config, workload, waitTimeSamples,
                utilizationOverTime, totalRequests.get(), failedRequests.get(),
                timeoutCount.get(), peakActive.get(), queueMetrics,
                mixedMetrics, burstinessMetrics);
    }

    private void processQueue(PoolConfig config,
                              BlockingQueue<SimulationRequest> requestQueue,
                              ExecutorService executor, List<Future<?>> futures,
                              List<Double> waitTimeSamples,
                              AtomicInteger activeConnections, AtomicInteger peakActive,
                              AtomicInteger timeoutCount, AtomicInteger failedRequests,
                              List<Double> shortQueryWaitTimes, List<Double> longQueryWaitTimes,
                              List<Double> shortQueryServiceTimes, List<Double> longQueryServiceTimes,
                              AtomicInteger shortQueryTimeouts, AtomicInteger longQueryTimeouts) {
        while (!requestQueue.isEmpty()) {
            if (activeConnections.get() >= config.getMaxPoolSize()) {
                break;
            }

            SimulationRequest req = requestQueue.poll();
            if (req == null) break;

            long waitTime = System.currentTimeMillis() - req.timestamp;
            if (config.getConnectionTimeoutMs() > 0 && waitTime > config.getConnectionTimeoutMs()) {
                timeoutCount.incrementAndGet();
                failedRequests.incrementAndGet();
                if (req.isShortQuery) {
                    shortQueryTimeouts.incrementAndGet();
                } else {
                    longQueryTimeouts.incrementAndGet();
                }
                continue;
            }

            waitTimeSamples.add((double) waitTime);
            if (req.isShortQuery) {
                shortQueryWaitTimes.add((double) waitTime);
            } else {
                longQueryWaitTimes.add((double) waitTime);
            }

            activeConnections.incrementAndGet();
            peakActive.updateAndGet(v -> Math.max(v, activeConnections.get()));

            final double serviceTime = req.serviceTime;
            final boolean isShort = req.isShortQuery;

            Future<?> future = executor.submit(() -> {
                try {
                    sleepUninterruptibly((long) serviceTime);
                } finally {
                    activeConnections.decrementAndGet();
                    if (isShort) {
                        shortQueryServiceTimes.add(serviceTime);
                    } else {
                        longQueryServiceTimes.add(serviceTime);
                    }
                }
            });
            futures.add(future);
        }

        futures.removeIf(Future::isDone);
    }

    private MixedTransactionMetrics buildMixedTransactionMetrics(
            int shortCount, int longCount,
            List<Double> shortWaitTimes, List<Double> longWaitTimes,
            List<Double> shortServiceTimes, List<Double> longServiceTimes,
            int shortTimeouts, int longTimeouts,
            int totalRequests, WorkloadProfile workload) {

        if (workload.getMixedTransactionConfig() == null || !workload.getMixedTransactionConfig().isEnabled()) {
            return null;
        }

        double shortAvgWait = shortWaitTimes.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double longAvgWait = longWaitTimes.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double shortAvgService = shortServiceTimes.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double longAvgService = longServiceTimes.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double shortP95 = calculatePercentile(shortWaitTimes, 95);
        double longP95 = calculatePercentile(longWaitTimes, 95);
        double shortTimeoutRate = shortCount > 0 ? (double) shortTimeouts / shortCount : 0;
        double longTimeoutRate = longCount > 0 ? (double) longTimeouts / longCount : 0;
        double ratio = totalRequests > 0 ? (double) shortCount / totalRequests : 0;

        return MixedTransactionMetrics.builder()
                .shortQueryCount(shortCount)
                .longQueryCount(longCount)
                .shortQueryAvgWaitTimeMs(shortAvgWait)
                .longQueryAvgWaitTimeMs(longAvgWait)
                .shortQueryAvgServiceTimeMs(shortAvgService)
                .longQueryAvgServiceTimeMs(longAvgService)
                .shortQueryP95WaitTimeMs(shortP95)
                .longQueryP95WaitTimeMs(longP95)
                .shortQueryTimeoutRate(shortTimeoutRate)
                .longQueryTimeoutRate(longTimeoutRate)
                .shortQueryRatio(ratio)
                .build();
    }

    private BurstinessMetrics buildBurstinessMetrics(List<Double> arrivalRateSamples,
                                                      List<Double> interArrivalTimes,
                                                      WorkloadProfile workload,
                                                      MarkovArrivalProcess markovProcess) {
        if (markovProcess == null) {
            return null;
        }

        double avgRate = arrivalRateSamples.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double peakRate = arrivalRateSamples.stream().mapToDouble(Double::doubleValue).max().orElse(0);
        double valleyRate = arrivalRateSamples.stream().mapToDouble(Double::doubleValue).min().orElse(0);

        double rateVariance = 0;
        if (avgRate > 0) {
            rateVariance = arrivalRateSamples.stream()
                    .mapToDouble(r -> Math.pow(r - avgRate, 2))
                    .average().orElse(0);
        }
        double rateCV = avgRate > 0 ? Math.sqrt(rateVariance) / avgRate : 0;
        double burstinessIndex = 1 + rateCV;

        int burstCount = 0;
        double burstThreshold = avgRate * 1.5;
        boolean inBurst = false;
        double burstDurationSum = 0;
        int burstStartIdx = 0;
        double maxBurstRate = 0;

        for (int i = 0; i < arrivalRateSamples.size(); i++) {
            double rate = arrivalRateSamples.get(i);
            if (rate > burstThreshold) {
                maxBurstRate = Math.max(maxBurstRate, rate);
                if (!inBurst) {
                    inBurst = true;
                    burstCount++;
                    burstStartIdx = i;
                }
            } else {
                if (inBurst) {
                    burstDurationSum += (i - burstStartIdx) * 100;
                    inBurst = false;
                }
            }
        }
        if (inBurst) {
            burstDurationSum += (arrivalRateSamples.size() - burstStartIdx) * 100;
        }
        double avgBurstDuration = burstCount > 0 ? burstDurationSum / burstCount : 0;

        double interArrivalSCV = 1.0;
        if (!interArrivalTimes.isEmpty()) {
            double meanIA = interArrivalTimes.stream().mapToDouble(Double::doubleValue).average().orElse(1);
            if (meanIA > 0) {
                double varIA = interArrivalTimes.stream()
                        .mapToDouble(t -> Math.pow(t - meanIA, 2))
                        .average().orElse(0);
                interArrivalSCV = varIA / (meanIA * meanIA);
            }
        }

        return BurstinessMetrics.builder()
                .burstinessIndex(burstinessIndex)
                .squaredCoefficientOfVariation(rateCV * rateCV)
                .peakArrivalRate(peakRate)
                .valleyArrivalRate(valleyRate)
                .avgArrivalRate(avgRate)
                .burstCount(burstCount)
                .avgBurstDurationMs(avgBurstDuration)
                .maxBurstArrivalRate(maxBurstRate)
                .interArrivalSquaredCV(interArrivalSCV)
                .build();
    }

    private SimulationResult buildSimulationResult(PoolConfig config, WorkloadProfile workload,
                                                   List<Double> waitTimeSamples,
                                                   Map<Integer, Double> utilizationOverTime,
                                                   int totalRequests, int failedRequests,
                                                   int timeoutCount, int peakActive,
                                                   QueueMetrics queueMetrics,
                                                   MixedTransactionMetrics mixedMetrics,
                                                   BurstinessMetrics burstinessMetrics) {
        double avgWaitTime = waitTimeSamples.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double maxWaitTime = waitTimeSamples.stream().mapToDouble(Double::doubleValue).max().orElse(0);
        double percentile95 = calculatePercentile(waitTimeSamples, 95);
        double avgUtilization = utilizationOverTime.values().stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double throughput = totalRequests * 1000.0 / workload.getSimulationDurationMs();
        double rejectRate = totalRequests > 0 ? (double) failedRequests / totalRequests : 0;

        return SimulationResult.builder()
                .config(config)
                .workload(workload)
                .avgWaitTimeMs(avgWaitTime)
                .maxWaitTimeMs(maxWaitTime)
                .percentile95WaitTimeMs(percentile95)
                .avgActiveConnections(peakActive * avgUtilization)
                .avgIdleConnections(config.getMaxPoolSize() - (peakActive * avgUtilization))
                .connectionUtilization(avgUtilization)
                .throughput(throughput)
                .totalRequests(totalRequests)
                .failedRequests(failedRequests)
                .timeoutCount(timeoutCount)
                .rejectRate(rejectRate)
                .waitTimeSamples(waitTimeSamples.size() > 1000 ?
                        waitTimeSamples.subList(0, 1000) : waitTimeSamples)
                .utilizationOverTime(utilizationOverTime)
                .queueMetrics(queueMetrics)
                .mixedTransactionMetrics(mixedMetrics)
                .burstinessMetrics(burstinessMetrics)
                .build();
    }

    private int getPoissonRandom(double lambda) {
        if (lambda <= 0) return 0;
        double L = Math.exp(-lambda);
        double p = 1.0;
        int k = 0;
        do {
            k++;
            p *= random.nextDouble();
        } while (p > L && k < 1000);
        return k - 1;
    }

    private double getGaussianRandom(double mean, double stdDev) {
        double value = mean + random.nextGaussian() * stdDev;
        return Math.max(1, value);
    }

    private double calculatePercentile(List<Double> values, int percentile) {
        if (values.isEmpty()) return 0;
        List<Double> sorted = new ArrayList<>(values);
        Collections.sort(sorted);
        int index = (int) Math.ceil(percentile / 100.0 * sorted.size()) - 1;
        return sorted.get(Math.max(0, Math.min(index, sorted.size() - 1)));
    }

    private void sleepUninterruptibly(long ms) {
        try {
            Thread.sleep(Math.max(1, ms / 10));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private static class SimulationRequest {
        final long timestamp;
        final boolean isShortQuery;
        final double serviceTime;

        SimulationRequest(long timestamp, boolean isShortQuery, double serviceTime) {
            this.timestamp = timestamp;
            this.isShortQuery = isShortQuery;
            this.serviceTime = serviceTime;
        }
    }

    private static class MarkovArrivalProcess {
        private int currentState;
        private final MarkovArrivalConfig config;
        private final Random random;

        MarkovArrivalProcess(MarkovArrivalConfig config, Random random) {
            this.config = config;
            this.random = random;
            this.currentState = 0;
        }

        double getCurrentArrivalRate() {
            return config.getArrivalRates()[currentState];
        }

        int generateRequests(long timeStepMs) {
            double rate = getCurrentArrivalRate();
            double lambda = rate * timeStepMs / 1000.0;

            if (lambda <= 0) return 0;
            double L = Math.exp(-lambda);
            double p = 1.0;
            int k = 0;
            do {
                k++;
                p *= random.nextDouble();
            } while (p > L && k < 1000);
            return k - 1;
        }

        void transition() {
            double[] row = config.getTransitionMatrix()[currentState];
            double r = random.nextDouble();
            double cumulative = 0;
            for (int j = 0; j < row.length; j++) {
                cumulative += row[j];
                if (r <= cumulative) {
                    currentState = j;
                    return;
                }
            }
            currentState = row.length - 1;
        }
    }

    private static class MixedTransactionProfile {
        private final MixedTransactionConfig config;
        private final Random random;

        MixedTransactionProfile(MixedTransactionConfig config, Random random) {
            this.config = config;
            this.random = random;
        }

        boolean isShortQuery() {
            return random.nextDouble() < config.getShortQueryRatio();
        }

        double generateServiceTime(boolean isShort) {
            if (isShort) {
                double value = config.getShortQueryAvgTimeMs() +
                        random.nextGaussian() * config.getShortQueryStdDevMs();
                return Math.max(1, value);
            } else {
                double value = config.getLongQueryAvgTimeMs() +
                        random.nextGaussian() * config.getLongQueryStdDevMs();
                return Math.max(config.getShortQueryAvgTimeMs(), value);
            }
        }
    }
}
