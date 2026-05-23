package com.analytics.sink;

import com.analytics.config.PipelineConfig;
import com.analytics.model.UserBehaviorAggregate;
import org.apache.flink.connector.jdbc.JdbcConnectionOptions;
import org.apache.flink.connector.jdbc.JdbcExecutionOptions;
import org.apache.flink.connector.jdbc.JdbcSink;
import org.apache.flink.streaming.api.functions.sink.SinkFunction;

public class ClickHouseSinkFactory {

    private static final String INSERT_SQL = 
            "INSERT INTO user_behavior_aggregate " +
            "(user_id, event_type, event_count, total_amount, window_start, window_end, process_time) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?)";

    public static SinkFunction<UserBehaviorAggregate> createClickHouseSink(PipelineConfig config) {
        return createClickHouseSink(
                config.getClickhouseUrl(),
                config.getClickhouseUser(),
                config.getClickhousePassword()
        );
    }

    public static SinkFunction<UserBehaviorAggregate> createClickHouseSink(
            String url,
            String username,
            String password) {

        return JdbcSink.sink(
                INSERT_SQL,
                (statement, aggregate) -> {
                    statement.setString(1, aggregate.getUserId());
                    statement.setString(2, aggregate.getEventType());
                    statement.setLong(3, aggregate.getEventCount());
                    statement.setBigDecimal(4, aggregate.getTotalAmount());
                    statement.setTimestamp(5, aggregate.getWindowStart());
                    statement.setTimestamp(6, aggregate.getWindowEnd());
                    statement.setTimestamp(7, aggregate.getProcessTime());
                },
                JdbcExecutionOptions.builder()
                        .withBatchSize(5000)
                        .withBatchIntervalMs(500)
                        .withMaxRetries(5)
                        .build(),
                new JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                        .withUrl(url)
                        .withDriverName("com.clickhouse.jdbc.ClickHouseDriver")
                        .withUsername(username)
                        .withPassword(password)
                        .withConnectionCheckTimeoutSeconds(60)
                        .build()
        );
    }

    public static String getCreateTableSql() {
        return "CREATE TABLE IF NOT EXISTS user_behavior_aggregate (" +
                "user_id String," +
                "event_type String," +
                "event_count UInt64," +
                "total_amount Decimal(18,2)," +
                "window_start DateTime," +
                "window_end DateTime," +
                "process_time DateTime" +
                ") ENGINE = MergeTree() " +
                "ORDER BY (user_id, event_type, window_start) " +
                "PARTITION BY toYYYYMMDD(window_start) " +
                "SETTINGS index_granularity = 8192";
    }
}
