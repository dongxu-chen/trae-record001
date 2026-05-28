package com.mqmonitor.autoscaler;

import com.mqmonitor.common.config.AutoScalerConfig;
import com.mqmonitor.common.enums.MQType;
import com.mqmonitor.common.model.PredictionResult;
import com.mqmonitor.common.model.QueueMetrics;
import com.mqmonitor.prediction.TimeSeriesPredictor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

public class ConsumerAutoScaler {
    private static final Logger logger = LoggerFactory.getLogger(ConsumerAutoScaler.class);

    private final AutoScalerConfig config;
    private final ScalingStrategyEngine strategyEngine;
    private final TimeSeriesPredictor predictor;
    private final Map<String, GroupState> groupStates = new ConcurrentHashMap<>();
    private final List<ScalingDecision> decisionHistory = Collections.synchronizedList(new ArrayList<>());
    private final Map<String, ScalingActionHandler> actionHandlers = new ConcurrentHashMap<>();

    private volatile boolean running = false;
    private Thread schedulerThread;

    public interface ScalingActionHandler {
        boolean scaleUp(MQType mqType, String clusterName, String topic, String consumerGroup, int targetConsumers);
        boolean scaleDown(MQType mqType, String clusterName, String topic, String consumerGroup, int targetConsumers);
        int getCurrentConsumerCount(MQType mqType, String clusterName, String topic, String consumerGroup);
    }

    private static class GroupState {
        String key;
        MQType mqType;
        String clusterName;
        String topic;
        String consumerGroup;
        int currentConsumers;
        long lastScalingTime;
        AtomicInteger scaleUpCountLastHour = new AtomicInteger(0);
        AtomicInteger scaleDownCountLastHour = new AtomicInteger(0);
        List<Long> scalingTimes = new ArrayList<>();
        List<QueueMetrics> metricsHistory = new ArrayList<>();
        PredictionResult lastPrediction;
        ScalingDecision lastDecision;
        String lastStatus;
        String lastError;

        GroupState(MQType mqType, String clusterName, String topic, String consumerGroup) {
            this.key = mqType + ":" + clusterName + ":" + topic + ":" + consumerGroup;
            this.mqType = mqType;
            this.clusterName = clusterName;
            this.topic = topic;
            this.consumerGroup = consumerGroup;
        }

        synchronized void recordScaling(long time, boolean isScaleUp) {
            scalingTimes.add(time);
            if (isScaleUp) {
                scaleUpCountLastHour.incrementAndGet();
            } else {
                scaleDownCountLastHour.incrementAndGet();
            }
            cleanupOldScalingRecords();
        }

        private void cleanupOldScalingRecords() {
            long cutoff = System.currentTimeMillis() - TimeUnit.HOURS.toMillis(1);
            scalingTimes.removeIf(t -> t < cutoff);
        }

        synchronized int getScaleUpCountLastHour() {
            cleanupOldScalingRecords();
            return (int) scalingTimes.stream()
                    .filter(t -> System.currentTimeMillis() - t < TimeUnit.HOURS.toMillis(1))
                    .count();
        }

        synchronized int getScaleDownCountLastHour() {
            cleanupOldScalingRecords();
            return (int) scalingTimes.stream()
                    .filter(t -> System.currentTimeMillis() - t < TimeUnit.HOURS.toMillis(1))
                    .count();
        }

        synchronized void addMetrics(QueueMetrics metrics) {
            metricsHistory.add(metrics);
            while (metricsHistory.size() > 100) {
                metricsHistory.remove(0);
            }
        }
    }

    public ConsumerAutoScaler(AutoScalerConfig config, TimeSeriesPredictor predictor) {
        this.config = config;
        this.strategyEngine = new ScalingStrategyEngine(config);
        this.predictor = predictor;
    }

    public void registerActionHandler(ScalingActionHandler handler) {
        this.actionHandlers.put("default", handler);
    }

    public void start() {
        if (running) {
            logger.warn("ConsumerAutoScaler already running");
            return;
        }
        running = true;
        schedulerThread = new Thread(this::runScheduler, "consumer-autoscaler");
        schedulerThread.setDaemon(true);
        schedulerThread.start();
        logger.info("ConsumerAutoScaler started with strategy: {}", config.getStrategy());
    }

    public void stop() {
        running = false;
        if (schedulerThread != null) {
            schedulerThread.interrupt();
        }
        logger.info("ConsumerAutoScaler stopped");
    }

