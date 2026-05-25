package com.coupon.clickhouse.repository;

import com.coupon.model.CouponDistribution;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.BatchPreparedStatementSetter;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.util.List;

@Slf4j
@Repository
public class CouponDistributionRepository {

    private final JdbcTemplate clickHouseJdbcTemplate;

    private static final String INSERT_SQL = """
        INSERT INTO coupon_distribution (
            distribution_id, user_id, coupon_id, coupon_code, denomination,
            coupon_type, scene_code, min_order_amount, status, experiment_id,
            group_id, rl_action_index, rl_reward, state_vector, issue_time,
            expire_time, use_time, order_id, order_amount, discount_amount,
            create_time, update_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now(), now())
        """;

    private static final String UPDATE_STATUS_SQL = """
        ALTER TABLE coupon_distribution UPDATE
            status = ?, use_time = ?, order_id = ?,
            order_amount = ?, discount_amount = ?, rl_reward = ?, update_time = now()
        WHERE distribution_id = ?
        """;

    public CouponDistributionRepository(@Qualifier("clickHouseJdbcTemplate") JdbcTemplate clickHouseJdbcTemplate) {
        this.clickHouseJdbcTemplate = clickHouseJdbcTemplate;
    }

    public void save(CouponDistribution distribution) {
        try {
            clickHouseJdbcTemplate.update(INSERT_SQL,
                    distribution.getDistributionId(),
                    distribution.getUserId(),
                    distribution.getCouponId(),
                    distribution.getCouponCode(),
                    distribution.getDenomination(),
                    distribution.getCouponType(),
                    distribution.getSceneCode(),
                    distribution.getMinOrderAmount(),
                    distribution.getStatus() != null ? distribution.getStatus().getCode() : 0,
                    distribution.getExperimentId(),
                    distribution.getGroupId(),
                    distribution.getRlActionIndex(),
                    distribution.getRlReward(),
                    distribution.getStateVector(),
                    toTimestamp(distribution.getIssueTime()),
                    toTimestamp(distribution.getExpireTime()),
                    toTimestamp(distribution.getUseTime()),
                    distribution.getOrderId(),
                    distribution.getOrderAmount(),
                    distribution.getDiscountAmount()
            );
            log.debug("Saved coupon distribution: {}", distribution.getDistributionId());
        } catch (Exception e) {
            log.error("Failed to save coupon distribution: {}", distribution.getDistributionId(), e);
        }
    }

    @Async
    public void saveAsync(CouponDistribution distribution) {
        save(distribution);
    }

    public void batchSave(List<CouponDistribution> distributions) {
        try {
            clickHouseJdbcTemplate.batchUpdate(INSERT_SQL, new BatchPreparedStatementSetter() {
                @Override
                public void setValues(PreparedStatement ps, int i) throws SQLException {
                    CouponDistribution d = distributions.get(i);
                    ps.setString(1, d.getDistributionId());
                    ps.setString(2, d.getUserId());
                    ps.setString(3, d.getCouponId());
                    ps.setString(4, d.getCouponCode());
                    ps.setBigDecimal(5, d.getDenomination());
                    ps.setInt(6, d.getCouponType());
                    ps.setInt(7, d.getSceneCode());
                    ps.setBigDecimal(8, d.getMinOrderAmount());
                    ps.setInt(9, d.getStatus() != null ? d.getStatus().getCode() : 0);
                    ps.setString(10, d.getExperimentId());
                    ps.setString(11, d.getGroupId());
                    ps.setObject(12, d.getRlActionIndex());
                    ps.setObject(13, d.getRlReward());
                    ps.setString(14, d.getStateVector());
                    ps.setTimestamp(15, toTimestamp(d.getIssueTime()));
                    ps.setTimestamp(16, toTimestamp(d.getExpireTime()));
                    ps.setTimestamp(17, toTimestamp(d.getUseTime()));
                    ps.setString(18, d.getOrderId());
                    ps.setBigDecimal(19, d.getOrderAmount());
                    ps.setBigDecimal(20, d.getDiscountAmount());
                }

                @Override
                public int getBatchSize() {
                    return distributions.size();
                }
            });
            log.info("Batch saved {} coupon distributions", distributions.size());
        } catch (Exception e) {
            log.error("Failed to batch save coupon distributions", e);
        }
    }

    public void updateStatus(CouponDistribution distribution) {
        try {
            clickHouseJdbcTemplate.update(UPDATE_STATUS_SQL,
                    distribution.getStatus().getCode(),
                    toTimestamp(distribution.getUseTime()),
                    distribution.getOrderId(),
                    distribution.getOrderAmount(),
                    distribution.getDiscountAmount(),
                    distribution.getRlReward(),
                    distribution.getDistributionId()
            );
            log.debug("Updated coupon distribution status: {}", distribution.getDistributionId());
        } catch (Exception e) {
            log.error("Failed to update coupon distribution: {}", distribution.getDistributionId(), e);
        }
    }

