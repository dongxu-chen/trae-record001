package com.coupon.rl.agent;

import com.coupon.model.CouponDistribution;
import com.coupon.model.UserProfile;
import com.coupon.rl.buffer.ReplayBuffer;
import com.coupon.rl.config.RLConfig;
import com.coupon.rl.model.CouponAction;
import com.coupon.rl.model.Experience;
import com.coupon.rl.network.DQNNetwork;
import com.coupon.rl.reward.RewardCalculator;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import org.nd4j.linalg.api.ndarray.INDArray;
import org.nd4j.linalg.factory.Nd4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Component
public class DQNAgent {

    private final DQNNetwork dqnNetwork;
    private final ReplayBuffer replayBuffer;
    private final RewardCalculator rewardCalculator;
    private final RLConfig rlConfig;

    private final AtomicInteger trainStepCounter = new AtomicInteger(0);

    @Getter
    private volatile double epsilon;

    @Value("${coupon.rl.avoid-duplicate-coupons:true}")
    private boolean avoidDuplicateCoupons;

    public DQNAgent(DQNNetwork dqnNetwork, ReplayBuffer replayBuffer,
                    RewardCalculator rewardCalculator, RLConfig rlConfig) {
        this.dqnNetwork = dqnNetwork;
        this.replayBuffer = replayBuffer;
        this.rewardCalculator = rewardCalculator;
        this.rlConfig = rlConfig;
        this.epsilon = rlConfig.getEpsilonStart();
    }

    public CouponAction selectAction(UserProfile userProfile) {
        return selectAction(userProfile, avoidDuplicateCoupons);
    }

    public CouponAction selectAction(UserProfile userProfile, boolean avoidDuplicates) {
        double[] stateVector = userProfile.toStateVector();
        INDArray state = Nd4j.create(stateVector, new int[]{1, stateVector.length});

        int actionIndex;
        if (rlConfig.isTrainEnabled() && Math.random() < epsilon) {
            actionIndex = selectRandomAction(userProfile, avoidDuplicates);
        } else {
            actionIndex = selectGreedyAction(userProfile, avoidDuplicates);
        }

        log.debug("Selected action {} for user {}, epsilon={}, avoidDuplicate={}",
                actionIndex, userProfile.getUserId(), epsilon, avoidDuplicates);

        return CouponAction.fromIndex(actionIndex);
    }

    private int selectRandomAction(UserProfile userProfile, boolean avoidDuplicates) {
        int totalActions = CouponAction.getTotalActions();
        if (!avoidDuplicates) {
            return (int) (Math.random() * totalActions);
        }

        List<Integer> validActions = new ArrayList<>();
        for (int i = 0; i < totalActions; i++) {
            CouponAction action = CouponAction.fromIndex(i);
            int typeCode = action.getCouponType().getCode();
            int denom = action.getDenomination().intValue();
            if (!userProfile.hasRecentSimilarCoupon(typeCode, denom)) {
                validActions.add(i);
            }
        }

        if (validActions.isEmpty()) {
            log.debug("All actions are duplicates for user {}, using random", userProfile.getUserId());
            return (int) (Math.random() * totalActions);
        }

        return validActions.get((int) (Math.random() * validActions.size()));
    }

    public int selectGreedyAction(UserProfile userProfile, boolean avoidDuplicates) {
        double[] stateVector = userProfile.toStateVector();
        INDArray state = Nd4j.create(stateVector, new int[]{1, stateVector.length});

        if (!avoidDuplicates) {
            return dqnNetwork.selectGreedyAction(state);
        }

        INDArray qValues = dqnNetwork.predictQValues(state);
        List<int[]> actionValuePairs = new ArrayList<>();

        for (int i = 0; i < qValues.length(); i++) {
            CouponAction action = CouponAction.fromIndex(i);
            int typeCode = action.getCouponType().getCode();
            int denom = action.getDenomination().intValue();

            if (!userProfile.hasRecentSimilarCoupon(typeCode, denom)) {
                actionValuePairs.add(new int[]{i, (int) (qValues.getDouble(i) * 1000000)});
            }
        }

        if (actionValuePairs.isEmpty()) {
            log.debug("All actions are duplicates for user {}, using greedy best", userProfile.getUserId());
            return dqnNetwork.selectGreedyAction(state);
        }

        actionValuePairs.sort(Comparator.comparingInt((int[] a) -> a[1]).reversed());
        return actionValuePairs.get(0)[0];
    }

    public CouponAction selectGreedyAction(UserProfile userProfile) {
        int actionIndex = selectGreedyAction(userProfile, avoidDuplicateCoupons);
        return CouponAction.fromIndex(actionIndex);
    }