    private void runScheduler() {
        while (running && !Thread.currentThread().isInterrupted()) {
            try {
                long interval = Math.max(1000, config.getCheckIntervalMs());
                Thread.sleep(interval);

                if (config.isEnabled()) {
                    evaluateAllGroups();
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                logger.error("Error in auto-scaler scheduler", e);
            }
        }
    }

    public void registerConsumerGroup(MQType mqType, String clusterName, String topic, String consumerGroup) {
        String key = mqType + ":" + clusterName + ":" + topic + ":" + consumerGroup;
        groupStates.computeIfAbsent(key, k -> new GroupState(mqType, clusterName, topic, consumerGroup));
        logger.info("Registered consumer group for auto-scaling: {}", key);
    }

    public void unregisterConsumerGroup(MQType mqType, String clusterName, String topic, String consumerGroup) {
        String key = mqType + ":" + clusterName + ":" + topic + ":" + consumerGroup;
        groupStates.remove(key);
        logger.info("Unregistered consumer group from auto-scaling: {}", key);
    }

    public void reportMetrics(MQType mqType, String clusterName, String topic,
                             String consumerGroup, QueueMetrics metrics) {
        String key = mqType + ":" + clusterName + ":" + topic + ":" + consumerGroup;
        GroupState state = groupStates.get(key);
        if (state == null) {
            state = new GroupState(mqType, clusterName, topic, consumerGroup);
            groupStates.put(key, state);
        }
        state.addMetrics(metrics);
    }

    private void evaluateAllGroups() {
        for (GroupState state : groupStates.values()) {
            try {
                evaluateGroup(state);
            } catch (Exception e) {
                logger.error("Error evaluating group {}", state.key, e);
                state.lastError = e.getMessage();
            }
        }
    }

    public ScalingDecision evaluateGroup(MQType mqType, String clusterName, String topic, String consumerGroup) {
        String key = mqType + ":" + clusterName + ":" + topic + ":" + consumerGroup;
        GroupState state = groupStates.get(key);
        if (state == null) {
            state = new GroupState(mqType, clusterName, topic, consumerGroup);
            groupStates.put(key, state);
        }
        return evaluateGroup(state);
    }

    private ScalingDecision evaluateGroup(GroupState state) {
        ScalingActionHandler handler = actionHandlers.get("default");
        if (handler == null) {
            logger.warn("No scaling action handler registered");
            return null;
        }

        int currentConsumers = handler.getCurrentConsumerCount(
                state.mqType, state.clusterName, state.topic, state.consumerGroup);
        state.currentConsumers = currentConsumers;

        PredictionResult prediction = null;
        if (predictor != null && state.metricsHistory.size() >= 10) {
            try {
                List<Double> lagValues = new ArrayList<>();
                for (QueueMetrics m : state.metricsHistory) {
                    lagValues.add((double) m.getBacklog());
                }
                prediction = predictor.predictBacklog(lagValues, 20);
                state.lastPrediction = prediction;
            } catch (Exception e) {
                logger.warn("Failed to generate prediction for {}", state.key, e);
            }
        }

        ScalingDecision decision = strategyEngine.evaluate(
                state.mqType, state.clusterName, state.topic, state.consumerGroup,
                currentConsumers, state.metricsHistory, prediction, state.lastScalingTime);

        applyRateLimits(decision, state);

        if (decision.getAction() == AutoScalerConfig.ScalingAction.SCALE_UP
                || decision.getAction() == AutoScalerConfig.ScalingAction.SCALE_DOWN) {
            executeScaling(decision, handler, state);
        }

        state.lastDecision = decision;
        state.lastStatus = decision.getAction().toString();
        decisionHistory.add(decision);

        if (decisionHistory.size() > 1000) {
            synchronized (decisionHistory) {
                while (decisionHistory.size() > 1000) {
                    decisionHistory.remove(0);
                }
            }
        }

        return decision;
    }

    private void applyRateLimits(ScalingDecision decision, GroupState state) {
        if (decision.getAction() == AutoScalerConfig.ScalingAction.SCALE_UP) {
            int scaleUps = state.getScaleUpCountLastHour();
            if (scaleUps >= config.getMaxScaleUpPerHour()) {
                decision.setAction(AutoScalerConfig.ScalingAction.NO_CHANGE);
                decision.setReason(String.format("Scale-up rate limit exceeded: %d/%d per hour",
                        scaleUps, config.getMaxScaleUpPerHour()));
                decision.addWarning("Rate limit reached");
                decision.setTargetConsumers(decision.getCurrentConsumers());
                decision.setScaleAmount(0);
            }
        } else if (decision.getAction() == AutoScalerConfig.ScalingAction.SCALE_DOWN) {
            int scaleDowns = state.getScaleDownCountLastHour();
            if (scaleDowns >= config.getMaxScaleDownPerHour()) {
                decision.setAction(AutoScalerConfig.ScalingAction.NO_CHANGE);
                decision.setReason(String.format("Scale-down rate limit exceeded: %d/%d per hour",
                        scaleDowns, config.getMaxScaleDownPerHour()));
                decision.addWarning("Rate limit reached");
                decision.setTargetConsumers(decision.getCurrentConsumers());
                decision.setScaleAmount(0);
            }
        }
    }

    private void executeScaling(ScalingDecision decision, ScalingActionHandler handler, GroupState state) {
        if (config.isDryRun()) {
            logger.info("[DRY RUN] Would {} consumers for {} from {} to {}",
                    decision.getAction(), state.key,
                    decision.getCurrentConsumers(), decision.getTargetConsumers());
            decision.addWarning("Dry run mode - no actual scaling performed");
            return;
        }

        boolean success = false;
        try {
            if (decision.getAction() == AutoScalerConfig.ScalingAction.SCALE_UP) {
                success = handler.scaleUp(state.mqType, state.clusterName, state.topic,
                        state.consumerGroup, decision.getTargetConsumers());
            } else if (decision.getAction() == AutoScalerConfig.ScalingAction.SCALE_DOWN) {
                success = handler.scaleDown(state.mqType, state.clusterName, state.topic,
                        state.consumerGroup, decision.getTargetConsumers());
            }

            if (success) {
                state.lastScalingTime = System.currentTimeMillis();
                state.recordScaling(state.lastScalingTime,
                        decision.getAction() == AutoScalerConfig.ScalingAction.SCALE_UP);
                logger.info("Successfully {} consumers for {} from {} to {}",
                        decision.getAction(), state.key,
                        decision.getCurrentConsumers(), decision.getTargetConsumers());
            } else {
                decision.addWarning("Scaling action failed");
                state.lastError = "Scaling action returned false";
                logger.warn("Failed to {} consumers for {}", decision.getAction(), state.key);
            }
        } catch (Exception e) {
            decision.addWarning("Scaling exception: " + e.getMessage());
            state.lastError = e.getMessage();
            logger.error("Exception while scaling consumers for {}", state.key, e);
        }
    }

    public Map<String, Object> getGroupStatus(MQType mqType, String clusterName, String topic, String consumerGroup) {
        String key = mqType + ":" + clusterName + ":" + topic + ":" + consumerGroup;
        GroupState state = groupStates.get(key);
        if (state == null) {
            return null;
        }

        Map<String, Object> status = new LinkedHashMap<>();
        status.put("key", state.key);
        status.put("mqType", state.mqType);
        status.put("clusterName", state.clusterName);
        status.put("topic", state.topic);
        status.put("consumerGroup", state.consumerGroup);
        status.put("currentConsumers", state.currentConsumers);
        status.put("lastScalingTime", state.lastScalingTime);
        status.put("scaleUpsLastHour", state.getScaleUpCountLastHour());
        status.put("scaleDownsLastHour", state.getScaleDownCountLastHour());
        status.put("status", state.lastStatus);
        status.put("lastError", state.lastError);
        status.put("metricsHistorySize", state.metricsHistory.size());

        if (state.lastDecision != null) {
            status.put("lastDecision", state.lastDecision.toSummary());
        }

        return status;
    }

    public List<Map<String, Object>> getAllGroupStatuses() {
        List<Map<String, Object>> statuses = new ArrayList<>();
        for (GroupState state : groupStates.values()) {
            statuses.add(getGroupStatus(state.mqType, state.clusterName, state.topic, state.consumerGroup));
        }
        return statuses;
    }

    public List<ScalingDecision> getDecisionHistory(int limit) {
        List<ScalingDecision> history;
        synchronized (decisionHistory) {
            history = new ArrayList<>(decisionHistory);
        }
        if (limit > 0 && history.size() > limit) {
            return history.subList(history.size() - limit, history.size());
        }
        return history;
    }

    public Map<String, Object> getStats() {
        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("enabled", config.isEnabled());
        stats.put("strategy", config.getStrategy());
        stats.put("dryRun", config.isDryRun());
        stats.put("registeredGroups", groupStates.size());
        stats.put("totalDecisions", decisionHistory.size());

        long scaleUps = 0, scaleDowns = 0, noChanges = 0;
        for (ScalingDecision d : decisionHistory) {
            switch (d.getAction()) {
                case SCALE_UP: scaleUps++; break;
                case SCALE_DOWN: scaleDowns++; break;
                case NO_CHANGE: noChanges++; break;
            }
        }
        stats.put("scaleUpDecisions", scaleUps);
        stats.put("scaleDownDecisions", scaleDowns);
        stats.put("noChangeDecisions", noChanges);

        return stats;
    }

    public AutoScalerConfig getConfig() {
        return config;
    }

    public ScalingStrategyEngine getStrategyEngine() {
        return strategyEngine;
    }

    public boolean isRunning() {
        return running;
    }
}
