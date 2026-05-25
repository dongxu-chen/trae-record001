package com.tracking.storage.dao;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.AnomalyAlert;
import com.tracking.common.model.AnomalyDetectionQuery;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Repository
public class AnomalyDetectionDao {

    private static final Logger LOG = LoggerFactory.getLogger(AnomalyDetectionDao.class);

    private final JdbcTemplate jdbcTemplate;
    private final JedisPool jedisPool;

    public AnomalyDetectionDao(DataSource dataSource, JedisPool jedisPool) {
        this.jdbcTemplate = new JdbcTemplate(dataSource);
        this.jedisPool = jedisPool;
    }

    public void saveAlert(AnomalyAlert alert) {
        String sql = "INSERT INTO " + TrackingConstants.CLICKHOUSE_TABLE_ANOMALY_DETECTION +
            " (alert_id, anomaly_type, severity, metric_name, dimension, dimension_value, " +
            "current_value, baseline_value, deviation_percent, z_score, window_start_time, " +
            "window_end_time, detection_time, description, details, status, acknowledged_by, " +
            "acknowledged_time, comment) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        try {
            jdbcTemplate.update(sql,
                alert.getAlertId(),
                alert.getAnomalyType(),
                alert.getSeverity(),
                alert.getMetricName(),
                alert.getDimension(),
                alert.getDimensionValue(),
                alert.getCurrentValue(),
                alert.getBaselineValue(),
                alert.getDeviationPercent(),
                alert.getZScore(),
                alert.getWindowStartTime(),
                alert.getWindowEndTime(),
                alert.getDetectionTime(),
                alert.getDescription(),
                alert.getDetails() != null ? JSON.toJSONString(alert.getDetails()) : null,
                alert.getStatus(),
                alert.getAcknowledgedBy(),
                alert.getAcknowledgedTime(),
                alert.getComment()
            );
        } catch (Exception e) {
            LOG.warn("Failed to save anomaly alert to ClickHouse, using Redis only", e);
        }

