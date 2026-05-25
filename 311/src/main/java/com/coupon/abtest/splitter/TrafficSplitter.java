package com.coupon.abtest.splitter;

import com.alibaba.fastjson2.JSON;
import com.coupon.abtest.config.ABTestConfig;
import com.coupon.model.ExperimentConfig;
import com.coupon.model.UserProfile;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.io.Serializable;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
public class TrafficSplitter {

    private static final String BALANCE_CHECK_KEY = "abtest:balance:";
    private static final String STRATUM_KEY_PREFIX = "abtest:stratum:";
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd");

    private final ABTestConfig abTestConfig;
    private final StringRedisTemplate redisTemplate;

    private final Map<String, StratumBalanceStats> balanceStatsCache = new ConcurrentHashMap<>();

    public TrafficSplitter(ABTestConfig abTestConfig, StringRedisTemplate redisTemplate) {
        this.abTestConfig = abTestConfig;
        this.redisTemplate = redisTemplate;
    }

    public String assignGroup(String userId, ExperimentConfig experiment) {
        return assignGroup(userId, null, experiment);
    }

    public String assignGroup(String userId, UserProfile profile, ExperimentConfig experiment) {
        if (experiment == null || !experiment.isActive()) {
            log.debug("Experiment not active, returning null for user: {}", userId);
            return null;
        }

        List<ExperimentConfig.ExperimentGroup> groups = experiment.getGroups();
        if (groups == null || groups.isEmpty()) {
            return null;
        }

        String stratumId = calculateStratumId(profile);
        String hashKey = abTestConfig.getTrafficSalt() + ":" + experiment.getExperimentId()
                + ":" + stratumId + ":" + userId;

        int hash = computeHash(hashKey);
        int totalPercent = experiment.getTotalTrafficPercent();

        if (totalPercent <= 0) {
            return null;
        }

        int position = hash % 100;

        if (position >= totalPercent) {
            log.debug("User {} not in experiment traffic ({}%)", userId, totalPercent);
            return null;
        }

        int cumulativePercent = 0;
        for (ExperimentConfig.ExperimentGroup group : groups) {
            cumulativePercent += group.getTrafficPercent();
            if (position < cumulativePercent) {
                log.debug("User {} assigned to group {} in experiment {}, stratum={}",
                        userId, group.getGroupId(), experiment.getExperimentId(), stratumId);

                recordGroupAssignment(experiment.getExperimentId(), group.getGroupId(), stratumId, profile);
                return group.getGroupId();
            }
        }

        return null;
    }

    public ExperimentConfig.ExperimentGroup getGroup(ExperimentConfig experiment, String groupId) {
        if (experiment == null || experiment.getGroups() == null) {
            return null;
        }

        return experiment.getGroups().stream()
                .filter(g -> g.getGroupId().equals(groupId))
                .findFirst()
                .orElse(null);
    }

    public boolean isInGroup(String userId, ExperimentConfig experiment, String groupId) {
        String assignedGroup = assignGroup(userId, experiment);
        return groupId.equals(assignedGroup);
    }

    public String calculateStratumId(UserProfile profile) {
        if (profile == null) {
            return "default";
        }

        int userLevelStratum = calculateUserLevelStratum(profile.getUserLevel());
        int activityStratum = calculateActivityStratum(profile.getActivityScore());
        int consumptionStratum = calculateConsumptionStratum(profile.getAvgOrderValue());
        int newUserStratum = profile.isNewUser() ? 0 : 1;

        return String.format("L%d_A%d_C%d_N%d",
                userLevelStratum, activityStratum, consumptionStratum, newUserStratum);
    }

    private int calculateUserLevelStratum(int userLevel) {
        if (userLevel <= 1) return 0;
        if (userLevel <= 3) return 1;
        return 2;
    }

    private int calculateActivityStratum(double activityScore) {
        if (activityScore < 30) return 0;
        if (activityScore < 70) return 1;
        return 2;
    }

    private int calculateConsumptionStratum(double avgOrderValue) {
        if (avgOrderValue < 50) return 0;
        if (avgOrderValue < 200) return 1;
        return 2;
    }

