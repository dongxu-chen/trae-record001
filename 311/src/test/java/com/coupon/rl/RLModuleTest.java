package com.coupon.rl;

import com.coupon.model.UserProfile;
import com.coupon.rl.agent.DQNAgent;
import com.coupon.rl.buffer.ReplayBuffer;
import com.coupon.rl.config.RLConfig;
import com.coupon.rl.model.CouponAction;
import com.coupon.rl.model.Experience;
import com.coupon.rl.reward.RewardCalculator;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class RLModuleTest {

    private RLConfig rlConfig;
    private ReplayBuffer replayBuffer;
    private RewardCalculator rewardCalculator;

    @BeforeEach
    void setUp() {
        rlConfig = new RLConfig();
        rlConfig.setStateDim(8);
        rlConfig.setActionDim(12);
        rlConfig.setBatchSize(10);
        rlConfig.setGamma(0.99);

        replayBuffer = new ReplayBuffer(1000);
        rewardCalculator = new RewardCalculator();
    }

    @Test
    void testUserProfileStateVector() {
        UserProfile profile = createTestUserProfile("user001");
        double[] state = profile.toStateVector();

        assertEquals(8, state.length);
        for (double v : state) {
            assertTrue(v >= 0 && v <= 1, "State value should be normalized between 0 and 1");
        }
    }

    @Test
    void testCouponActionFromIndex() {
        int totalActions = CouponAction.getTotalActions();
        assertEquals(20, totalActions);

        for (int i = 0; i < totalActions; i++) {
            CouponAction action = CouponAction.fromIndex(i);
            assertNotNull(action);
            assertEquals(i, action.getActionIndex());
            assertNotNull(action.getCouponType());
            assertNotNull(action.getDenomination());
            assertTrue(action.getDenomination().compareTo(java.math.BigDecimal.ZERO) > 0);
        }

        CouponAction action0 = CouponAction.fromIndex(0);
        assertEquals(1, action0.getCouponType().getCode());
        assertEquals(new java.math.BigDecimal("5"), action0.getDenomination());
    }

    @Test
    void testReplayBuffer() {
        assertEquals(0, replayBuffer.size());
        assertFalse(replayBuffer.isReady(10));

        for (int i = 0; i < 15; i++) {
            Experience exp = createTestExperience(i);
            replayBuffer.add(exp);
        }

        assertEquals(15, replayBuffer.size());
        assertTrue(replayBuffer.isReady(10));

        List<Experience> sample = replayBuffer.sample(10);
        assertEquals(10, sample.size());

        for (int i = 0; i < 1000; i++) {
            replayBuffer.add(createTestExperience(100 + i));
        }
        assertEquals(1000, replayBuffer.size());
    }

    @Test
    void testReplayBufferPrioritySampling() {
        for (int i = 0; i < 50; i++) {
            Experience exp = createTestExperience(i);
            exp.setReward(i % 10 == 0 ? 10.0 : 0.1);
            replayBuffer.add(exp);
        }

        List<Experience> sample = replayBuffer.samplePriority(20);
        assertEquals(20, sample.size());

        long highRewardCount = sample.stream()
                .filter(e -> e.getReward() > 5.0)
                .count();
        assertTrue(highRewardCount > 0, "Priority sampling should include some high-reward experiences");
    }

    @Test
    void testRewardCalculator() {
        UserProfile profile = createTestUserProfile("user001");
        com.coupon.model.CouponDistribution usedDistribution =
                createTestDistribution("dist001", com.coupon.model.enums.CouponStatus.USED);

        usedDistribution.setOrderAmount(new java.math.BigDecimal("100"));
        usedDistribution.setDiscountAmount(new java.math.BigDecimal("10"));

        double reward = rewardCalculator.calculateReward(usedDistribution, profile);
        assertTrue(reward > 0, "Used coupon should give positive reward");

        com.coupon.model.CouponDistribution expiredDistribution =
                createTestDistribution("dist002", com.coupon.model.enums.CouponStatus.EXPIRED);
        double expiredReward = rewardCalculator.calculateReward(expiredDistribution, profile);
        assertEquals(-1.0, expiredReward, 0.001, "Expired coupon should give negative reward");

        com.coupon.model.CouponDistribution revokedDistribution =
                createTestDistribution("dist003", com.coupon.model.enums.CouponStatus.REVOKED);
        double revokedReward = rewardCalculator.calculateReward(revokedDistribution, profile);
        assertEquals(-0.5, revokedReward, 0.001, "Revoked coupon should give negative reward");
    }

    @Test
    void testStateNormalization() {
        UserProfile extremeProfile = UserProfile.builder()
                .userId("extreme")
                .consumptionFrequency(100)
                .avgOrderValue(10000)
                .activityScore(200)
                .orderCount30d(100)
                .daysSinceLastOrder(365)
                .couponUsageRate(2.0)
                .avgDiscountSensitivity(-0.5)
                .isNewUser(true)
                .build();

        double[] state = extremeProfile.toStateVector();
        for (double v : state) {
            assertTrue(v >= 0 && v <= 1, "Extreme values should be clipped to [0, 1]");
        }

        assertEquals(1.0, state[7], 0.001, "New user flag should be 1.0");
    }

    private UserProfile createTestUserProfile(String userId) {
        return UserProfile.builder()
                .userId(userId)
                .consumptionFrequency(5.5)
                .avgOrderValue(150.0)
                .activityScore(75.0)
                .totalSpend(1500.0)
                .orderCount30d(10)
                .daysSinceLastOrder(3)
                .couponUsageRate(0.7)
                .avgDiscountSensitivity(0.6)
                .isNewUser(false)
                .userLevel(2)
                .registerTime(LocalDateTime.now().minusMonths(6))
                .lastActiveTime(LocalDateTime.now().minusDays(1))
                .updateTime(LocalDateTime.now())
                .build();
    }

    private Experience createTestExperience(int id) {
        double[] state = new double[8];
        double[] nextState = new double[8];
        for (int i = 0; i < 8; i++) {
            state[i] = Math.random();
            nextState[i] = Math.random();
        }

        return Experience.builder()
                .state(state)
                .action(id % 12)
                .reward(Math.random() * 2 - 1)
                .nextState(nextState)
                .done(Math.random() > 0.7)
                .timestamp(System.currentTimeMillis())
                .userId("user" + id)
                .build();
    }

    private com.coupon.model.CouponDistribution createTestDistribution(String distId,
                                                                       com.coupon.model.enums.CouponStatus status) {
        return com.coupon.model.CouponDistribution.builder()
                .distributionId(distId)
                .userId("user001")
                .couponId("CPN_TEST_001")
                .couponCode("TESTCODE001")
                .denomination(new java.math.BigDecimal("10"))
                .couponType(1)
                .sceneCode(2)
                .minOrderAmount(new java.math.BigDecimal("30"))
                .status(status)
                .experimentId("default_coupon_exp")
                .groupId("rl_group")
                .issueTime(LocalDateTime.now())
                .expireTime(LocalDateTime.now().plusDays(7))
                .rlActionIndex(0)
                .build();
    }
}
