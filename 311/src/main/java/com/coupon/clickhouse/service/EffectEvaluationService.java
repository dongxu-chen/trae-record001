package com.coupon.clickhouse.service;

import com.alibaba.fastjson2.JSON;
import com.coupon.abtest.service.ABTestTrackingService;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class EffectEvaluationService {

    private final JdbcTemplate clickHouseJdbcTemplate;
    private final ABTestTrackingService trackingService;

    public EffectEvaluationService(@Qualifier("clickHouseJdbcTemplate") JdbcTemplate clickHouseJdbcTemplate,
                                   ABTestTrackingService trackingService) {
        this.clickHouseJdbcTemplate = clickHouseJdbcTemplate;
        this.trackingService = trackingService;
    }

    public CouponEffectStats getOverallStats(LocalDate startDate, LocalDate endDate) {
        String sql = """
            SELECT
                count() AS issue_count,
                countIf(status = 1) AS used_count,
                countIf(status = 2) AS expired_count,
                sum(denomination) AS total_denomination,
                sumIf(discount_amount, status = 1) AS total_discount,
                sumIf(order_amount, status = 1) AS total_order_amount,
                uniq(user_id) AS unique_users
            FROM coupon_distribution
            WHERE issue_time BETWEEN ? AND ?
            """;

        try {
            return clickHouseJdbcTemplate.queryForObject(sql, new CouponStatsRowMapper(),
                    toDateTime(startDate.atStartOfDay()),
                    toDateTime(endDate.atTime(23, 59, 59)));
        } catch (Exception e) {
            log.error("Failed to get overall stats", e);
            return null;
        }
    }

    public List<ExperimentGroupStats> getExperimentGroupStats(String experimentId,
                                                              LocalDate startDate,
                                                              LocalDate endDate) {
        String sql = """
            SELECT
                group_id,
                count() AS issue_count,
                countIf(status = 1) AS used_count,
                countIf(status = 2) AS expired_count,
                sum(denomination) AS total_denomination,
                sumIf(discount_amount, status = 1) AS total_discount,
                sumIf(order_amount, status = 1) AS total_order_amount,
                uniq(user_id) AS unique_users,
                countIf(status = 1) * 100.0 / if(count() = 0, 1, count()) AS usage_rate,
                if(sumIf(discount_amount, status = 1) = 0, 0,
                   (sumIf(order_amount, status = 1) - sumIf(discount_amount, status = 1)) / sumIf(discount_amount, status = 1)) AS roi
            FROM coupon_distribution
            WHERE experiment_id = ? AND issue_time BETWEEN ? AND ?
            GROUP BY group_id
            ORDER BY group_id
            """;

        try {
            return clickHouseJdbcTemplate.query(sql, new ExperimentGroupStatsRowMapper(),
                    experimentId,
                    toDateTime(startDate.atStartOfDay()),
                    toDateTime(endDate.atTime(23, 59, 59)));
        } catch (Exception e) {
            log.error("Failed to get experiment group stats for: {}", experimentId, e);
            return List.of();
        }
    }

    public List<DailyStats> getDailyStats(LocalDate startDate, LocalDate endDate,
                                          String experimentId, String groupId) {
        StringBuilder sql = new StringBuilder("""
            SELECT
                toDate(issue_time) AS stat_date,
                count() AS issue_count,
                countIf(status = 1) AS used_count,
                countIf(status = 2) AS expired_count,
                sum(denomination) AS total_denomination,
                sumIf(discount_amount, status = 1) AS total_discount,
                sumIf(order_amount, status = 1) AS total_order_amount,
                uniq(user_id) AS unique_users
            FROM coupon_distribution
            WHERE issue_time BETWEEN ? AND ?
            """);

        if (experimentId != null && !experimentId.isEmpty()) {
            sql.append(" AND experiment_id = '").append(experimentId).append("'");
        }
        if (groupId != null && !groupId.isEmpty()) {
            sql.append(" AND group_id = '").append(groupId).append("'");
        }

        sql.append(" GROUP BY stat_date ORDER BY stat_date");

        try {
            return clickHouseJdbcTemplate.query(sql.toString(), new DailyStatsRowMapper(),
                    toDateTime(startDate.atStartOfDay()),
                    toDateTime(endDate.atTime(23, 59, 59)));
        } catch (Exception e) {
            log.error("Failed to get daily stats", e);
            return List.of();
        }
    }

    public Map<Integer, ActionPerformance> getActionPerformanceStats(LocalDate startDate, LocalDate endDate) {
        String sql = """
            SELECT
                rl_action_index,
                count() AS issue_count,
                countIf(status = 1) AS used_count,
                sum(denomination) AS total_denomination,
                sumIf(discount_amount, status = 1) AS total_discount,
                sumIf(order_amount, status = 1) AS total_order_amount,
                countIf(status = 1) * 100.0 / if(count() = 0, 1, count()) AS usage_rate,
                if(sumIf(discount_amount, status = 1) = 0, 0,
                   (sumIf(order_amount, status = 1) - sumIf(discount_amount, status = 1)) / sumIf(discount_amount, status = 1)) AS roi,
                avg(rl_reward) AS avg_reward
            FROM coupon_distribution
            WHERE rl_action_index IS NOT NULL AND issue_time BETWEEN ? AND ?
            GROUP BY rl_action_index
            ORDER BY rl_action_index
            """;

        try {
            List<ActionPerformance> list = clickHouseJdbcTemplate.query(sql, new ActionPerformanceRowMapper(),
                    toDateTime(startDate.atStartOfDay()),
                    toDateTime(endDate.atTime(23, 59, 59)));

            Map<Integer, ActionPerformance> result = new HashMap<>();
            for (ActionPerformance ap : list) {
                if (ap.getActionIndex() != null) {
                    result.put(ap.getActionIndex(), ap);
                }
            }
            return result;
        } catch (Exception e) {
            log.error("Failed to get action performance stats", e);
            return new HashMap<>();
        }
    }

    public ExperimentComparison compareExperiments(String experimentId, LocalDate startDate, LocalDate endDate) {
        List<ExperimentGroupStats> stats = getExperimentGroupStats(experimentId, startDate, endDate);

        ExperimentComparison comparison = new ExperimentComparison();
        comparison.setExperimentId(experimentId);
        comparison.setStartDate(startDate);
        comparison.setEndDate(endDate);

        ExperimentGroupStats controlGroup = null;
        ExperimentGroupStats experimentalGroup = null;

        for (ExperimentGroupStats s : stats) {
            if ("control".equals(s.getGroupId())) {
                controlGroup = s;
            } else if ("rl_group".equals(s.getGroupId())) {
                experimentalGroup = s;
            }
        }

        comparison.setControlGroup(controlGroup);
        comparison.setExperimentalGroup(experimentalGroup);

        if (controlGroup != null && experimentalGroup != null) {
            comparison.setUsageRateLift(
                    experimentalGroup.getUsageRate() - controlGroup.getUsageRate()
            );
            comparison.setRoiLift(
                    experimentalGroup.getRoi() - controlGroup.getRoi()
            );

            if (controlGroup.getUsageRate() > 0) {
                comparison.setUsageRateLiftPercent(
                        (experimentalGroup.getUsageRate() - controlGroup.getUsageRate()) / controlGroup.getUsageRate() * 100
                );
            }
            if (controlGroup.getRoi() > 0) {
                comparison.setRoiLiftPercent(
                        (experimentalGroup.getRoi() - controlGroup.getRoi()) / controlGroup.getRoi() * 100
                );
            }
        }

        trackComparisonEvent(comparison);

        return comparison;
    }

    private void trackComparisonEvent(ExperimentComparison comparison) {
        Map<String, Object> properties = new HashMap<>();
        properties.put("control_usage_rate", comparison.getControlGroup() != null ? comparison.getControlGroup().getUsageRate() : null);
        properties.put("experimental_usage_rate", comparison.getExperimentalGroup() != null ? comparison.getExperimentalGroup().getUsageRate() : null);
        properties.put("usage_rate_lift", comparison.getUsageRateLift());
        properties.put("control_roi", comparison.getControlGroup() != null ? comparison.getControlGroup().getRoi() : null);
        properties.put("experimental_roi", comparison.getExperimentalGroup() != null ? comparison.getExperimentalGroup().getRoi() : null);
        properties.put("roi_lift", comparison.getRoiLift());

        trackingService.trackConversion(
                "system",
                comparison.getExperimentId(),
                "analysis",
                "experiment_comparison",
                properties
        );
    }

    private java.sql.Timestamp toDateTime(LocalDateTime dateTime) {
        return java.sql.Timestamp.valueOf(dateTime);
    }

    @Data
    public static class CouponEffectStats {
        protected long issueCount;
        protected long usedCount;
        protected long expiredCount;
        protected BigDecimal totalDenomination;
        protected BigDecimal totalDiscount;
        protected BigDecimal totalOrderAmount;
        protected long uniqueUsers;

        public double getUsageRate() {
            return issueCount > 0 ? usedCount * 100.0 / issueCount : 0;
        }

        public double getExpireRate() {
            return issueCount > 0 ? expiredCount * 100.0 / issueCount : 0;
        }

        public double getRoi() {
            if (totalDiscount == null || totalDiscount.doubleValue() <= 0) {
                return 0;
            }
            BigDecimal profit = totalOrderAmount.subtract(totalDiscount);
            return profit.divide(totalDiscount, 4, RoundingMode.HALF_UP).doubleValue();
        }

        public BigDecimal getAvgOrderValue() {
            if (usedCount <= 0) {
                return BigDecimal.ZERO;
            }
            return totalOrderAmount.divide(BigDecimal.valueOf(usedCount), 2, RoundingMode.HALF_UP);
        }
    }

    @Data
    public static class ExperimentGroupStats extends CouponEffectStats {
        private String groupId;
        private double usageRate;
        private double roi;
    }

    @Data
    public static class DailyStats extends CouponEffectStats {
        private LocalDate statDate;
    }

    @Data
    public static class ActionPerformance {
        private Integer actionIndex;
        private long issueCount;
        private long usedCount;
        private BigDecimal totalDenomination;
        private BigDecimal totalDiscount;
        private BigDecimal totalOrderAmount;
        private double usageRate;
        private double roi;
        private double avgReward;
    }

    @Data
    @Builder
    public static class ExperimentComparison {
        private String experimentId;
        private LocalDate startDate;
        private LocalDate endDate;
        private ExperimentGroupStats controlGroup;
        private ExperimentGroupStats experimentalGroup;
        private double usageRateLift;
        private double roiLift;
        private double usageRateLiftPercent;
        private double roiLiftPercent;

        public ExperimentComparison() {}
    }

    private static class CouponStatsRowMapper implements RowMapper<CouponEffectStats> {
        @Override
        public CouponEffectStats mapRow(ResultSet rs, int rowNum) throws SQLException {
            CouponEffectStats stats = new CouponEffectStats();
            mapCommonStats(rs, stats);
            return stats;
        }
    }

    private static class ExperimentGroupStatsRowMapper implements RowMapper<ExperimentGroupStats> {
        @Override
        public ExperimentGroupStats mapRow(ResultSet rs, int rowNum) throws SQLException {
            ExperimentGroupStats stats = new ExperimentGroupStats();
            mapCommonStats(rs, stats);
            stats.setGroupId(rs.getString("group_id"));
            stats.setUsageRate(rs.getDouble("usage_rate"));
            stats.setRoi(rs.getDouble("roi"));
            return stats;
        }
    }

    private static class DailyStatsRowMapper implements RowMapper<DailyStats> {
        @Override
        public DailyStats mapRow(ResultSet rs, int rowNum) throws SQLException {
            DailyStats stats = new DailyStats();
            mapCommonStats(rs, stats);
            stats.setStatDate(rs.getDate("stat_date").toLocalDate());
            return stats;
        }
    }

    private static class ActionPerformanceRowMapper implements RowMapper<ActionPerformance> {
        @Override
        public ActionPerformance mapRow(ResultSet rs, int rowNum) throws SQLException {
            ActionPerformance stats = new ActionPerformance();
            stats.setActionIndex((Integer) rs.getObject("rl_action_index"));
            stats.setIssueCount(rs.getLong("issue_count"));
            stats.setUsedCount(rs.getLong("used_count"));
            stats.setTotalDenomination(rs.getBigDecimal("total_denomination"));
            stats.setTotalDiscount(rs.getBigDecimal("total_discount"));
            stats.setTotalOrderAmount(rs.getBigDecimal("total_order_amount"));
            stats.setUsageRate(rs.getDouble("usage_rate"));
            stats.setRoi(rs.getDouble("roi"));
            stats.setAvgReward(rs.getDouble("avg_reward"));
            return stats;
        }
    }

    private static void mapCommonStats(ResultSet rs, CouponEffectStats stats) throws SQLException {
        stats.setIssueCount(rs.getLong("issue_count"));
        stats.setUsedCount(rs.getLong("used_count"));
        stats.setExpiredCount(rs.getLong("expired_count"));
        stats.setTotalDenomination(rs.getBigDecimal("total_denomination"));
        stats.setTotalDiscount(rs.getBigDecimal("total_discount"));
        stats.setTotalOrderAmount(rs.getBigDecimal("total_order_amount"));
        stats.setUniqueUsers(rs.getLong("unique_users"));
    }
}
