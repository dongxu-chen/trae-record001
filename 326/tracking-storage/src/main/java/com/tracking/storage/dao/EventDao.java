package com.tracking.storage.dao;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.ClickStreamQuery;
import com.tracking.common.model.ClickStreamResult;
import com.tracking.common.model.TrackEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

@Repository
public class EventDao {

    private static final Logger LOG = LoggerFactory.getLogger(EventDao.class);

    private final JdbcTemplate jdbcTemplate;

    public EventDao(DataSource dataSource) {
        this.jdbcTemplate = new JdbcTemplate(dataSource);
    }

    public ClickStreamResult queryClickStream(ClickStreamQuery query) {
        StringBuilder sql = new StringBuilder();
        List<Object> params = new ArrayList<>();

        sql.append("SELECT * FROM ").append(TrackingConstants.CLICKHOUSE_TABLE_EVENTS).append(" WHERE 1=1 ");

        if (query.getUserId() != null) {
            sql.append("AND user_id = ? ");
            params.add(query.getUserId());
        }
        if (query.getAnonymousId() != null) {
            sql.append("AND anonymous_id = ? ");
            params.add(query.getAnonymousId());
        }
        if (query.getSessionId() != null) {
            sql.append("AND session_id = ? ");
            params.add(query.getSessionId());
        }
        if (query.getDeviceId() != null) {
            sql.append("AND device_id = ? ");
            params.add(query.getDeviceId());
        }
        if (query.getStartTime() != null) {
            sql.append("AND timestamp >= ? ");
            params.add(query.getStartTime());
        }
        if (query.getEndTime() != null) {
            sql.append("AND timestamp <= ? ");
            params.add(query.getEndTime());
        }
        if (query.getEvent() != null) {
            sql.append("AND event = ? ");
            params.add(query.getEvent());
        }
        if (query.getPlatform() != null) {
            sql.append("AND platform = ? ");
            params.add(query.getPlatform());
        }
        if (query.getAppId() != null) {
            sql.append("AND app_id = ? ");
            params.add(query.getAppId());
        }

        String countSql = "SELECT count() FROM (" + sql + ")";
        Long total = jdbcTemplate.queryForObject(countSql, params.toArray(), Long.class);

        sql.append("ORDER BY timestamp DESC ");

        int page = query.getPage() != null ? query.getPage() : 1;
        int pageSize = query.getPageSize() != null ? query.getPageSize() : 20;
        int offset = (page - 1) * pageSize;
        sql.append("LIMIT ? OFFSET ? ");
        params.add(pageSize);
        params.add(offset);

        LOG.debug("Query click stream SQL: {}", sql);
        List<TrackEvent> events = jdbcTemplate.query(sql.toString(), params.toArray(), new EventRowMapper());

        return ClickStreamResult.builder()
                .total(total != null ? total : 0L)
                .events(events)
                .page(page)
                .pageSize(pageSize)
                .build();
    }

    public long countDistinctUsers(Long startTime, Long endTime, String platform, String appId) {
        StringBuilder sql = new StringBuilder();
        List<Object> params = new ArrayList<>();

        sql.append("SELECT uniqExact(user_id) FROM ").append(TrackingConstants.CLICKHOUSE_TABLE_EVENTS)
                .append(" WHERE 1=1 ");

        if (startTime != null) {
            sql.append("AND timestamp >= ? ");
            params.add(startTime);
        }
        if (endTime != null) {
            sql.append("AND timestamp <= ? ");
            params.add(endTime);
        }
        if (platform != null) {
            sql.append("AND platform = ? ");
            params.add(platform);
        }
        if (appId != null) {
            sql.append("AND app_id = ? ");
            params.add(appId);
        }

        Long result = jdbcTemplate.queryForObject(sql.toString(), params.toArray(), Long.class);
        return result != null ? result : 0L;
    }

    public List<TrackEvent> queryUserEventsByStep(String userId, String event, Long startTime, Long endTime) {
        String sql = "SELECT * FROM " + TrackingConstants.CLICKHOUSE_TABLE_EVENTS +
                " WHERE user_id = ? AND event = ? AND timestamp >= ? AND timestamp <= ? " +
                "ORDER BY timestamp ASC";

        return jdbcTemplate.query(sql, new Object[]{userId, event, startTime, endTime}, new EventRowMapper());
    }

    private static class EventRowMapper implements RowMapper<TrackEvent> {
        @Override
        public TrackEvent mapRow(ResultSet rs, int rowNum) throws SQLException {
            TrackEvent event = TrackEvent.builder()
                    .id(rs.getString("id"))
                    .event(rs.getString("event"))
                    .timestamp(rs.getLong("timestamp"))
                    .receiveTime(rs.getLong("receive_time"))
                    .anonymousId(rs.getString("anonymous_id"))
                    .userId(rs.getString("user_id"))
                    .sessionId(rs.getString("session_id"))
                    .platform(rs.getString("platform"))
                    .appId(rs.getString("app_id"))
                    .appVersion(rs.getString("app_version"))
                    .channel(rs.getString("channel"))
                    .os(rs.getString("os"))
                    .osVersion(rs.getString("os_version"))
                    .deviceId(rs.getString("device_id"))
                    .deviceModel(rs.getString("device_model"))
                    .ip(rs.getString("ip"))
                    .userAgent(rs.getString("user_agent"))
                    .referrer(rs.getString("referrer"))
                    .url(rs.getString("url"))
                    .title(rs.getString("title"))
                    .screenWidth(rs.getInt("screen_width"))
                    .screenHeight(rs.getInt("screen_height"))
                    .networkType(rs.getString("network_type"))
                    .carrier(rs.getString("carrier"))
                    .source(rs.getString("source"))
                    .country(rs.getString("country"))
                    .province(rs.getString("province"))
                    .city(rs.getString("city"))
                    .build();

            String propertiesJson = rs.getString("properties");
            if (propertiesJson != null && !propertiesJson.isEmpty()) {
                event.setProperties(JSON.parseObject(propertiesJson, JSONObject.class));
            }

            return event;
        }
    }
}
