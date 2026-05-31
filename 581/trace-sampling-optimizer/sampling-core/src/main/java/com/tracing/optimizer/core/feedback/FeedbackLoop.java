package com.tracing.optimizer.core.feedback;

import com.tracing.optimizer.core.model.FeedbackSignal;
import com.tracing.optimizer.core.model.SamplingRate;
import com.tracing.optimizer.core.model.ServiceMetadata;
import com.tracing.optimizer.core.model.TraceMetrics;
import com.tracing.optimizer.core.rl.SamplingAgent;
import com.tracing.optimizer.core.rl.SamplingEnvironment;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;

public class FeedbackLoop {

    private static final Logger log = LoggerFactory.getLogger(FeedbackLoop.class);

    private final BlockingQueue<FeedbackSignal> signalQueue;
    private final Map<String, List<FeedbackSignal>> signalHistory;
    private final SamplingAgent agent;
    private final SamplingEnvironment environment;
    private final ScheduledExecutorService scheduler;
    private final long evaluationIntervalMs;
    private final int historyWindowSize;
    private final double adjustmentSensitivity;
    private volatile boolean running;

    public FeedbackLoop(SamplingAgent agent, SamplingEnvironment environment,
                        long evaluationIntervalMs) {
        this.signalQueue = new LinkedBlockingQueue<>();
        this.signalHistory = new ConcurrentHashMap<>();
        this.agent = agent;
        this.environment = environment;
        this.evaluationIntervalMs = evaluationIntervalMs;
        this.historyWindowSize = 100;
        this.adjustmentSensitivity = 0.1;
        this.scheduler = Executors.newScheduledThreadPool(2);
        this.running = false;
    }

    public void start() {
        if (running) return;
        running = true;
        scheduler.scheduleAtFixedRate(this::processSignals, 0,
                evaluationIntervalMs, TimeUnit.MILLISECONDS);
        scheduler.scheduleAtFixedRate(this::evaluateFeedbackWindow,
                evaluationIntervalMs * 2, evaluationIntervalMs, TimeUnit.MILLISECONDS);
        log.info("Feedback loop started with interval {}ms", evaluationIntervalMs);
    }

    public void stop() {
        running = false;
        scheduler.shutdown();
        try {
            if (!scheduler.awaitTermination(5, TimeUnit.SECONDS)) {
                scheduler.shutdownNow();
            }
        } catch (InterruptedException e) {
            scheduler.shutdownNow();
            Thread.currentThread().interrupt();
        }
        log.info("Feedback loop stopped");
    }

    public void submitSignal(FeedbackSignal signal) {
        signalQueue.offer(signal);
        signalHistory.computeIfAbsent(signal.getServiceName(), k -> new CopyOnWriteArrayList<>())
                .add(signal);
        if (signalHistory.get(signal.getServiceName()).size() > historyWindowSize) {
            List<FeedbackSignal> list = signalHistory.get(signal.getServiceName());
            list.subList(0, list.size() - historyWindowSize).clear();
        }
    }

    private void processSignals() {
        List<FeedbackSignal> batch = new ArrayList<>();
        signalQueue.drainTo(batch);

        if (batch.isEmpty()) return;

        Map<String, Double> adjustments = new LinkedHashMap<>();

        for (FeedbackSignal signal : batch) {
            String svc = signal.getServiceName();
            double adjustment = computeAdjustment(signal);
            adjustments.merge(svc, adjustment, Double::sum);
            log.info("Processing signal: {} for service {} -> adjustment {}",
                    signal.getSignalType(), svc, adjustment);
        }

        if (!adjustments.isEmpty()) {
            Map<String, Double> currentRates = environment.getCurrentRates();
            Map<String, Double> newRates = new LinkedHashMap<>();

            for (Map.Entry<String, Double> entry : adjustments.entrySet()) {
                String svc = entry.getKey();
                double current = currentRates.getOrDefault(svc, 0.1);
                double adjusted = Math.max(0.01, Math.min(1.0, current + entry.getValue()));
                newRates.put(svc, adjusted);
            }

            Map<String, Double> rewards = environment.step(newRates);
            for (Map.Entry<String, Double> entry : rewards.entrySet()) {
                String svc = entry.getKey();
                int actionIdx = agent.rateToActionIndex(newRates.get(svc));
                agent.learn(svc, environment.getStepCount(), actionIdx, entry.getValue(),
                        environment.getStepCount() + 1, false);
            }

            agent.decayExploration();
        }
    }

