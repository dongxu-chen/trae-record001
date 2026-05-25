package com.coupon.clickhouse.repository;

import com.coupon.abtest.service.ABTestTrackingService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.LocalDateTime;

@Slf4j
@Repository
public class ABTestEventRepository {

    private final JdbcTemplate clickHouseJdbcTemplate;

    private static final String INSERT_SQL = """
        INSERT INTO abtest_events (
            event_id, event_type, user_id, experiment_id, group_id,
            action, scene, source, properties, event_time, create_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())
        """;

    public ABTestEventRepository(@Qualifier("clickHouseJdbcTemplate") JdbcTemplate clickHouseJdbcTemplate) {
        this.clickHouseJdbcTemplate = clickHouseJdbcTemplate;
    }

    @Async
    public void saveEvent(ABTestTrackingService.TrackingEvent event) {
        try {
            String propertiesJson = event.getProperties() != null
                    ? com.alibaba.fastjson2.JSON.toJSONString(event.getProperties())
                    : "{}";

            clickHouseJdbcTemplate.update(INSERT_SQL,
                    event.getEventId(),
                    event.getEventType(),
                    event.getUserId(),
                    event.getExperimentId(),
                    event.getGroupId(),
                    event.getAction(),
                    event.getScene(),
                    event.getSource(),
                    propertiesJson,
                    toTimestamp(event.getTimestamp())
            );
            log.debug("Saved ABTest event: {}", event.getEventId());
        } catch (Exception e) {
            log.error("Failed to save ABTest event: {}", event.getEventId(), e);
        }
    }

    private Timestamp toTimestamp(LocalDateTime dateTime) {
        return dateTime != null ? Timestamp.valueOf(dateTime) : null;
    }
}
