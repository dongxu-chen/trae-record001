package com.dbpool.optimizer.core;

import com.dbpool.optimizer.model.*;
import org.apache.commons.math3.distribution.NormalDistribution;
import org.springframework.stereotype.Component;

@Component
public class QueueingTheoryAnalyzer {

    public QueueMetrics analyze(PoolConfig config, WorkloadProfile workload) {
        int servers = config.getMaxPoolSize();
        double arrivalRate = workload.getArrivalRate();
        double serviceRate = 1000.0 / workload.getAvgServiceTimeMs();
        double trafficIntensity = arrivalRate / (servers * serviceRate);

        if (trafficIntensity >= 1.0) {
            trafficIntensity = 0.95;
        }

        double erlangC = calculateErlangC(servers, arrivalRate / serviceRate);
        double avgWaitTimeMs = calculateAvgWaitTime(servers, arrivalRate, serviceRate, erlangC);
        double avgQueueLength = arrivalRate * avgWaitTimeMs / 1000.0;
        double probabilityOfWaiting = erlangC;

        double burstinessIndex = 1.0;
        double squaredCV = 1.0;
        double mapEffectiveRate = arrivalRate;

        if (workload.getMarkovArrivalConfig() != null && workload.getMarkovArrivalConfig().isEnabled()) {
            MAPAnalysisResult mapResult = analyzeMAP(config, workload);
            burstinessIndex = mapResult.burstinessIndex;
            squaredCV = mapResult.squaredCV;
            mapEffectiveRate = mapResult.effectiveArrivalRate;
            avgWaitTimeMs = mapResult.adjustedWaitTimeMs;
            avgQueueLength = mapResult.adjustedQueueLength;
            probabilityOfWaiting = Math.min(1.0, erlangC * burstinessIndex);
        }

        return QueueMetrics.builder()
                .avgQueueLength(avgQueueLength)
                .maxQueueLength(calculateMaxQueueLength(avgQueueLength, workload.getVarianceFactor()))
                .avgQueueWaitTimeMs(avgWaitTimeMs)
                .serverUtilization(trafficIntensity)
                .probabilityOfWaiting(probabilityOfWaiting)
                .erlangC(erlangC)
                .effectiveServers(calculateEffectiveServers(servers, trafficIntensity))
                .trafficIntensity(trafficIntensity)
                .burstinessIndex(burstinessIndex)
                .squaredCoefficientOfVariation(squaredCV)
                .mapEffectiveArrivalRate(mapEffectiveRate)
                .build();
    }

    public MAPAnalysisResult analyzeMAP(PoolConfig config, WorkloadProfile workload) {
        MarkovArrivalConfig mapConfig = workload.getMarkovArrivalConfig();
        int stateCount = mapConfig.getStateCount();
        double[][] transitionMatrix = mapConfig.getTransitionMatrix();
        double[] arrivalRates = mapConfig.getArrivalRates();

        double[] steadyState = computeSteadyState(transitionMatrix, stateCount);

        double effectiveArrivalRate = 0;
        for (int i = 0; i < stateCount; i++) {
            effectiveArrivalRate += steadyState[i] * arrivalRates[i];
        }

        double scvArrival = computeMAPSquaredCV(transitionMatrix, arrivalRates, steadyState, stateCount);

        double burstinessIndex = scvArrival;
        if (mapConfig.getBurstinessFactor() > 0) {
            burstinessIndex = Math.max(scvArrival, mapConfig.getBurstinessFactor());
        }

        int servers = config.getMaxPoolSize();
        double serviceRate = 1000.0 / workload.getAvgServiceTimeMs();
        double offeredLoad = effectiveArrivalRate / serviceRate;
        double erlangC = calculateErlangC(servers, offeredLoad);

        double adjustedWaitTimeMs;
        if (effectiveArrivalRate > 0 && servers * serviceRate > effectiveArrivalRate) {
            double baseWait = (erlangC * 1000.0) / (servers * serviceRate - effectiveArrivalRate);
            adjustedWaitTimeMs = baseWait * (1 + (burstinessIndex - 1) * 0.5);
        } else {
            adjustedWaitTimeMs = Double.MAX_VALUE / 2;
        }

        double adjustedQueueLength = effectiveArrivalRate * adjustedWaitTimeMs / 1000.0;

        return new MAPAnalysisResult(effectiveArrivalRate, scvArrival, burstinessIndex,
                adjustedWaitTimeMs, adjustedQueueLength);
    }

