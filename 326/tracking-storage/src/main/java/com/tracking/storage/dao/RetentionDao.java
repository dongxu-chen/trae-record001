package com.tracking.storage.dao;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.RetentionQuery;
import com.tracking.common.model.RetentionResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import javax.sql.DataSource;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Repository
public class RetentionDao {

    private static final Logger LOG = LoggerFactory.getLogger(RetentionDao.class);

    private final JdbcTemplate jdbcTemplate;
    private final JedisPool jedisPool;

    public RetentionDao(DataSource dataSource, JedisPool jedisPool) {
        this.jdbcTemplate = new JdbcTemplate(dataSource);
        this.jedisPool = jedisPool;
    }

    public RetentionResult calculateRetention(RetentionQuery query) {
        String cacheKey = buildCacheKey(query);

        if (Boolean.TRUE.equals(query.getUseCache())) {
            RetentionResult cached = getFromCache(cacheKey);
            if (cached != null) {
                return cached;
            }
        }

        List<Integer> retentionDays = query.getRetentionDays();
        if (retentionDays == null || retentionDays.isEmpty()) {
            retentionDays = new ArrayList<>();
            for (int day : TrackingConstants.RETENTION_DEFAULT_DAYS) {
                retentionDays.add(day);
            }
        }

        RetentionResult result;

        if (query.getGroupBy() != null) {
            result = calculateGroupedRetention(query, retentionDays);
        } else {
            result = calculateSingleRetention(query, retentionDays);
        }

        saveToCache(cacheKey, result);
        return result;
    }

    private RetentionResult calculateSingleRetention(RetentionQuery query, List<Integer> retentionDays) {
        long initialUsers = getInitialUserCount(query);

        List<RetentionResult.RetentionItem> retentionItems = new ArrayList<>();

        for (int day : retentionDays) {
            long returnUsers = getReturnUserCount(query, day);
            double retentionRate = initialUsers > 0 ? (double) returnUsers / initialUsers * 100 : 0;

            retentionItems.add(RetentionResult.RetentionItem.builder()
                    .day(day)
                    .label(day + "天留存")
                    .returnUsers(returnUsers)
                    .retentionRate(retentionRate)
                    .build());
        }

        return RetentionResult.builder()
                .retentionType(query.getRetentionType())
                .initialEvent(query.getInitialEvent())
                .returnEvent(query.getReturnEvent())
                .startTime(query.getStartTime())
                .endTime(query.getEndTime())
                .initialUsers(initialUsers)
                .retentionItems(retentionItems)
                .build();
    }

    private RetentionResult calculateGroupedRetention(RetentionQuery query, List<Integer> retentionDays) {
        RetentionResult result = calculateSingleRetention(query, retentionDays);

        Map<String, List<RetentionResult.RetentionItem>> groupResults = new HashMap<>();

        String groupBy = query.getGroupBy();
        String groupSql = buildGroupBySql(query, groupBy);

        try {
            List<Map<String, Object>> groupUsers = jdbcTemplate.queryForList(groupSql);

            for (Map<String, Object> groupRow : groupUsers) {
                String groupValue = String.valueOf(groupRow.get("group_val"));
                long groupInitialUsers = ((Number) groupRow.get("initial_users")).longValue();

                List<RetentionResult.RetentionItem> groupItems = new ArrayList<>();

                for (int day : retentionDays) {
                    long returnUsers = getGroupedReturnUserCount(query, groupBy, groupValue, day);
                    double retentionRate = groupInitialUsers > 0 ? 
                        (double) returnUsers / groupInitialUsers * 100 : 0;

                    groupItems.add(RetentionResult.RetentionItem.builder()
                            .day(day)
                            .label(day + "天留存")
                            .returnUsers(returnUsers)
                            .retentionRate(retentionRate)
                            .build());
                }

                groupResults.put(groupValue, groupItems);
            }
        } catch (Exception e) {
            LOG.warn("Failed to calculate grouped retention", e);
        }

        result.setGroupResults(groupResults);
        return result;
    }

