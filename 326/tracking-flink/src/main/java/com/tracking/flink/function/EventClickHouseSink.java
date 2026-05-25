package com.tracking.flink.function;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.TrackEvent;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

public class EventClickHouseSink extends RichSinkFunction<TrackEvent> {

    private static final Logger LOG = LoggerFactory.getLogger(EventClickHouseSink.class);

    private final String host;
    private final int port;
    private final String database;
    private final String username;
    private final String password;

    private transient Connection connection;
    private transient List<TrackEvent> batch;
    private static final int BATCH_SIZE = 1000;
    private static final long FLUSH_INTERVAL_MS = 5000;
    private transient long lastFlushTime;

    public EventClickHouseSink(String host, int port, String database, String username, String password) {
        this.host = host;
        this.port = port;
        this.database = database;
        this.username = username;
        this.password = password;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        Class.forName("com.clickhouse.jdbc.ClickHouseDriver");
        String url = String.format("jdbc:clickhouse://%s:%d/%s", host, port, database);
        connection = DriverManager.getConnection(url, username, password);
        batch = new ArrayList<>(BATCH_SIZE);
        lastFlushTime = System.currentTimeMillis();
    }

    @Override
    public void invoke(TrackEvent event, Context context) throws Exception {
        batch.add(event);

        if (batch.size() >= BATCH_SIZE ||
                System.currentTimeMillis() - lastFlushTime > FLUSH_INTERVAL_MS) {
            flush();
        }
    }

    private void flush() throws Exception {
        if (batch.isEmpty()) {
            return;
        }

        String sql = String.format(
                "INSERT INTO %s.%s (" +
                        "id, event, timestamp, receive_time, " +
                        "anonymous_id, user_id, session_id, " +
                        "platform, app_id, app_version, channel, " +
                        "os, os_version, device_id, device_model, " +
                        "ip, user_agent, referrer, url, title, " +
                        "screen_width, screen_height, network_type, carrier, " +
                        "properties, source, country, province, city" +
                        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                database, TrackingConstants.CLICKHOUSE_TABLE_EVENTS
        );

        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            for (TrackEvent event : batch) {
                int idx = 1;
                ps.setString(idx++, event.getId());
                ps.setString(idx++, event.getEvent());
                ps.setLong(idx++, event.getTimestamp() != null ? event.getTimestamp() : 0);
                ps.setLong(idx++, event.getReceiveTime() != null ? event.getReceiveTime() : 0);
                ps.setString(idx++, event.getAnonymousId());
                ps.setString(idx++, event.getUserId());
                ps.setString(idx++, event.getSessionId());
                ps.setString(idx++, event.getPlatform());
                ps.setString(idx++, event.getAppId());
                ps.setString(idx++, event.getAppVersion());
                ps.setString(idx++, event.getChannel());
                ps.setString(idx++, event.getOs());
                ps.setString(idx++, event.getOsVersion());
                ps.setString(idx++, event.getDeviceId());
                ps.setString(idx++, event.getDeviceModel());
                ps.setString(idx++, event.getIp());
                ps.setString(idx++, event.getUserAgent());
                ps.setString(idx++, event.getReferrer());
                ps.setString(idx++, event.getUrl());
                ps.setString(idx++, event.getTitle());
                ps.setInt(idx++, event.getScreenWidth() != null ? event.getScreenWidth() : 0);
                ps.setInt(idx++, event.getScreenHeight() != null ? event.getScreenHeight() : 0);
                ps.setString(idx++, event.getNetworkType());
                ps.setString(idx++, event.getCarrier());
                ps.setString(idx++, event.getProperties() != null ? JSON.toJSONString(event.getProperties()) : "{}");
                ps.setString(idx++, event.getSource());
                ps.setString(idx++, event.getCountry());
                ps.setString(idx++, event.getProvince());
                ps.setString(idx++, event.getCity());
                ps.addBatch();
            }
            ps.executeBatch();
            LOG.info("Inserted {} events to ClickHouse", batch.size());
        }

        batch.clear();
        lastFlushTime = System.currentTimeMillis();
    }

    @Override
    public void close() throws Exception {
        if (!batch.isEmpty()) {
            flush();
        }
        if (connection != null && !connection.isClosed()) {
            connection.close();
        }
    }
}
