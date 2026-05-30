package com.distid.metrics;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import lombok.Getter;

public class IdMetrics {

    @Getter
    private final Timer snowflakeTimer;
    @Getter
    private final Timer segmentTimer;
    @Getter
    private final Counter snowflakeErrorCounter;
    @Getter
    private final Counter segmentErrorCounter;
    @Getter
    private final Counter snowflakeClockBackwardCounter;

    @Getter
    private final TDigestPercentiles snowflakePercentiles;
    @Getter
    private final TDigestPercentiles segmentPercentiles;

    public IdMetrics(MeterRegistry registry) {
        this.snowflakeTimer = Timer.builder("distid.snowflake.latency")
                .description("Snowflake ID generation latency")
                .tag("type", "snowflake")
                .register(registry);

        this.segmentTimer = Timer.builder("distid.segment.latency")
                .description("Segment ID generation latency")
                .tag("type", "segment")
                .register(registry);

        this.snowflakeErrorCounter = Counter.builder("distid.snowflake.errors")
                .description("Snowflake ID generation errors")
                .tag("type", "snowflake")
                .register(registry);

        this.segmentErrorCounter = Counter.builder("distid.segment.errors")
                .description("Segment ID generation errors")
                .tag("type", "segment")
                .register(registry);

        this.snowflakeClockBackwardCounter = Counter.builder("distid.snowflake.clock_backward")
                .description("Snowflake clock backward events")
                .tag("type", "snowflake")
                .register(registry);

        this.snowflakePercentiles = new TDigestPercentiles(registry, "distid.snowflake.percentile");
        this.segmentPercentiles = new TDigestPercentiles(registry, "distid.segment.percentile");
    }

    public void recordSnowflakeSuccess(long durationNanos) {
        double micros = durationNanos / 1000.0;
        snowflakePercentiles.record(micros);
        snowflakeTimer.record(java.time.Duration.ofNanos(durationNanos));
    }

    public void recordSegmentSuccess(long durationNanos) {
        double micros = durationNanos / 1000.0;
        segmentPercentiles.record(micros);
        segmentTimer.record(java.time.Duration.ofNanos(durationNanos));
    }

    public void recordSnowflakeError() {
        snowflakeErrorCounter.increment();
    }

    public void recordSegmentError() {
        segmentErrorCounter.increment();
    }

    public void recordSnowflakeClockBackward() {
        snowflakeClockBackwardCounter.increment();
    }
}