    private double computeAdjustment(FeedbackSignal signal) {
        double baseAdjustment = 0.0;
        switch (signal.getSignalType()) {
            case ERROR_RATE_INCREASED:
                baseAdjustment = 0.2 * signal.getSeverity();
                break;
            case LATENCY_DEGRADED:
                baseAdjustment = 0.15 * signal.getSeverity();
                break;
            case MISSING_CRITICAL_TRACE:
                baseAdjustment = 0.25 * signal.getSeverity();
                break;
            case FALSE_POSITIVE_ANOMALY:
                baseAdjustment = -0.1 * signal.getSeverity();
                break;
            case COST_OVERRUN:
                baseAdjustment = -0.15 * signal.getSeverity();
                break;
            case OBSERVABILITY_GAP:
                baseAdjustment = 0.1 * signal.getSeverity();
                break;
            case SAMPLING_EFFECTIVE:
                baseAdjustment = 0.0;
                break;
        }
        if (signal.getSuggestedRate() > 0) {
            return (signal.getSuggestedRate() - signal.getPreviousSamplingRate()) * adjustmentSensitivity;
        }
        return baseAdjustment * adjustmentSensitivity;
    }

    private void evaluateFeedbackWindow() {
        Instant cutoff = Instant.now().minus(Duration.ofMinutes(5));
        for (Map.Entry<String, List<FeedbackSignal>> entry : signalHistory.entrySet()) {
            String svc = entry.getKey();
            List<FeedbackSignal> signals = entry.getValue();
            long negativeSignals = signals.stream()
                    .filter(s -> s.getTimestamp().isAfter(cutoff))
                    .filter(s -> s.getSignalType() != FeedbackSignal.SignalType.SAMPLING_EFFECTIVE)
                    .count();

            if (negativeSignals > 10) {
                log.warn("Service {} has {} negative feedback signals in last 5 minutes, "
                        + "triggering emergency sampling rate increase", svc, negativeSignals);
                Map<String, Double> emergencyRate = new LinkedHashMap<>();
                emergencyRate.put(svc, 1.0);
                environment.step(emergencyRate);
            }
        }
    }

    public FeedbackAnalysis analyzeFeedback(String serviceName) {
        List<FeedbackSignal> signals = signalHistory.getOrDefault(serviceName, Collections.emptyList());
        FeedbackAnalysis analysis = new FeedbackAnalysis();
        analysis.serviceName = serviceName;
        analysis.totalSignals = signals.size();

        for (FeedbackSignal signal : signals) {
            switch (signal.getSignalType()) {
                case ERROR_RATE_INCREASED: analysis.errorRateSignals++; break;
                case LATENCY_DEGRADED: analysis.latencySignals++; break;
                case MISSING_CRITICAL_TRACE: analysis.missingTraceSignals++; break;
                case COST_OVERRUN: analysis.costOverrunSignals++; break;
                case SAMPLING_EFFECTIVE: analysis.effectiveSignals++; break;
                default: break;
            }
            analysis.avgSeverity += signal.getSeverity();
        }

        if (!signals.isEmpty()) {
            analysis.avgSeverity /= signals.size();
        }
        return analysis;
    }

    public static class FeedbackAnalysis {
        public String serviceName;
        public int totalSignals;
        public int errorRateSignals;
        public int latencySignals;
        public int missingTraceSignals;
        public int costOverrunSignals;
        public int effectiveSignals;
        public double avgSeverity;
    }
}
