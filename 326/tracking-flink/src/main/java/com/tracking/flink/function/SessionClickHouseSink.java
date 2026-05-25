package com.tracking.flink.function;

import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.SessionInfo;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.util.ArrayList;
import java.util.List;

public class SessionClickHouseSink extends RichSinkFunction<SessionInfo> {

    private static final Logger LOG = LoggerFactory.getLogger(SessionClickHouseSink.class);

    private final String host;
    private final int port;
    private final String database;
    private final String username;
    private final String password;

    private transient Connection connection;
    private transient List<SessionInfo> batch;
    private static final int BATCH_SIZE = 500;
    private static final long FLUSH_INTERVAL_MS = 10000;
    private transient long lastFlushTime;

    public SessionClickHouseSink(String host, int port, String database, String username, String password) {
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
    public void invoke(SessionInfo session, Context context) throws Exception {
        batch.add(session);

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
                        "session_id, anonymous_id, user_id, device_id, " +
                        "start_time, end_time, duration, event_count, " +
                        "first_page, last_page, entry_source" +
                        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                database, TrackingConstants.CLICKHOUSE_TABLE_SESSIONS
        );

        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            for (SessionInfo session : batch) {
                int idx = 1;
                ps.setString(idx++, session.getSessionId());
                ps.setString(idx++, session.getAnonymousId());
                ps.setString(idx++, session.getUserId());
                ps.setString(idx++, session.getDeviceId());
                ps.setLong(idx++, session.getStartTime() != null ? session.getStartTime() : 0);
                ps.setLong(idx++, session.getEndTime() != null ? session.getEndTime() : 0);
                ps.setLong(idx++, session.getStartTime() != null && session.getEndTime() != null
                        ? session.getEndTime() - session.getStartTime() : 0);
                ps.setInt(idx++, session.getEventCount() != null ? session.getEventCount() : 0);
                ps.setString(idx++, session.getFirstPage());
                ps.setString(idx++, session.getLastPage());
                ps.setString(idx++, session.getEntrySource());
                ps.addBatch();
            }
            ps.executeBatch();
            LOG.info("Inserted {} sessions to ClickHouse", batch.size());
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