        saveToRedis(alert);
    }

    public List<AnomalyAlert> queryAlerts(AnomalyDetectionQuery query) {
        StringBuilder sql = new StringBuilder();
        List<Object> params = new ArrayList<>();

        sql.append("SELECT * FROM ").append(TrackingConstants.CLICKHOUSE_TABLE_ANOMALY_DETECTION)
           .append(" WHERE 1=1 ");

        if (query.getStartTime() != null) {
            sql.append("AND detection_time >= ? ");
            params.add(query.getStartTime());
        }
        if (query.getEndTime() != null) {
            sql.append("AND detection_time <= ? ");
            params.add(query.getEndTime());
        }
        if (query.getMetricName() != null) {
            sql.append("AND metric_name = ? ");
            params.add(query.getMetricName());
        }
        if (query.getAnomalyType() != null) {
            sql.append("AND anomaly_type = ? ");
            params.add(query.getAnomalyType());
        }
        if (query.getSeverity() != null) {
            sql.append("AND severity = ? ");
            params.add(query.getSeverity());
        }
        if (query.getStatus() != null) {
            sql.append("AND status = ? ");
            params.add(query.getStatus());
        }

        sql.append("ORDER BY detection_time DESC ");

        int page = query.getPage() != null ? query.getPage() : 1;
        int pageSize = query.getPageSize() != null ? query.getPageSize() : 20;
        sql.append("LIMIT ? OFFSET ? ");
        params.add(pageSize);
        params.add((page - 1) * pageSize);

        try {
            return jdbcTemplate.query(sql.toString(), this::mapRow, params.toArray());
        } catch (Exception e) {
            LOG.warn("Failed to query alerts from ClickHouse, trying Redis", e);
            return getRecentAlertsFromRedis(query.getSeverity(), pageSize);
        }
    }

    public Map<String, Object> getAlertStats(Long startTime, Long endTime) {
        Map<String, Object> stats = new HashMap<>();

        try (Jedis jedis = jedisPool.getResource()) {
            for (String severity : new String[]{
                TrackingConstants.ANOMALY_SEVERITY_CRITICAL,
                TrackingConstants.ANOMALY_SEVERITY_HIGH,
                TrackingConstants.ANOMALY_SEVERITY_MEDIUM,
                TrackingConstants.ANOMALY_SEVERITY_LOW
            }) {
                String listKey = "tracking:anomaly:alerts:" + severity;
                long count = jedis.llen(listKey);
                stats.put(severity + "_count", count);
            }
        } catch (Exception e) {
            LOG.warn("Failed to get alert stats from Redis", e);
        }

        try {
            String sql = "SELECT severity, count(*) as cnt FROM " + 
                TrackingConstants.CLICKHOUSE_TABLE_ANOMALY_DETECTION + 
                " WHERE detection_time >= ? AND detection_time <= ? GROUP BY severity";
            
            List<Map<String, Object>> results = jdbcTemplate.queryForList(sql, startTime, endTime);
            for (Map<String, Object> row : results) {
                String severity = (String) row.get("severity");
                long count = ((Number) row.get("cnt")).longValue();
                stats.put("db_" + severity + "_count", count);
            }
        } catch (Exception e) {
            LOG.warn("Failed to get alert stats from ClickHouse", e);
        }

        return stats;
    }

    public boolean acknowledgeAlert(String alertId, String acknowledgedBy, String comment) {
        long now = System.currentTimeMillis();

        try (Jedis jedis = jedisPool.getResource()) {
            String key = "tracking:anomaly:alert:" + alertId;
            String json = jedis.get(key);
            if (json != null) {
                AnomalyAlert alert = JSON.parseObject(json, AnomalyAlert.class);
                alert.setStatus("acknowledged");
                alert.setAcknowledgedBy(acknowledgedBy);
                alert.setAcknowledgedTime(now);
                alert.setComment(comment);
                jedis.setex(key, 24 * 3600, JSON.toJSONString(alert));
            }
        } catch (Exception e) {
            LOG.warn("Failed to acknowledge alert in Redis", e);
        }

        try {
            String sql = "ALTER TABLE " + TrackingConstants.CLICKHOUSE_TABLE_ANOMALY_DETECTION +
                " UPDATE status = 'acknowledged', acknowledged_by = ?, " +
                "acknowledged_time = ?, comment = ? WHERE alert_id = ?";
            jdbcTemplate.update(sql, acknowledgedBy, now, comment, alertId);
            return true;
        } catch (Exception e) {
            LOG.warn("ClickHouse ALTER may not be supported, ack stored in Redis only", e);
            return true;
        }
    }

    private List<AnomalyAlert> getRecentAlertsFromRedis(String severity, int limit) {
        List<AnomalyAlert> alerts = new ArrayList<>();

        try (Jedis jedis = jedisPool.getResource()) {
            String listKey = severity != null ? 
                "tracking:anomaly:alerts:" + severity : 
                "tracking:anomaly:alerts:" + TrackingConstants.ANOMALY_SEVERITY_HIGH;
            
            List<String> alertIds = jedis.lrange(listKey, 0, limit - 1);
            for (String alertId : alertIds) {
                String key = "tracking:anomaly:alert:" + alertId;
                String json = jedis.get(key);
                if (json != null) {
                    alerts.add(JSON.parseObject(json, AnomalyAlert.class));
                }
            }
        } catch (Exception e) {
            LOG.warn("Failed to get alerts from Redis", e);
        }

        return alerts;
    }

    private void saveToRedis(AnomalyAlert alert) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = "tracking:anomaly:alert:" + alert.getAlertId();
            jedis.setex(key, 24 * 3600, JSON.toJSONString(alert));

            String listKey = "tracking:anomaly:alerts:" + alert.getSeverity();
            jedis.lpush(listKey, alert.getAlertId());
            jedis.ltrim(listKey, 0, 99);
        } catch (Exception e) {
            LOG.warn("Failed to save alert to Redis", e);
        }
    }

    private AnomalyAlert mapRow(ResultSet rs, int rowNum) throws SQLException {
        String detailsJson = rs.getString("details");
        Map<String, Object> details = null;
        if (detailsJson != null && !detailsJson.isEmpty()) {
            details = JSON.parseObject(detailsJson, new com.alibaba.fastjson2.TypeReference<Map<String, Object>>() {});
        }

        return AnomalyAlert.builder()
                .alertId(rs.getString("alert_id"))
                .anomalyType(rs.getString("anomaly_type"))
                .severity(rs.getString("severity"))
                .metricName(rs.getString("metric_name"))
                .dimension(rs.getString("dimension"))
                .dimensionValue(rs.getString("dimension_value"))
                .currentValue(rs.getDouble("current_value"))
                .baselineValue(rs.getDouble("baseline_value"))
                .deviationPercent(rs.getDouble("deviation_percent"))
                .zScore(rs.getDouble("z_score"))
                .windowStartTime(rs.getLong("window_start_time"))
                .windowEndTime(rs.getLong("window_end_time"))
                .detectionTime(rs.getLong("detection_time"))
                .description(rs.getString("description"))
                .details(details)
                .status(rs.getString("status"))
                .acknowledgedBy(rs.getString("acknowledged_by"))
                .acknowledgedTime(rs.getLong("acknowledged_time"))
                .comment(rs.getString("comment"))
                .build();
    }
}
