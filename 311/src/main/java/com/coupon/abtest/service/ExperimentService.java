package com.coupon.abtest.service;

import com.alibaba.fastjson2.JSON;
import com.coupon.abtest.config.ABTestConfig;
import com.coupon.abtest.splitter.TrafficSplitter;
import com.coupon.model.ExperimentConfig;
import com.coupon.model.enums.SceneType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class ExperimentService {

    private static final String EXPERIMENT_KEY_PREFIX = "abtest:experiment:";
    private static final String DEFAULT_EXPERIMENT_ID = "default_coupon_exp";

    private final ABTestConfig abTestConfig;
    private final TrafficSplitter trafficSplitter;
    private final StringRedisTemplate redisTemplate;

    private final Map<String, ExperimentConfig> experimentCache = new ConcurrentHashMap<>();

    public ExperimentService(ABTestConfig abTestConfig, TrafficSplitter trafficSplitter,
                             StringRedisTemplate redisTemplate) {
        this.abTestConfig = abTestConfig;
        this.trafficSplitter = trafficSplitter;
        this.redisTemplate = redisTemplate;
    }

    @PostConstruct
    public void init() {
        createDefaultExperiments();
        loadExperiments();
        log.info("Experiment service initialized with {} experiments", experimentCache.size());
    }

    public ExperimentConfig createExperiment(ExperimentConfig config) {
        String key = getExperimentKey(config.getExperimentId());
        try {
            config.setCreateTime(LocalDateTime.now());
            config.setUpdateTime(LocalDateTime.now());
            String json = JSON.toJSONString(config);
            redisTemplate.opsForValue().set(key, json, 30, TimeUnit.DAYS);
            experimentCache.put(config.getExperimentId(), config);
            log.info("Created experiment: {}", config.getExperimentId());
            return config;
        } catch (Exception e) {
            log.error("Failed to create experiment: {}", config.getExperimentId(), e);
            return null;
        }
    }

    public ExperimentConfig getExperiment(String experimentId) {
        if (experimentCache.containsKey(experimentId)) {
            return experimentCache.get(experimentId);
        }

        String key = getExperimentKey(experimentId);
        try {
            String json = redisTemplate.opsForValue().get(key);
            if (json != null) {
                ExperimentConfig config = JSON.parseObject(json, ExperimentConfig.class);
                experimentCache.put(experimentId, config);
                return config;
            }
        } catch (Exception e) {
            log.error("Failed to get experiment: {}", experimentId, e);
        }
        return null;
    }

    public ExperimentConfig getExperimentByScene(SceneType sceneType) {
        return experimentCache.values().stream()
                .filter(e -> e.getSceneType() == sceneType && e.isActive())
                .findFirst()
                .orElseGet(() -> experimentCache.get(DEFAULT_EXPERIMENT_ID));
    }

    public List<ExperimentConfig> getAllExperiments() {
        return new ArrayList<>(experimentCache.values());
    }

    public void loadExperiments() {
        try {
            Set<String> keys = redisTemplate.keys(EXPERIMENT_KEY_PREFIX + "*");
            if (keys != null) {
                for (String key : keys) {
                    String json = redisTemplate.opsForValue().get(key);
                    if (json != null) {
                        try {
                            ExperimentConfig config = JSON.parseObject(json, ExperimentConfig.class);
                            experimentCache.put(config.getExperimentId(), config);
                        } catch (Exception e) {
                            log.warn("Failed to parse experiment from key: {}", key, e);
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.error("Failed to load experiments", e);
        }
    }

    public String assignUserToGroup(String userId, SceneType sceneType) {
        ExperimentConfig experiment = getExperimentByScene(sceneType);
        if (experiment == null) {
            return null;
        }
        return trafficSplitter.assignGroup(userId, experiment);
    }

    public ExperimentConfig.ExperimentGroup getExperimentGroup(String userId, SceneType sceneType) {
        ExperimentConfig experiment = getExperimentByScene(sceneType);
        if (experiment == null) {
            return null;
        }
        String groupId = trafficSplitter.assignGroup(userId, experiment);
        if (groupId == null) {
            return null;
        }
        return trafficSplitter.getGroup(experiment, groupId);
    }

    public boolean isRlEnabledForUser(String userId, SceneType sceneType) {
        ExperimentConfig.ExperimentGroup group = getExperimentGroup(userId, sceneType);
        return group != null && Boolean.TRUE.equals(group.getIsRlEnabled());
    }

    public void updateExperiment(ExperimentConfig config) {
        config.setUpdateTime(LocalDateTime.now());
        createExperiment(config);
    }

    public void deleteExperiment(String experimentId) {
        String key = getExperimentKey(experimentId);
        try {
            redisTemplate.delete(key);
            experimentCache.remove(experimentId);
            log.info("Deleted experiment: {}", experimentId);
        } catch (Exception e) {
            log.error("Failed to delete experiment: {}", experimentId, e);
        }
    }

    private void createDefaultExperiments() {
        if (getExperiment(DEFAULT_EXPERIMENT_ID) == null) {
            ExperimentConfig defaultExp = ExperimentConfig.builder()
                    .experimentId(DEFAULT_EXPERIMENT_ID)
                    .experimentName("默认优惠券实验")
                    .description("默认的优惠券发放AB实验，包含对照组和RL实验组")
                    .sceneType(SceneType.REPURCHASE)
                    .status(1)
                    .totalTrafficPercent(100)
                    .startTime(LocalDateTime.now().minusYears(1))
                    .endTime(LocalDateTime.now().plusYears(1))
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
            createExperiment(defaultExp);

            createSceneExperiment(SceneType.NEW_USER, "new_user_exp", "新人优惠券实验", 100);
            createSceneExperiment(SceneType.WAKE_UP, "wake_up_exp", "唤醒优惠券实验", 100);
        }
    }

    private void createSceneExperiment(SceneType sceneType, String expId, String name, int trafficPercent) {
        if (getExperiment(expId) == null) {
            ExperimentConfig exp = ExperimentConfig.builder()
                    .experimentId(expId)
                    .experimentName(name)
                    .description(name + " - 包含对照组和RL实验组")
                    .sceneType(sceneType)
                    .status(1)
                    .totalTrafficPercent(trafficPercent)
                    .startTime(LocalDateTime.now().minusYears(1))
                    .endTime(LocalDateTime.now().plusYears(1))
                    .groups(Arrays.asList(
                            ExperimentConfig.ExperimentGroup.builder()
                                    .groupId("control")
                                    .groupName("对照组")
                                    .groupType("control")
                                    .trafficPercent(30)
                                    .isRlEnabled(false)
                                    .fixedDenomination(sceneType == SceneType.NEW_USER ? new BigDecimal("20") : new BigDecimal("15"))
                                    .fixedCouponType(sceneType == SceneType.NEW_USER ? 4 : 1)
                                    .minOrderAmount(new BigDecimal("50"))
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
            createExperiment(exp);
        }
    }

    private String getExperimentKey(String experimentId) {
        return EXPERIMENT_KEY_PREFIX + experimentId;
    }

    public void refreshCache() {
        experimentCache.clear();
        loadExperiments();
        log.info("Experiment cache refreshed");
    }
}