    private void recordGroupAssignment(String experimentId, String groupId,
                                       String stratumId, UserProfile profile) {
        String date = LocalDate.now().format(DATE_FORMATTER);
        String balanceKey = BALANCE_CHECK_KEY + experimentId + ":" + date;
        String stratumKey = STRATUM_KEY_PREFIX + experimentId + ":" + stratumId;

        try {
            String groupCountKey = groupId + ":count";
            redisTemplate.opsForHash().increment(balanceKey, groupCountKey, 1);
            redisTemplate.opsForHash().increment(balanceKey, stratumId + ":" + groupId + ":count", 1);

            if (profile != null) {
                double[] features = {
                        profile.getConsumptionFrequency(),
                        profile.getAvgOrderValue(),
                        profile.getActivityScore(),
                        profile.isNewUser() ? 1.0 : 0.0
                };
                String featureSumKey = groupId + ":features";
                String currentSumStr = (String) redisTemplate.opsForHash().get(balanceKey, featureSumKey);
                double[] currentSum = currentSumStr != null
                        ? JSON.parseObject(currentSumStr, double[].class)
                        : new double[4];

                for (int i = 0; i < features.length; i++) {
                    currentSum[i] += features[i];
                }
                redisTemplate.opsForHash().put(balanceKey, featureSumKey, JSON.toJSONString(currentSum));
            }

            redisTemplate.expire(balanceKey, 7, TimeUnit.DAYS);
            redisTemplate.opsForValue().increment(stratumKey);
            redisTemplate.expire(stratumKey, 30, TimeUnit.DAYS);

            updateBalanceStats(experimentId, groupId, stratumId);

        } catch (Exception e) {
            log.error("Failed to record group assignment", e);
        }
    }

    private void updateBalanceStats(String experimentId, String groupId, String stratumId) {
        String key = experimentId;
        StratumBalanceStats stats = balanceStatsCache.computeIfAbsent(key, k -> new StratumBalanceStats());
        stats.getGroupCounts().merge(groupId, 1L, Long::sum);
        stats.getStratumCounts().merge(stratumId, 1L, Long::sum);
        stats.setLastUpdateTime(System.currentTimeMillis());
    }

    public BalanceCheckResult checkBalance(String experimentId) {
        String date = LocalDate.now().format(DATE_FORMATTER);
        String balanceKey = BALANCE_CHECK_KEY + experimentId + ":" + date;
        BalanceCheckResult result = new BalanceCheckResult();
        result.setExperimentId(experimentId);
        result.setCheckDate(date);

        try {
            Map<Object, Object> entries = redisTemplate.opsForHash().entries(balanceKey);
            Map<String, Long> groupCounts = new HashMap<>();
            Map<String, long[]> groupFeatureSums = new HashMap<>();
            Map<String, Long> stratumGroupCounts = new HashMap<>();

            for (Map.Entry<Object, Object> entry : entries.entrySet()) {
                String key = entry.getKey().toString();
                String value = entry.getValue().toString();

                if (key.endsWith(":count") && !key.contains(":")) {
                    String groupId = key.replace(":count", "");
                    groupCounts.put(groupId, Long.parseLong(value));
                } else if (key.contains(":") && key.endsWith(":count")) {
                    stratumGroupCounts.put(key, Long.parseLong(value));
                } else if (key.endsWith(":features")) {
                    String groupId = key.replace(":features", "");
                    groupFeatureSums.put(groupId, JSON.parseObject(value, long[].class));
                }
            }

            result.setGroupCounts(groupCounts);
            result.setStratumGroupCounts(stratumGroupCounts);

            long total = groupCounts.values().stream().mapToLong(Long::longValue).sum();
            if (total > 0) {
                Map<String, Double> groupRatios = new HashMap<>();
                for (Map.Entry<String, Long> entry : groupCounts.entrySet()) {
                    groupRatios.put(entry.getKey(), entry.getValue() * 100.0 / total);
                }
                result.setGroupRatios(groupRatios);

                double maxDiff = 0;
                Double firstRatio = null;
                for (Double ratio : groupRatios.values()) {
                    if (firstRatio == null) {
                        firstRatio = ratio;
                    } else {
                        maxDiff = Math.max(maxDiff, Math.abs(ratio - firstRatio));
                    }
                }
                result.setMaxGroupRatioDiff(maxDiff);
                result.setBalanced(maxDiff < 5.0);
            }

            if (groupFeatureSums.size() >= 2) {
                Map<String, double[]> featureMeans = new HashMap<>();
                for (Map.Entry<String, long[]> entry : groupFeatureSums.entrySet()) {
                    String groupId = entry.getKey();
                    long count = groupCounts.getOrDefault(groupId, 1L);
                    long[] sums = entry.getValue();
                    double[] means = new double[sums.length];
                    for (int i = 0; i < sums.length; i++) {
                        means[i] = (double) sums[i] / count;
                    }
                    featureMeans.put(groupId, means);
                }
                result.setFeatureMeans(featureMeans);

                List<String> groupIds = new ArrayList<>(featureMeans.keySet());
                if (groupIds.size() >= 2) {
                    double[] means1 = featureMeans.get(groupIds.get(0));
                    double[] means2 = featureMeans.get(groupIds.get(1));
                    double[] standardizedDiff = new double[means1.length];
                    for (int i = 0; i < means1.length; i++) {
                        double pooledStd = 1.0;
                        standardizedDiff[i] = Math.abs(means1[i] - means2[i]) / pooledStd;
                    }
                    result.setStandardizedFeatureDiff(standardizedDiff);

                    double maxStdDiff = 0;
                    for (double diff : standardizedDiff) {
                        maxStdDiff = Math.max(maxStdDiff, diff);
                    }
                    result.setMaxStandardizedDiff(maxStdDiff);
                    result.setFeatureBalanced(maxStdDiff < 0.1);
                }
            }

            result.setStratumStats(balanceStatsCache.get(experimentId));

            log.info("Balance check for experiment {}: balanced={}, maxRatioDiff={:.2f}%, maxStdDiff={:.3f}",
                    experimentId, result.isBalanced(), result.getMaxGroupRatioDiff(), result.getMaxStandardizedDiff());

        } catch (Exception e) {
            log.error("Failed to check balance for experiment: {}", experimentId, e);
        }

        return result;
    }

