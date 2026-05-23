package com.analytics.sink;

import com.analytics.config.PipelineConfig;
import com.analytics.model.MultiDimensionAggregate;
import org.apache.flink.connector.jdbc.JdbcConnectionOptions;
import org.apache.flink.connector.jdbc.JdbcExecutionOptions;
import org.apache.flink.connector.jdbc.JdbcSink;
import org.apache.flink.streaming.api.functions.sink.SinkFunction;

public class MultiDimensionClickHouseSink {

    private static final String INSERT_SQL = 
            "INSERT INTO multi_dimension_aggregate " +
            "(dimension_type, dimension_value, event_type, event_count, " +
            "unique_user_count, total_amount, avg_amount, window_start, window_end, process_time) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

    public static SinkFunction<MultiDimensionAggregate> createSink(PipelineConfig config) {
        return createSink(
                config.getClickhouseUrl(),
                config.getClickhouseUser(),
                config.getClickhousePassword()
        );
    }

    public static SinkFunction<MultiDimensionAggregate> createSink(
            String url,
            String username,
            String password) {

        return JdbcSink.sink(
                INSERT_SQL,
                (statement, aggregate) -> {
                    statement.setString(1, aggregate.getDimensionType());
                    statement.setString(2, aggregate.getDimensionValue());
                    statement.setString(3, aggregate.getEventType());
                    statement.setLong(4, aggregate.getEventCount());
                    statement.setLong(5, aggregate.getUniqueUserCount());
                    statement.setBigDecimal(6, aggregate.getTotalAmount());
                    statement.setBigDecimal(7, aggregate.getAvgAmount());
                    statement.setTimestamp(8, aggregate.getWindowStart());
                    statement.setTimestamp(9, aggregate.getWindowEnd());
                    statement.setTimestamp(10, aggregate.getProcessTime());
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
        return "CREATE TABLE IF NOT EXISTS multi_dimension_aggregate (" +
                "dimension_type String," +
                "dimension_value String," +
                "event_type String," +
                "event_count UInt64," +
                "unique_user_count UInt64," +
                "total_amount Decimal(18,2)," +
                "avg_amount Decimal(18,2)," +
                "window_start DateTime," +
                "window_end DateTime," +
                "process_time DateTime" +
                ") ENGINE = SummingMergeTree() " +
                "ORDER BY (dimension_type, dimension_value, event_type, window_start) " +
                "PARTITION BY toYYYYMMDD(window_start) " +
                "SETTINGS index_granularity = 8192";
    }
}
