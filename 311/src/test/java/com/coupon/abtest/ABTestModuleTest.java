package com.coupon.abtest;

import com.coupon.abtest.config.ABTestConfig;
import com.coupon.abtest.splitter.TrafficSplitter;
import com.coupon.model.ExperimentConfig;
import com.coupon.model.enums.SceneType;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class ABTestModuleTest {

    private TrafficSplitter trafficSplitter;
    private ABTestConfig abTestConfig;

    @BeforeEach
    void setUp() {
        abTestConfig = new ABTestConfig();
        abTestConfig.setDefaultExperiment("default_coupon_exp");
        abTestConfig.setTrafficSalt("test_salt_2024");
        trafficSplitter = new TrafficSplitter(abTestConfig);
    }

    @Test
    void testTrafficSplitConsistency() {
        ExperimentConfig experiment = createTestExperiment();

        Map<String, String> userGroupMap = new HashMap<>();
        for (int i = 0; i < 100; i++) {
            String userId = "user_" + i;
            String group = trafficSplitter.assignGroup(userId, experiment);
            userGroupMap.put(userId, group);
        }

        for (int i = 0; i < 100; i++) {
            String userId = "user_" + i;
            String group1 = userGroupMap.get(userId);
            String group2 = trafficSplitter.assignGroup(userId, experiment);
            assertEquals(group1, group2, "Traffic split should be consistent for same user");
        }
    }

    @Test
    void testTrafficDistribution() {
        ExperimentConfig experiment = createTestExperiment();

        int controlCount = 0;
        int rlGroupCount = 0;
        int noGroupCount = 0;
        int totalUsers = 10000;

        for (int i = 0; i < totalUsers; i++) {
            String userId = "user_" + i;
            String group = trafficSplitter.assignGroup(userId, experiment);
            if ("control".equals(group)) {
                controlCount++;
            } else if ("rl_group".equals(group)) {
                rlGroupCount++;
            } else {
                noGroupCount++;
            }
        }

        double controlPercent = controlCount * 100.0 / totalUsers;
        double rlGroupPercent = rlGroupCount * 100.0 / totalUsers;

        assertTrue(Math.abs(controlPercent - 30) < 2,
                "Control group should be ~30%, actual: " + controlPercent);
        assertTrue(Math.abs(rlGroupPercent - 70) < 2,
                "RL group should be ~70%, actual: " + rlGroupPercent);
    }

    @Test
    void testTrafficSplitWithZeroPercent() {
        ExperimentConfig exp = ExperimentConfig.builder()
                .experimentId("test_exp")
                .experimentName("Test Exp")
                .sceneType(SceneType.REPURCHASE)
                .status(1)
                .totalTrafficPercent(0)
                .startTime(LocalDateTime.now().minusDays(1))
                .endTime(LocalDateTime.now().plusDays(1))
                .groups(Arrays.asList(
                        ExperimentConfig.ExperimentGroup.builder()
                                .groupId("control")
                                .trafficPercent(50)
                                .isRlEnabled(false)
                                .build(),
                        ExperimentConfig.ExperimentGroup.builder()
                                .groupId("rl_group")
                                .trafficPercent(50)
                                .isRlEnabled(true)
                                .build()
                ))
                .build();

        for (int i = 0; i < 100; i++) {
            assertNull(trafficSplitter.assignGroup("user_" + i, exp),
                    "Should return null when total traffic is 0%");
        }
    }

    @Test
    void testInactiveExperiment() {
        ExperimentConfig exp = ExperimentConfig.builder()
                .experimentId("inactive_exp")
                .status(0)
                .startTime(LocalDateTime.now().minusDays(10))
                .endTime(LocalDateTime.now().minusDays(1))
                .build();

        assertNull(trafficSplitter.assignGroup("user001", exp),
                "Should return null for inactive experiment");
    }

    @Test
    void testIsInGroup() {
        ExperimentConfig experiment = createTestExperiment();

        String userIdInControl = findUserInGroup(experiment, "control");
        assertNotNull(userIdInControl, "Should find user in control group");
        assertTrue(trafficSplitter.isInGroup(userIdInControl, experiment, "control"));
        assertFalse(trafficSplitter.isInGroup(userIdInControl, experiment, "rl_group"));
    }

    @Test
    void testGetGroup() {
        ExperimentConfig experiment = createTestExperiment();

        ExperimentConfig.ExperimentGroup controlGroup =
                trafficSplitter.getGroup(experiment, "control");
        assertNotNull(controlGroup);
        assertEquals("control", controlGroup.getGroupId());
        assertFalse(controlGroup.getIsRlEnabled());

        ExperimentConfig.ExperimentGroup rlGroup =
                trafficSplitter.getGroup(experiment, "rl_group");
        assertNotNull(rlGroup);
        assertEquals("rl_group", rlGroup.getGroupId());
        assertTrue(rlGroup.getIsRlEnabled());

        assertNull(trafficSplitter.getGroup(experiment, "non_existent"));
    }

    @Test
    void testExperimentIsActive() {
        ExperimentConfig activeExp = ExperimentConfig.builder()
                .experimentId("active")
                .status(1)
                .startTime(LocalDateTime.now().minusDays(1))
                .endTime(LocalDateTime.now().plusDays(1))
                .build();
        assertTrue(activeExp.isActive());

        ExperimentConfig inactiveExp = ExperimentConfig.builder()
                .experimentId("inactive")
                .status(0)
                .startTime(LocalDateTime.now().minusDays(1))
                .endTime(LocalDateTime.now().plusDays(1))
                .build();
        assertFalse(inactiveExp.isActive());

        ExperimentConfig expiredExp = ExperimentConfig.builder()
                .experimentId("expired")
                .status(1)
                .startTime(LocalDateTime.now().minusDays(10))
                .endTime(LocalDateTime.now().minusDays(1))
                .build();
        assertFalse(expiredExp.isActive());
    }

    private ExperimentConfig createTestExperiment() {
        return ExperimentConfig.builder()
                .experimentId("test_exp")
                .experimentName("Test Experiment")
                .description("Test AB experiment")
                .sceneType(SceneType.REPURCHASE)
                .status(1)
                .totalTrafficPercent(100)
                .startTime(LocalDateTime.now().minusDays(1))
                .endTime(LocalDateTime.now().plusDays(1))
                .groups(Arrays.asList(
                        ExperimentConfig.ExperimentGroup.builder()
                                .groupId("control")
                                .groupName("对照组")
                                .groupType("control")
                                .trafficPercent(30)
                                .isRlEnabled(false)
                                .fixedDenomination(new BigDecimal("10"))
                                .fixedCouponType(1)
                                .minOrderAmount(new BigDecimal("30"))
                                .build(),
                        ExperimentConfig.ExperimentGroup.builder()
                                .groupId("rl_group")
                                .groupName("RL实验组")
                                .groupType("experimental")
                                .trafficPercent(70)
                                .isRlEnabled(true)
                                .build()
                ))
                .build();
    }

    private String findUserInGroup(ExperimentConfig experiment, String targetGroup) {
        for (int i = 0; i < 1000; i++) {
            String userId = "user_" + i;
            String group = trafficSplitter.assignGroup(userId, experiment);
            if (targetGroup.equals(group)) {
                return userId;
            }
        }
        return null;
    }
}