    private double[] computeSteadyState(double[][] transitionMatrix, int stateCount) {
        double[][] A = new double[stateCount][stateCount + 1];
        for (int i = 0; i < stateCount; i++) {
            for (int j = 0; j < stateCount; j++) {
                A[i][j] = transitionMatrix[j][i];
            }
            A[i][i] -= 1.0;
        }
        for (int j = 0; j < stateCount; j++) {
            A[stateCount - 1][j] = 1.0;
        }
        A[stateCount - 1][stateCount] = 1.0;

        return solveLinearSystem(A, stateCount);
    }

    private double[] solveLinearSystem(double[][] A, int n) {
        for (int i = 0; i < n; i++) {
            int maxRow = i;
            for (int k = i + 1; k < n; k++) {
                if (Math.abs(A[k][i]) > Math.abs(A[maxRow][i])) {
                    maxRow = k;
                }
            }
            double[] temp = A[i];
            A[i] = A[maxRow];
            A[maxRow] = temp;

            if (Math.abs(A[i][i]) < 1e-12) continue;

            for (int k = i + 1; k < n; k++) {
                double factor = A[k][i] / A[i][i];
                for (int j = i; j <= n; j++) {
                    A[k][j] -= factor * A[i][j];
                }
            }
        }

        double[] x = new double[n];
        for (int i = n - 1; i >= 0; i--) {
            double sum = A[i][n];
            for (int j = i + 1; j < n; j++) {
                sum -= A[i][j] * x[j];
            }
            x[i] = Math.abs(A[i][i]) < 1e-12 ? 0 : sum / A[i][i];
        }

        double sum = 0;
        for (double v : x) sum += v;
        if (sum > 0) {
            for (int i = 0; i < n; i++) x[i] /= sum;
        }

        return x;
    }

    private double computeMAPSquaredCV(double[][] transitionMatrix, double[] arrivalRates,
                                        double[] steadyState, int stateCount) {
        double meanRate = 0;
        for (int i = 0; i < stateCount; i++) {
            meanRate += steadyState[i] * arrivalRates[i];
        }

        if (meanRate <= 0) return 1.0;

        double meanInterArrival = 1.0 / meanRate;

        double variance = 0;
        for (int i = 0; i < stateCount; i++) {
            double diff = (1.0 / arrivalRates[i]) - meanInterArrival;
            variance += steadyState[i] * diff * diff;
        }

        double scv = variance / (meanInterArrival * meanInterArrival);

        double[][] P = transitionMatrix;
        double[] fundamentalRates = new double[stateCount];
        for (int i = 0; i < stateCount; i++) {
            double sumP = 0;
            for (int j = 0; j < stateCount; j++) {
                if (j != i) sumP += P[i][j];
            }
            fundamentalRates[i] = Math.max(sumP * arrivalRates[i], arrivalRates[i] * 0.1);
        }

        double crossCorrelation = 0;
        for (int i = 0; i < stateCount; i++) {
            for (int j = 0; j < stateCount; j++) {
                if (i != j) {
                    crossCorrelation += steadyState[i] * P[i][j] *
                            (1.0 / arrivalRates[i]) * (1.0 / arrivalRates[j]);
                }
            }
        }

        scv += 2 * crossCorrelation / (meanInterArrival * meanInterArrival);
        scv = Math.max(scv, 1.0);

        return scv;
    }

    public double calculateErlangC(int servers, double offeredLoad) {
        if (offeredLoad <= 0) return 0.0;
        if (servers <= 0) return 1.0;

        double numerator = (Math.pow(offeredLoad, servers) / factorial(servers)) * (servers / (servers - offeredLoad));
        double denominator = 0.0;

        for (int k = 0; k < servers; k++) {
            denominator += Math.pow(offeredLoad, k) / factorial(k);
        }
        denominator += numerator;

        if (denominator == 0) return 0.0;
        return Math.min(1.0, numerator / denominator);
    }

