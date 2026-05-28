package com.datasync.service;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
public class MetricsService {

    private final MeterRegistry meterRegistry;

    private final Counter binlogEventCounter;
    private final Counter canalErrorCounter;
    private final Counter parseErrorCounter;
    private final Counter kafkaSendSuccessCounter;
    private final Counter kafkaSendErrorCounter;
    private final Counter kafkaConsumeSuccessCounter;
    private final Counter kafkaConsumeErrorCounter;
    private final Counter clickHouseWriteSuccessCounter;
    private final Counter clickHouseWriteErrorCounter;
    private final Counter conflictResolutionCounter;
    private final Counter fullSyncCounter;

    private final Timer clickHouseWriteTimer;

    private final AtomicLong syncDelayGauge;
    private final AtomicLong lastSyncTimestampGauge;
    private final AtomicLong totalRowsSyncedGauge;

    public MetricsService(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;

        this.binlogEventCounter = Counter.builder("mysql_ch_sync_binlog_events_total")
                .description("Total number of binlog events received")
                .tag("type", "all")
                .register(meterRegistry);

        this.canalErrorCounter = Counter.builder("mysql_ch_sync_canal_errors_total")
                .description("Total number of canal errors")
                .register(meterRegistry);

        this.parseErrorCounter = Counter.builder("mysql_ch_sync_parse_errors_total")
                .description("Total number of parse errors")
                .register(meterRegistry);

        this.kafkaSendSuccessCounter = Counter.builder("mysql_ch_sync_kafka_send_success_total")
                .description("Total number of successful kafka sends")
                .register(meterRegistry);

        this.kafkaSendErrorCounter = Counter.builder("mysql_ch_sync_kafka_send_errors_total")
                .description("Total number of kafka send errors")
                .register(meterRegistry);

        this.kafkaConsumeSuccessCounter = Counter.builder("mysql_ch_sync_kafka_consume_success_total")
                .description("Total number of successful kafka consumes")
                .register(meterRegistry);

        this.kafkaConsumeErrorCounter = Counter.builder("mysql_ch_sync_kafka_consume_errors_total")
                .description("Total number of kafka consume errors")
                .register(meterRegistry);

        this.clickHouseWriteSuccessCounter = Counter.builder("mysql_ch_sync_clickhouse_write_success_total")
                .description("Total number of successful ClickHouse writes")
                .register(meterRegistry);

        this.clickHouseWriteErrorCounter = Counter.builder("mysql_ch_sync_clickhouse_write_errors_total")
                .description("Total number of ClickHouse write errors")
                .register(meterRegistry);

        this.conflictResolutionCounter = Counter.builder("mysql_ch_sync_conflicts_resolved_total")
                .description("Total number of conflicts resolved")
                .register(meterRegistry);

        this.fullSyncCounter = Counter.builder("mysql_ch_sync_full_sync_total")
                .description("Total number of full sync operations")
                .register(meterRegistry);

        this.clickHouseWriteTimer = Timer.builder("mysql_ch_sync_clickhouse_write_latency_seconds")
                .description("ClickHouse write latency")
                .register(meterRegistry);

        this.syncDelayGauge = new AtomicLong(0);
        Gauge.builder("mysql_ch_sync_delay_milliseconds")
                .description("Current sync delay in milliseconds")
                .register(meterRegistry);

        this.lastSyncTimestampGauge = new AtomicLong(0);
        Gauge.builder("mysql_ch_sync_last_timestamp_seconds")
                .description("Last sync timestamp in seconds")
                .register(meterRegistry);

        this.totalRowsSyncedGauge = new AtomicLong(0);
        Gauge.builder("mysql_ch_sync_rows_total")
                .description("Total rows synced")
                .register(meterRegistry);

        log.info("Metrics service initialized");
    }

    public void incrementBinlogEventCount(String eventType) {
        binlogEventCounter.increment();
        meterRegistry.counter("mysql_ch_sync_binlog_events_total", "type", eventType.toLowerCase())
                .increment();
    }

    public void incrementCanalErrorCount() {
        canalErrorCounter.increment();
    }

    public void incrementParseErrorCount() {
        parseErrorCounter.increment();
    }

    public void incrementKafkaSendSuccessCount() {
        kafkaSendSuccessCounter.increment();
    }

    public void incrementKafkaSendErrorCount() {
        kafkaSendErrorCounter.increment();
    }

    public void incrementKafkaConsumeSuccessCount(int count) {
        kafkaConsumeSuccessCounter.increment(count);
        totalRowsSyncedGauge.addAndGet(count);
    }

    public void incrementKafkaConsumeErrorCount() {
        kafkaConsumeErrorCounter.increment();
    }

    public void incrementClickHouseWriteSuccessCount(int count) {
        clickHouseWriteSuccessCounter.increment(count);
    }

    public void incrementClickHouseWriteErrorCount() {
        clickHouseWriteErrorCounter.increment();
    }

    public void incrementConflictResolutionCount() {
        conflictResolutionCounter.increment();
    }

    public void incrementFullSyncCount() {
        fullSyncCounter.increment();
    }

    public void recordSyncDelay(long delayMs) {
        syncDelayGauge.set(delayMs);
    }

    public void recordClickHouseWriteLatency(long latencyMs) {
        clickHouseWriteTimer.record(latencyMs, java.util.concurrent.TimeUnit.MILLISECONDS);
    }

    public void recordLastSyncTimestamp(long timestampMs) {
        lastSyncTimestampGauge.set(timestampMs / 1000);
    }

    public void recordTotalRowsSynced(long count) {
        totalRowsSyncedGauge.set(count);
    }

    public void incrementFullSyncProgress(String table, long processed, long total) {
        Gauge.builder("mysql_ch_sync_full_sync_progress")
                .description("Full sync progress")
                .tag("table", table)
                .register(meterRegistry);

        Gauge.builder("mysql_ch_sync_full_sync_total_rows")
                .description("Full sync total rows")
                .tag("table", table)
                .register(meterRegistry);

        meterRegistry.gauge("mysql_ch_sync_full_sync_progress",
                java.util.Collections.emptyList(),
                g -> (double) processed / total * 100);
    }
}
