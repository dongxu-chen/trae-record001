package com.abtest.service;

import com.abtest.dto.EventDTO;
import com.abtest.entity.Metric;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class ClickHouseMetricsService {

    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final Connection clickHouseConnection;
    private final ObjectMapper objectMapper;

    @Value("${clickhouse.database:abtest}")
    private String database;

    public void initTables() {
        try {
            String createDbSql = "CREATE DATABASE IF NOT EXISTS " + database;
            try (PreparedStatement stmt = clickHouseConnection.prepareStatement(createDbSql)) {
                stmt.execute();
            }

            String useDbSql = "USE " + database;
            try (PreparedStatement stmt = clickHouseConnection.prepareStatement(useDbSql)) {
                stmt.execute();
            }

            String createEventsTable = """
                CREATE TABLE IF NOT EXISTS events (
                    timestamp DateTime,
                    user_id String,
                    experiment_id Int64,
                    variant_name String,
                    event_name String,
                    properties String
                ) ENGINE = MergeTree()
                PARTITION BY toYYYYMM(timestamp)
                ORDER BY (experiment_id, variant_name, timestamp, user_id)
                """;
            try (PreparedStatement stmt = clickHouseConnection.prepareStatement(createEventsTable)) {
                stmt.execute();
            }

            String createAssignmentsTable = """
                CREATE TABLE IF NOT EXISTS user_assignments (
                    assignment_timestamp DateTime,
                    user_id String,
                    experiment_id Int64,
                    variant_name String,
                    bucket Int32
                ) ENGINE = MergeTree()
                PARTITION BY toYYYYMM(assignment_timestamp)
                ORDER BY (experiment_id, user_id, assignment_timestamp)
                """;
            try (PreparedStatement stmt = clickHouseConnection.prepareStatement(createAssignmentsTable)) {
                stmt.execute();
            }

            log.info("ClickHouse tables initialized successfully");
        } catch (Exception e) {
            log.error("Failed to initialize ClickHouse tables", e);
        }
    }

    public void recordUserAssignment(String userId, Long experimentId, String variantName, int bucket) {
        try {
            String sql = """
                INSERT INTO user_assignments (assignment_timestamp, user_id, experiment_id, variant_name, bucket)
                VALUES (?, ?, ?, ?, ?)
                """;
            try (PreparedStatement stmt = clickHouseConnection.prepareStatement(sql)) {
                stmt.setString(1, LocalDateTime.now().format(FORMATTER));
                stmt.setString(2, userId);
                stmt.setLong(3, experimentId);
                stmt.setString(4, variantName);
                stmt.setInt(5, bucket);
                stmt.execute();
            }
        } catch (Exception e) {
            log.error("Failed to record user assignment: userId={}, experimentId={}", userId, experimentId, e);
        }
    }

    public void trackEvent(EventDTO event) {
        try {
            String propertiesJson = event.getProperties() != null
                ? objectMapper.writeValueAsString(event.getProperties())
                : "{}";

            String sql = """
                INSERT INTO events (timestamp, user_id, experiment_id, variant_name, event_name, properties)
                VALUES (?, ?, ?, ?, ?, ?)
                """;

            try (PreparedStatement stmt = clickHouseConnection.prepareStatement(sql)) {
                stmt.setString(1, event.getTimestamp().format(FORMATTER));
                stmt.setString(2, event.getUserId());
                stmt.setLong(3, event.getExperimentId());
                stmt.setString(4, event.getVariantName() != null ? event.getVariantName() : "");
                stmt.setString(5, event.getEventName());
                stmt.setString(6, propertiesJson);
                stmt.execute();
            }
        } catch (Exception e) {
            log.error("Failed to track event: {}", event, e);
        }
    }

    private static final long DEFAULT_DELAY_MINUTES = 60;

    public Map<String, Object> calculateMetric(Long experimentId, String variantName, Metric metric) {
        return calculateMetric(experimentId, variantName, metric, DEFAULT_DELAY_MINUTES);
    }

    public Map<String, Object> calculateMetric(Long experimentId, String variantName, Metric metric, long delayMinutes) {
        Map<String, Object> result = new HashMap<>();

        try {
            if (metric.getType() == Metric.MetricType.CONVERSION) {
                result = calculateConversionMetric(experimentId, variantName, metric, delayMinutes);
            } else {
                result = calculateContinuousMetric(experimentId, variantName, metric, delayMinutes);
            }
        } catch (Exception e) {
            log.error("Failed to calculate metric: {} for variant: {}", metric.getName(), variantName, e);
            result.put("error", e.getMessage());
        }

        return result;
    }

    private Map<String, Object> calculateConversionMetric(Long experimentId, String variantName, Metric metric,
                                                           long delayMinutes) throws Exception {
        Map<String, Object> result = new HashMap<>();

        String eligibleUsersSql = """
            SELECT DISTINCT user_id
            FROM user_assignments
            WHERE experiment_id = ?
              AND variant_name = ?
              AND assignment_timestamp <= now() - INTERVAL ? MINUTE
            """;

        String exposureSql = """
            SELECT COUNT(DISTINCT e.user_id) as total_users
            FROM events e
            INNER JOIN (%s) eu ON e.user_id = eu.user_id
            WHERE e.experiment_id = ?
              AND e.variant_name = ?
              AND e.event_name = 'exposure'
            """.formatted(eligibleUsersSql);

        String conversionSql = """
            SELECT COUNT(DISTINCT e.user_id) as converted_users
            FROM events e
            INNER JOIN (%s) eu ON e.user_id = eu.user_id
            WHERE e.experiment_id = ?
              AND e.variant_name = ?
              AND e.event_name = ?
              AND e.user_id IN (
                  SELECT DISTINCT e2.user_id
                  FROM events e2
                  INNER JOIN (%s) eu2 ON e2.user_id = eu2.user_id
                  WHERE e2.experiment_id = ?
                    AND e2.variant_name = ?
                    AND e2.event_name = 'exposure'
              )
            """.formatted(eligibleUsersSql, eligibleUsersSql);

        int totalUsers = 0;
        int convertedUsers = 0;

        try (PreparedStatement stmt = clickHouseConnection.prepareStatement(exposureSql)) {
            stmt.setLong(1, experimentId);
            stmt.setString(2, variantName);
            stmt.setLong(3, delayMinutes);
            stmt.setLong(4, experimentId);
            stmt.setString(5, variantName);
            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    totalUsers = rs.getInt("total_users");
                }
            }
        }

        try (PreparedStatement stmt = clickHouseConnection.prepareStatement(conversionSql)) {
            stmt.setLong(1, experimentId);
            stmt.setString(2, variantName);
            stmt.setLong(3, delayMinutes);
            stmt.setLong(4, experimentId);
            stmt.setString(5, variantName);
            stmt.setString(6, metric.getEventName());
            stmt.setLong(7, experimentId);
            stmt.setString(8, variantName);
            stmt.setLong(9, delayMinutes);
            stmt.setLong(10, experimentId);
            stmt.setString(11, variantName);
            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    convertedUsers = rs.getInt("converted_users");
                }
            }
        }

        double conversionRate = totalUsers > 0 ? (double) convertedUsers / totalUsers : 0.0;

        result.put("totalUsers", totalUsers);
        result.put("convertedUsers", convertedUsers);
        result.put("conversionRate", conversionRate);
        result.put("metricType", "CONVERSION");
        result.put("delayMinutes", delayMinutes);

        return result;
    }

    private Map<String, Object> calculateContinuousMetric(Long experimentId, String variantName, Metric metric,
                                                           long delayMinutes) throws Exception {
        Map<String, Object> result = new HashMap<>();

        String propertyName = metric.getPropertyName() != null ? metric.getPropertyName() : "value";
        String aggregation = getAggregationFunction(metric.getAggregationType(), propertyName);

        String eligibleUsersSql = """
            SELECT DISTINCT user_id
            FROM user_assignments
            WHERE experiment_id = ?
              AND variant_name = ?
              AND assignment_timestamp <= now() - INTERVAL ? MINUTE
            """;

        String sql = """
            SELECT
                COUNT(DISTINCT e.user_id) as user_count,
                COUNT(*) as event_count,
                %s as metric_value,
                avg(toFloat64(JSONExtractString(e.properties, '%s'))) as avg_value,
                stddevPop(toFloat64(JSONExtractString(e.properties, '%s'))) as stddev_value,
                sum(toFloat64(JSONExtractString(e.properties, '%s'))) as sum_value
            FROM events e
            INNER JOIN (%s) eu ON e.user_id = eu.user_id
            WHERE e.experiment_id = ?
              AND e.variant_name = ?
              AND e.event_name = ?
            """.formatted(aggregation, propertyName, propertyName, propertyName, eligibleUsersSql);

        try (PreparedStatement stmt = clickHouseConnection.prepareStatement(sql)) {
            stmt.setLong(1, experimentId);
            stmt.setString(2, variantName);
            stmt.setLong(3, delayMinutes);
            stmt.setLong(4, experimentId);
            stmt.setString(5, variantName);
            stmt.setString(6, metric.getEventName());

            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    result.put("userCount", rs.getInt("user_count"));
                    result.put("eventCount", rs.getInt("event_count"));
                    result.put("metricValue", rs.getDouble("metric_value"));
                    result.put("avgValue", rs.getDouble("avg_value"));
                    result.put("stddevValue", rs.getDouble("stddev_value"));
                    result.put("sumValue", rs.getDouble("sum_value"));
                    result.put("metricType", "CONTINUOUS");
                    result.put("delayMinutes", delayMinutes);
                }
            }
        }

        return result;
    }

    private String getAggregationFunction(Metric.AggregationType type, String propertyName) {
        if (type == null) {
            return "avg(toFloat64(JSONExtractString(properties, '" + propertyName + "')))";
        }
        return switch (type) {
            case SUM -> "sum(toFloat64(JSONExtractString(properties, '" + propertyName + "')))";
            case AVG -> "avg(toFloat64(JSONExtractString(properties, '" + propertyName + "')))";
            case COUNT -> "count(*)";
            case DISTINCT_COUNT -> "count(distinct user_id)";
        };
    }

    public List<Map<String, Object>> getMetricTrend(Long experimentId, String variantName,
                                                     Metric metric, int days) {
        return getMetricTrend(experimentId, variantName, metric, days, DEFAULT_DELAY_MINUTES);
    }

    public List<Map<String, Object>> getMetricTrend(Long experimentId, String variantName,
                                                     Metric metric, int days, long delayMinutes) {
        List<Map<String, Object>> trend = new ArrayList<>();

        try {
            String propertyName = metric.getPropertyName() != null ? metric.getPropertyName() : "value";
            String aggregation = metric.getType() == Metric.MetricType.CONVERSION
                ? "count(distinct e.user_id)"
                : "avg(toFloat64(JSONExtractString(e.properties, '" + propertyName + "')))";

            String eligibleUsersSql = """
                SELECT DISTINCT user_id
                FROM user_assignments
                WHERE experiment_id = ?
                  AND variant_name = ?
                  AND assignment_timestamp <= now() - INTERVAL ? MINUTE
                """;

            String sql = """
                SELECT
                    toDate(e.timestamp) as date,
                    %s as value
                FROM events e
                INNER JOIN (%s) eu ON e.user_id = eu.user_id
                WHERE e.experiment_id = ?
                  AND e.variant_name = ?
                  AND e.event_name = ?
                  AND e.timestamp >= now() - INTERVAL ? DAY
                GROUP BY date
                ORDER BY date
                """.formatted(aggregation, eligibleUsersSql);

            try (PreparedStatement stmt = clickHouseConnection.prepareStatement(sql)) {
                stmt.setLong(1, experimentId);
                stmt.setString(2, variantName);
                stmt.setLong(3, delayMinutes);
                stmt.setLong(4, experimentId);
                stmt.setString(5, variantName);
                stmt.setString(6, metric.getEventName());
                stmt.setInt(7, days);

                try (ResultSet rs = stmt.executeQuery()) {
                    while (rs.next()) {
                        Map<String, Object> point = new HashMap<>();
                        point.put("date", rs.getString("date"));
                        point.put("value", rs.getDouble("value"));
                        trend.add(point);
                    }
                }
            }
        } catch (Exception e) {
            log.error("Failed to get metric trend", e);
        }

        return trend;
    }
}