    public double calculateAvgWaitTime(int servers, double arrivalRate, double serviceRate, double erlangC) {
        if (arrivalRate <= 0 || servers <= 0) return 0.0;
        return (erlangC * 1000.0) / (servers * serviceRate - arrivalRate);
    }

    public double calculateRequiredServers(double targetWaitTimeMs, WorkloadProfile workload) {
        double arrivalRate = workload.getArrivalRate();
        double avgServiceTimeMs = workload.getAvgServiceTimeMs();
        double serviceRate = 1000.0 / avgServiceTimeMs;

        double burstinessFactor = 1.0;
        if (workload.getMarkovArrivalConfig() != null && workload.getMarkovArrivalConfig().isEnabled()) {
            burstinessFactor = Math.max(1.0, workload.getMarkovArrivalConfig().getBurstinessFactor());
        }

        int servers = 1;
        int maxServers = 100;

        while (servers < maxServers) {
            double offeredLoad = arrivalRate / serviceRate;
            if (offeredLoad >= servers) {
                servers++;
                continue;
            }

            double erlangC = calculateErlangC(servers, offeredLoad);
            double waitTime = calculateAvgWaitTime(servers, arrivalRate, serviceRate, erlangC);
            waitTime *= (1 + (burstinessFactor - 1) * 0.5);

            if (waitTime <= targetWaitTimeMs) {
                return servers;
            }
            servers++;
        }

        return maxServers;
    }

    public double calculateRequiredServersWithConstraint(double targetWaitTimeMs, WorkloadProfile workload,
                                                          DatabaseConstraint constraint) {
        int theoreticalServers = (int) calculateRequiredServers(targetWaitTimeMs, workload);
        int dbLimit = constraint != null ? constraint.getAvailableConnections() : Integer.MAX_VALUE;
        return Math.min(theoreticalServers, dbLimit);
    }

    public double calculateOptimalUtilization(double targetWaitTimeMs, WorkloadProfile workload) {
        double avgServiceTimeMs = workload.getAvgServiceTimeMs();
        double coefficientOfVariation = workload.getServiceTimeStdDevMs() / avgServiceTimeMs;

        double baseUtilization = 0.7;

        if (workload.getMarkovArrivalConfig() != null && workload.getMarkovArrivalConfig().isEnabled()) {
            double burstiness = workload.getMarkovArrivalConfig().getBurstinessFactor();
            baseUtilization -= (burstiness - 1) * 0.08;
        }

        if (coefficientOfVariation > 1.0) {
            baseUtilization -= (coefficientOfVariation - 1.0) * 0.1;
        }

        if (targetWaitTimeMs < avgServiceTimeMs * 0.5) {
            baseUtilization -= 0.15;
        } else if (targetWaitTimeMs < avgServiceTimeMs) {
            baseUtilization -= 0.05;
        }

        return Math.max(0.3, Math.min(0.9, baseUtilization));
    }

    private double calculateMaxQueueLength(double avgQueueLength, double varianceFactor) {
        if (avgQueueLength <= 0) return 0;
        NormalDistribution normal = new NormalDistribution(avgQueueLength, avgQueueLength * varianceFactor);
        return normal.inverseCumulativeProbability(0.95);
    }

    private int calculateEffectiveServers(int servers, double utilization) {
        return (int) Math.ceil(servers * utilization);
    }

    private double factorial(int n) {
        if (n <= 1) return 1.0;
        double result = 1.0;
        for (int i = 2; i <= n; i++) {
            result *= i;
        }
        return result;
    }

    public static class MAPAnalysisResult {
        public final double effectiveArrivalRate;
        public final double squaredCV;
        public final double burstinessIndex;
        public final double adjustedWaitTimeMs;
        public final double adjustedQueueLength;

        public MAPAnalysisResult(double effectiveArrivalRate, double squaredCV,
                                  double burstinessIndex, double adjustedWaitTimeMs,
                                  double adjustedQueueLength) {
            this.effectiveArrivalRate = effectiveArrivalRate;
            this.squaredCV = squaredCV;
            this.burstinessIndex = burstinessIndex;
            this.adjustedWaitTimeMs = adjustedWaitTimeMs;
            this.adjustedQueueLength = adjustedQueueLength;
        }
    }
}
