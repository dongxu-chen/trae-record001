package com.distid.metrics;

import com.distid.snowflake.NtpTimeSynchronizer;
import com.distid.snowflake.SnowflakeIdService;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;

import javax.annotation.PostConstruct;
import java.util.Optional;

@Configuration
public class CustomMetricsExporter {

    private final SnowflakeIdService snowflakeIdService;
    private final Optional<NtpTimeSynchronizer> ntpTimeSynchronizer;
    private final MeterRegistry meterRegistry;

    @Autowired(required = false)
    public CustomMetricsExporter(SnowflakeIdService snowflakeIdService,
                                    Optional<NtpTimeSynchronizer> ntpTimeSynchronizer,
                                    MeterRegistry meterRegistry) {
        this.snowflakeIdService = snowflakeIdService;
        this.ntpTimeSynchronizer = ntpTimeSynchronizer;
        this.meterRegistry = meterRegistry;
    }

    @PostConstruct
    public void registerMetrics() {
        String podName = snowflakeIdService.getPodName() != null ? snowflakeIdService.getPodName() : "unknown";

        Gauge.builder("distid_snowflake_worker_id", () -> (double) snowflakeIdService.getWorkerId())
                .description("Snowflake worker ID assigned to this instance")
                .tag("pod", podName)
                .register(meterRegistry);

        Gauge.builder("distid_ntp_offset_ms", () -> (double) getNtpOffset())
                .description("NTP time offset in milliseconds")
                .tag("source", "ntp")
                .register(meterRegistry);

        Gauge.builder("distid_ntp_synchronized", () -> isNtpSynchronized() ? 1.0 : 0.0)
                .description("NTP synchronization status (1=OK, 0=FAILED)")
                .register(meterRegistry);

        Gauge.builder("distid_snowflake_worker_info", () -> 1.0)
                .description("Snowflake worker info gauge for label tracking")
                .tag("worker_id", String.valueOf(snowflakeIdService.getWorkerId()))
                .tag("pod", podName)
                .register(meterRegistry);
    }

    private long getNtpOffset() {
        return ntpTimeSynchronizer.map(NtpTimeSynchronizer::getNetworkOffsetMs).orElse(0L);
    }

    private boolean isNtpSynchronized() {
        return ntpTimeSynchronizer.map(NtpTimeSynchronizer::isSynchronizedOk).orElse(false);
    }
}
