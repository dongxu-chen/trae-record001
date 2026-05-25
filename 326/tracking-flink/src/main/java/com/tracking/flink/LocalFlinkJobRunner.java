package com.tracking.flink;

import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LocalFlinkJobRunner {

    private static final Logger LOG = LoggerFactory.getLogger(LocalFlinkJobRunner.class);

    public static void main(String[] args) throws Exception {
        String[] params = new String[]{
                "--kafka.brokers", "localhost:9092",
                "--kafka.group.id", "tracking_flink_local",
                "--redis.host", "localhost",
                "--redis.port", "6379",
                "--redis.password", "",
                "--clickhouse.host", "localhost",
                "--clickhouse.port", "8123",
                "--clickhouse.database", "tracking",
                "--clickhouse.username", "default",
                "--clickhouse.password", "",
                "--session.timeout.ms", "1800000"
        };

        LOG.info("Starting Flink job in local mode...");
        TrackingFlinkJob.main(params);
    }
}