    public List<StratumInfo> getAllStrataInfo() {
        List<StratumInfo> strata = new ArrayList<>();
        for (int l = 0; l < 3; l++) {
            for (int a = 0; a < 3; a++) {
                for (int c = 0; c < 3; c++) {
                    for (int n = 0; n < 2; n++) {
                        StratumInfo info = new StratumInfo();
                        info.setStratumId(String.format("L%d_A%d_C%d_N%d", l, a, c, n));
                        info.setUserLevel(l == 0 ? "低等级" : l == 1 ? "中等级" : "高等级");
                        info.setActivity(a == 0 ? "低活跃" : a == 1 ? "中活跃" : "高活跃");
                        info.setConsumption(c == 0 ? "低消费" : c == 1 ? "中消费" : "高消费");
                        info.setNewUser(n == 0);
                        strata.add(info);
                    }
                }
            }
        }
        return strata;
    }

    private int computeHash(String key) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hashBytes = digest.digest(key.getBytes(StandardCharsets.UTF_8));

            int hash = 0;
            for (int i = 0; i < 4; i++) {
                hash = ((hash << 8) | (hashBytes[i] & 0xFF));
            }
            return Math.abs(hash);
        } catch (NoSuchAlgorithmException e) {
            log.warn("SHA-256 not available, using simple hashCode");
            return Math.abs(key.hashCode());
        }
    }

    @Data
    public static class BalanceCheckResult implements Serializable {
        private static final long serialVersionUID = 1L;
        private String experimentId;
        private String checkDate;
        private Map<String, Long> groupCounts;
        private Map<String, Double> groupRatios;
        private Map<String, Long> stratumGroupCounts;
        private Map<String, double[]> featureMeans;
        private double[] standardizedFeatureDiff;
        private double maxGroupRatioDiff;
        private double maxStandardizedDiff;
        private boolean balanced;
        private boolean featureBalanced;
        private StratumBalanceStats stratumStats;
    }

    @Data
    public static class StratumBalanceStats implements Serializable {
        private static final long serialVersionUID = 1L;
        private Map<String, Long> groupCounts = new ConcurrentHashMap<>();
        private Map<String, Long> stratumCounts = new ConcurrentHashMap<>();
        private long lastUpdateTime;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class StratumInfo implements Serializable {
        private static final long serialVersionUID = 1L;
        private String stratumId;
        private String userLevel;
        private String activity;
        private String consumption;
        private boolean newUser;
    }
}