    public void storeExperience(UserProfile currentProfile, int action, double reward,
                                UserProfile nextProfile, boolean done, String userId) {
        Experience experience = Experience.builder()
                .state(currentProfile.toStateVector())
                .action(action)
                .reward(reward)
                .nextState(nextProfile != null ? nextProfile.toStateVector() : currentProfile.toStateVector())
                .done(done)
                .timestamp(System.currentTimeMillis())
                .userId(userId)
                .build();

        replayBuffer.add(experience);
    }

    public void storeExperienceFromDistribution(CouponDistribution distribution,
                                                UserProfile currentProfile,
                                                UserProfile nextProfile) {
        double reward = rewardCalculator.calculateDelayedReward(distribution, currentProfile);

        if (distribution.getRlActionIndex() != null) {
            storeExperience(
                    currentProfile,
                    distribution.getRlActionIndex(),
                    reward,
                    nextProfile,
                    true,
                    distribution.getUserId()
            );

            distribution.setRlReward(reward);
            log.debug("Stored experience for user {} with reward {}",
                    distribution.getUserId(), reward);
        }
    }

    public boolean train() {
        if (!rlConfig.isTrainEnabled()) {
            return false;
        }

        if (!replayBuffer.isReady(rlConfig.getBatchSize())) {
            log.debug("Replay buffer not ready: size={}, required={}",
                    replayBuffer.size(), rlConfig.getBatchSize());
            return false;
        }

        try {
            List<Experience> batch = replayBuffer.samplePriority(rlConfig.getBatchSize());

            int batchSize = batch.size();
            int stateDim = rlConfig.getStateDim();
            int actionDim = rlConfig.getActionDim();

            INDArray states = Nd4j.create(batchSize, stateDim);
            INDArray nextStates = Nd4j.create(batchSize, stateDim);
            int[] actions = new int[batchSize];
            double[] rewards = new double[batchSize];
            boolean[] dones = new boolean[batchSize];

            for (int i = 0; i < batchSize; i++) {
                Experience exp = batch.get(i);
                states.putRow(i, Nd4j.create(exp.getState()));
                nextStates.putRow(i, Nd4j.create(exp.getNextState()));
                actions[i] = exp.getAction();
                rewards[i] = exp.getReward();
                dones[i] = exp.isDone();
            }

            INDArray currentQ = dqnNetwork.predictQValues(states);
            INDArray nextQ = dqnNetwork.predictTargetQValues(nextStates);

            INDArray maxNextQ = nextQ.max(1);

            INDArray targets = currentQ.dup();

            for (int i = 0; i < batchSize; i++) {
                double target = rewards[i];
                if (!dones[i]) {
                    target += rlConfig.getGamma() * maxNextQ.getDouble(i);
                }
                targets.putScalar(i, actions[i], target);
            }

            dqnNetwork.fit(states, targets);

            int step = trainStepCounter.incrementAndGet();
            if (step % rlConfig.getTargetUpdateFrequency() == 0) {
                dqnNetwork.updateTargetNetwork();
                log.info("Target network updated at step {}", step);
            }

            updateEpsilon();

            if (step % 100 == 0) {
                double loss = dqnNetwork.computeLoss(states, targets);
                log.info("Training step {}, loss={:.4f}, epsilon={:.4f}, buffer={}",
                        step, loss, epsilon, replayBuffer.size());
            }

            return true;
        } catch (Exception e) {
            log.error("Training failed", e);
            return false;
        }
    }

    private void updateEpsilon() {
        if (epsilon > rlConfig.getEpsilonEnd()) {
            epsilon *= rlConfig.getEpsilonDecay();
            if (epsilon < rlConfig.getEpsilonEnd()) {
                epsilon = rlConfig.getEpsilonEnd();
            }
        }
    }

    @Scheduled(fixedDelay = 5000)
    public void scheduledTrain() {
        if (rlConfig.isTrainEnabled()) {
            train();
        }
    }

    @Scheduled(cron = "0 0 * * * *")
    public void scheduledSaveModel() {
        if (trainStepCounter.get() > 0) {
            dqnNetwork.saveModel();
            log.info("Model saved automatically at {}", LocalDateTime.now());
        }
    }

    public void saveModel() {
        dqnNetwork.saveModel();
    }

    public void loadModel() {
        dqnNetwork.loadModel();
        dqnNetwork.updateTargetNetwork();
    }

    public int getTrainStepCount() {
        return trainStepCounter.get();
    }

    public int getReplayBufferSize() {
        return replayBuffer.size();
    }
}
