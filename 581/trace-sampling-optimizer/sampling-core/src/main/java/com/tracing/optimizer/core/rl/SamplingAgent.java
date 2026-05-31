package com.tracing.optimizer.core.rl;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class SamplingAgent {

    private static final Logger log = LoggerFactory.getLogger(SamplingAgent.class);

    private final double learningRate;
    private final double discountFactor;
    private final double explorationRate;
    private final double explorationDecay;
    private final double minExplorationRate;
    private final int actionBins;

    private final Map<String, double[]> qTables;
    private final Map<Integer, double[]> reducedQTables;
    private final Random random;
    private final List<Experience> replayBuffer;
    private final int replayBufferSize;
    private final int batchSize;
    private final StateReducer stateReducer;
    private final boolean useStateReduction;
    private final Map<String, Integer> serviceStateCache;

    public SamplingAgent() {
        this(0.1, 0.95, 0.3, 0.995, 0.05, 20, true, 16, 1024);
    }

    public SamplingAgent(double learningRate, double discountFactor, double explorationRate,
                         double explorationDecay, double minExplorationRate, int actionBins,
                         boolean useStateReduction, int targetDimensions, int hashBuckets) {
        this.learningRate = learningRate;
        this.discountFactor = discountFactor;
        this.explorationRate = explorationRate;
        this.explorationDecay = explorationDecay;
        this.minExplorationRate = minExplorationRate;
        this.actionBins = actionBins;
        this.qTables = new HashMap<>();
        this.reducedQTables = new HashMap<>();
        this.random = new Random();
        this.replayBuffer = new ArrayList<>();
        this.replayBufferSize = 10000;
        this.batchSize = 32;
        this.useStateReduction = useStateReduction;
        this.stateReducer = useStateReduction
                ? new StateReducer(targetDimensions, hashBuckets, false)
                : null;
        this.serviceStateCache = new HashMap<>();
    }

    public Map<String, Double> selectActions(SamplingEnvironment.State state) {
        Map<String, Double> actions = new LinkedHashMap<>();

        for (SamplingEnvironment.ServiceState ss : state.serviceStates) {
            double[] qTable;
            int actionIdx;

            if (useStateReduction && stateReducer != null) {
                int reducedState = stateReducer.reduceState(ss);
                serviceStateCache.put(ss.serviceName, reducedState);
                ensureReducedQTableExists(reducedState);
                qTable = reducedQTables.get(reducedState);
                log.debug("Using reduced state {} for service {}", reducedState, ss.serviceName);
            } else {
                ensureQTableExists(ss.serviceName);
                qTable = qTables.get(ss.serviceName);
            }

            if (random.nextDouble() < explorationRate) {
                actionIdx = random.nextInt(actionBins);
            } else {
                actionIdx = argMax(qTable);
            }

            double rate = actionIndexToRate(actionIdx);
            actions.put(ss.serviceName, rate);
        }

        return actions;
    }

    public void learn(String serviceName, int stateHash, int actionIdx, double reward,
                      int nextStateHash, boolean done) {
        double[] qTable;
        int learningKey;

        if (useStateReduction && stateReducer != null) {
            Integer reducedState = serviceStateCache.get(serviceName);
            if (reducedState == null) reducedState = stateHash;
            ensureReducedQTableExists(reducedState);
            qTable = reducedQTables.get(reducedState);
            learningKey = reducedState;
            log.debug("Learning on reduced state {} for service {}, reward={}",
                    reducedState, serviceName, reward);
        } else {
            ensureQTableExists(serviceName);
            qTable = qTables.get(serviceName);
            learningKey = serviceName.hashCode();
        }

        Experience exp = new Experience(learningKey, actionIdx, reward, nextStateHash, done);
        replayBuffer.add(exp);
        if (replayBuffer.size() > replayBufferSize) {
            replayBuffer.remove(0);
        }

        if (replayBuffer.size() >= batchSize) {
            replayLearn(learningKey);
        }

        double maxNextQ = done ? 0.0 : qTable[actionIdx % actionBins];
        double tdTarget = reward + discountFactor * maxNextQ;
        double tdError = tdTarget - qTable[actionIdx];
        qTable[actionIdx] += learningRate * tdError;
    }

    private void replayLearn(int learningKey) {
        double[] qTable;
        if (useStateReduction && stateReducer != null) {
            qTable = reducedQTables.get(learningKey);
        } else {
            qTable = qTables.get(learningKey);
        }
        if (qTable == null) return;

        List<Experience> batch = sampleBatch();
        for (Experience exp : batch) {
            double maxNextQ = exp.done ? 0.0 : qTable[exp.nextAction % actionBins];
            double tdTarget = exp.reward + discountFactor * maxNextQ;
            qTable[exp.action] += learningRate * 0.5 * (tdTarget - qTable[exp.action]);
        }
    }

    private List<Experience> sampleBatch() {
        List<Experience> batch = new ArrayList<>(batchSize);
        for (int i = 0; i < batchSize && i < replayBuffer.size(); i++) {
            batch.add(replayBuffer.get(random.nextInt(replayBuffer.size())));
        }
        return batch;
    }

    public void decayExploration() {
        double newRate = explorationRate * explorationDecay;
        double clamped = Math.max(minExplorationRate, newRate);
        log.debug("Exploration rate: {} -> {}", explorationRate, clamped);
    }

    private void ensureQTableExists(String serviceName) {
        qTables.computeIfAbsent(serviceName, k -> new double[actionBins]);
    }

    private void ensureQTableExists(int key) {
        qTables.computeIfAbsent(String.valueOf(key), k -> new double[actionBins]);
    }

    private void ensureReducedQTableExists(int reducedState) {
        reducedQTables.computeIfAbsent(reducedState, k -> {
            log.debug("Created new Q-table for reduced state {}", reducedState);
            return new double[actionBins];
        });
    }

    private int argMax(double[] arr) {
        int best = 0;
        for (int i = 1; i < arr.length; i++) {
            if (arr[i] > arr[best]) best = i;
        }
        return best;
    }

    private double actionIndexToRate(int idx) {
        return (idx + 1.0) / actionBins;
    }

    public int rateToActionIndex(double rate) {
        int idx = (int) (rate * actionBins) - 1;
        return Math.max(0, Math.min(actionBins - 1, idx));
    }

    public Map<String, double[]> getQTables() { return Collections.unmodifiableMap(qTables); }
    public Map<Integer, double[]> getReducedQTables() { return Collections.unmodifiableMap(reducedQTables); }
    public double getExplorationRate() { return explorationRate; }
    public boolean isUseStateReduction() { return useStateReduction; }
    public StateReducer getStateReducer() { return stateReducer; }

    public Map<String, Object> getReductionStats() {
        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("useStateReduction", useStateReduction);
        if (stateReducer != null) {
            stats.put("targetDimensions", stateReducer.getTargetDimensions());
            stats.put("hashBuckets", stateReducer.getHashBuckets());
            stats.put("uniqueStates", stateReducer.getUniqueStates());
            stats.put("cacheHits", stateReducer.getCacheHits());
            stats.put("cacheMisses", stateReducer.getCacheMisses());
            stats.put("cacheHitRate", String.format("%.2f%%", stateReducer.getCacheHitRate() * 100));
            stats.put("reducedQTablesCount", reducedQTables.size());
            stats.put("serviceStateCacheSize", serviceStateCache.size());
        }
        return stats;
    }

    private static class Experience {
        final int state;
        final int action;
        final double reward;
        final int nextAction;
        final boolean done;

        Experience(int state, int action, double reward, int nextAction, boolean done) {
            this.state = state;
            this.action = action;
            this.reward = reward;
            this.nextAction = nextAction;
            this.done = done;
        }
    }
}