    private long getInitialUserCount(RetentionQuery query) {
        StringBuilder sql = new StringBuilder();
        List<Object> params = new ArrayList<>();

        sql.append("SELECT COUNT(DISTINCT user_id) as cnt FROM ")
           .append(TrackingConstants.CLICKHOUSE_TABLE_EVENTS)
           .append(" WHERE event_type = ? ")
           .append("AND timestamp >= ? AND timestamp <= ? ");

        params.add(query.getInitialEvent());
        params.add(query.getStartTime());
        params.add(query.getEndTime());

        if (query.getPlatform() != null) {
            sql.append("AND platform = ? ");
            params.add(query.getPlatform());
        }
        if (query.getAppId() != null) {
            sql.append("AND app_id = ? ");
            params.add(query.getAppId());
        }
        if (query.getChannel() != null) {
            sql.append("AND properties->'channel' = ? ");
            params.add(query.getChannel());
        }

        try {
            return jdbcTemplate.queryForObject(sql.toString(), Long.class, params.toArray());
        } catch (Exception e) {
            LOG.warn("Failed to get initial user count", e);
            return 0;
        }
    }

    private long getReturnUserCount(RetentionQuery query, int day) {
        long dayStartMillis = query.getStartTime();
        long dayEndMillis = query.getEndTime();
        long returnStart = dayStartMillis + (long) day * 24 * 60 * 60 * 1000;
        long returnEnd = dayEndMillis + (long) day * 24 * 60 * 60 * 1000;

        StringBuilder sql = new StringBuilder();
        List<Object> params = new ArrayList<>();

        sql.append("SELECT COUNT(DISTINCT e2.user_id) as cnt FROM (")
           .append("  SELECT DISTINCT user_id FROM ").append(TrackingConstants.CLICKHOUSE_TABLE_EVENTS)
           .append("  WHERE event_type = ? AND timestamp >= ? AND timestamp <= ? ");

        params.add(query.getInitialEvent());
        params.add(dayStartMillis);
        params.add(dayEndMillis);

        if (query.getPlatform() != null) {
            sql.append("  AND platform = ? ");
            params.add(query.getPlatform());
        }
        if (query.getAppId() != null) {
            sql.append("  AND app_id = ? ");
            params.add(query.getAppId());
        }
        if (query.getChannel() != null) {
            sql.append("  AND properties->'channel' = ? ");
            params.add(query.getChannel());
        }

        sql.append(") e1 INNER JOIN (")
           .append("  SELECT DISTINCT user_id FROM ").append(TrackingConstants.CLICKHOUSE_TABLE_EVENTS)
           .append("  WHERE event_type = ? AND timestamp >= ? AND timestamp <= ? ");

        params.add(query.getReturnEvent());
        params.add(returnStart);
        params.add(returnEnd);

        if (query.getPlatform() != null) {
            sql.append("  AND platform = ? ");
            params.add(query.getPlatform());
        }
        if (query.getAppId() != null) {
            sql.append("  AND app_id = ? ");
            params.add(query.getAppId());
        }

        sql.append(") e2 ON e1.user_id = e2.user_id");

        try {
            return jdbcTemplate.queryForObject(sql.toString(), Long.class, params.toArray());
        } catch (Exception e) {
            LOG.warn("Failed to get return user count for day {}", day, e);
            return 0;
        }
    }

    private String buildGroupBySql(RetentionQuery query, String groupBy) {
        StringBuilder sql = new StringBuilder();
        List<Object> params = new ArrayList<>();

        String groupExpr;
        if ("platform".equals(groupBy) || "app_id".equals(groupBy)) {
            groupExpr = groupBy;
        } else {
            groupExpr = "properties->'" + groupBy + "'";
        }

        sql.append("SELECT ")
           .append(groupExpr).append(" as group_val, ")
           .append("COUNT(DISTINCT user_id) as initial_users ")
           .append("FROM ").append(TrackingConstants.CLICKHOUSE_TABLE_EVENTS)
           .append(" WHERE event_type = ? ")
           .append("AND timestamp >= ? AND timestamp <= ? ");

        params.add(query.getInitialEvent());
        params.add(query.getStartTime());
        params.add(query.getEndTime());

        if (query.getPlatform() != null) {
            sql.append("AND platform = ? ");
            params.add(query.getPlatform());
        }
        if (query.getAppId() != null) {
            sql.append("AND app_id = ? ");
            params.add(query.getAppId());
        }

        sql.append("GROUP BY ").append(groupExpr);

        return sql.toString();
    }