    public List<CouponDistribution> findByUserId(String userId) {
        String sql = "SELECT * FROM coupon_distribution WHERE user_id = ? ORDER BY issue_time DESC";
        try {
            return clickHouseJdbcTemplate.query(sql, new CouponDistributionRowMapper(), userId);
        } catch (Exception e) {
            log.error("Failed to find distributions by user: {}", userId, e);
            return List.of();
        }
    }

    public List<CouponDistribution> findPotentiallyExpired(int limit) {
        String sql = """
            SELECT * FROM coupon_distribution
            WHERE status = 0 AND expire_time < now()
            ORDER BY expire_time ASC LIMIT ?
            """;
        try {
            return clickHouseJdbcTemplate.query(sql, new CouponDistributionRowMapper(), limit);
        } catch (Exception e) {
            log.error("Failed to find potentially expired distributions", e);
            return List.of();
        }
    }

    public List<CouponDistribution> findPendingForTraining(int limit) {
        String sql = """
            SELECT * FROM coupon_distribution
            WHERE status IN (1, 2, 3) AND rl_reward IS NOT NULL
            ORDER BY update_time DESC LIMIT ?
            """;
        try {
            return clickHouseJdbcTemplate.query(sql, new CouponDistributionRowMapper(), limit);
        } catch (Exception e) {
            log.error("Failed to find pending distributions for training", e);
            return List.of();
        }
    }

    public List<CouponDistribution> findExpiringCoupons(java.time.LocalDateTime startTime,
                                                        java.time.LocalDateTime endTime,
                                                        int offset, int limit) {
        String sql = """
            SELECT * FROM coupon_distribution
            WHERE status = 0
              AND expire_time >= ?
              AND expire_time < ?
            ORDER BY expire_time ASC
            LIMIT ? OFFSET ?
            """;
        try {
            return clickHouseJdbcTemplate.query(sql, new CouponDistributionRowMapper(),
                    Timestamp.valueOf(startTime), Timestamp.valueOf(endTime), limit, offset);
        } catch (Exception e) {
            log.error("Failed to find expiring coupons between {} and {}", startTime, endTime, e);
            return List.of();
        }
    }

    public java.util.Optional<CouponDistribution> findById(String distributionId) {
        String sql = "SELECT * FROM coupon_distribution WHERE distribution_id = ? LIMIT 1";
        try {
            List<CouponDistribution> results = clickHouseJdbcTemplate.query(
                    sql, new CouponDistributionRowMapper(), distributionId);
            return results.isEmpty() ? java.util.Optional.empty() : java.util.Optional.of(results.get(0));
        } catch (Exception e) {
            log.error("Failed to find distribution by id: {}", distributionId, e);
            return java.util.Optional.empty();
        }
    }

    private Timestamp toTimestamp(java.time.LocalDateTime dateTime) {
        return dateTime != null ? Timestamp.valueOf(dateTime) : null;
    }

    private static class CouponDistributionRowMapper implements RowMapper<CouponDistribution> {
        @Override
        public CouponDistribution mapRow(ResultSet rs, int rowNum) throws SQLException {
            return CouponDistribution.builder()
                    .distributionId(rs.getString("distribution_id"))
                    .userId(rs.getString("user_id"))
                    .couponId(rs.getString("coupon_id"))
                    .couponCode(rs.getString("coupon_code"))
                    .denomination(rs.getBigDecimal("denomination"))
                    .couponType(rs.getInt("coupon_type"))
                    .sceneCode(rs.getInt("scene_code"))
                    .minOrderAmount(rs.getBigDecimal("min_order_amount"))
                    .status(com.coupon.model.enums.CouponStatus.fromCode(rs.getInt("status")))
                    .experimentId(rs.getString("experiment_id"))
                    .groupId(rs.getString("group_id"))
                    .rlActionIndex((Integer) rs.getObject("rl_action_index"))
                    .rlReward((Double) rs.getObject("rl_reward"))
                    .stateVector(rs.getString("state_vector"))
                    .issueTime(toLocalDateTime(rs.getTimestamp("issue_time")))
                    .expireTime(toLocalDateTime(rs.getTimestamp("expire_time")))
                    .useTime(toLocalDateTime(rs.getTimestamp("use_time")))
                    .orderId(rs.getString("order_id"))
                    .orderAmount(rs.getBigDecimal("order_amount"))
                    .discountAmount(rs.getBigDecimal("discount_amount"))
                    .createTime(toLocalDateTime(rs.getTimestamp("create_time")))
                    .updateTime(toLocalDateTime(rs.getTimestamp("update_time")))
                    .build();
        }

        private java.time.LocalDateTime toLocalDateTime(Timestamp timestamp) {
            return timestamp != null ? timestamp.toLocalDateTime() : null;
        }
    }
}