    private long getGroupedReturnUserCount(RetentionQuery query, String groupBy, String groupValue, int day) {
        long dayStartMillis = query.getStartTime();
        long dayEndMillis = query.getEndTime();
        long returnStart = dayStartMillis + (long) day * 24 * 60 * 60 * 1000;
        long returnEnd = dayEndMillis + (long) day * 24 * 60 * 60 * 1000;

        String groupExpr;
        if ("platform".equals(groupBy) || "app_id".equals(groupBy)) {
            groupExpr = groupBy;
        } else {
            groupExpr = "properties->'" + groupBy + "'";
        }

        StringBuilder sql = new StringBuilder();
        List<Object> params = new ArrayList<>();

        sql.append("SELECT COUNT(DISTINCT e2.user_id) as cnt FROM (")
           .append("  SELECT DISTINCT user_id FROM ").append(TrackingConstants.CLICKHOUSE_TABLE_EVENTS)
           .append("  WHERE event_type = ? AND timestamp >= ? AND timestamp <= ? ")
           .append("  AND ").append(groupExpr).append(" = ? ");

        params.add(query.getInitialEvent());
        params.add(dayStartMillis);
        params.add(dayEndMillis);
        params.add(groupValue);

        if (query.getPlatform() != null) {
            sql.append("  AND platform = ? ");
            params.add(query.getPlatform());
        }
        if (query.getAppId() != null) {
            sql.append("  AND app_id = ? ");
            params.add(query.getAppId());
        }

        sql.append(") e1 INNER JOIN (")
           .append("  SELECT DISTINCT user_id FROM ").append(TrackingConstants.CLICKHOUSE_TABLE_EVENTS)
           .append("  WHERE event_type = ? AND timestamp >= ? AND timestamp <= ? ");

        params.add(query.getReturnEvent());
        params.add(returnStart);
        params.add(returnEnd);

        if (query.getPlatform() != null) {
            sql.append("  AND platform = ? ");
            params.add(query.getPlatform());
        }
        if (query.getAppId() != null) {
            sql.append("  AND app_id = ? ");
            params.add(query.getAppId());
        }

        sql.append(") e2 ON e1.user_id = e2.user_id");

        try {
            return jdbcTemplate.queryForObject(sql.toString(), Long.class, params.toArray());
        } catch (Exception e) {
            LOG.warn("Failed to get grouped return user count", e);
            return 0;
        }
    }

    private String buildCacheKey(RetentionQuery query) {
        StringBuilder sb = new StringBuilder("retention:");
        sb.append(query.getInitialEvent()).append(":");
        sb.append(query.getReturnEvent()).append(":");
        sb.append(query.getStartTime()).append(":");
        sb.append(query.getEndTime()).append(":");
        if (query.getRetentionDays() != null) {
            sb.append(query.getRetentionDays().toString());
        }
        if (query.getPlatform() != null) sb.append(":").append(query.getPlatform());
        if (query.getAppId() != null) sb.append(":").append(query.getAppId());
        if (query.getGroupBy() != null) sb.append(":group:").append(query.getGroupBy());
        return sb.toString();
    }

    private RetentionResult getFromCache(String key) {
        try (Jedis jedis = jedisPool.getResource()) {
            String json = jedis.get(key);
            if (json != null) {
                return JSON.parseObject(json, RetentionResult.class);
            }
        } catch (Exception e) {
            LOG.warn("Failed to get retention from cache", e);
        }
        return null;
    }

    private void saveToCache(String key, RetentionResult result) {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.setex(key, 1800, JSON.toJSONString(result));
        } catch (Exception e) {
            LOG.warn("Failed to save retention to cache", e);
        }
    }
}
