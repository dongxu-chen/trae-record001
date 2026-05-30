package com.distid.controller;

import com.distid.ha.CrossDcSyncService;
import com.distid.ha.DatacenterNode;
import com.distid.ha.DatacenterRegistry;
import com.distid.ha.FailoverManager;
import com.distid.readable.IdFormatterService;
import com.distid.readable.FormattedId;
import com.distid.segment.SegmentIdService;
import com.distid.snowflake.ClockBackwardException;
import com.distid.snowflake.SnowflakeIdService;
import com.distid.metrics.IdMetrics;
import com.distid.tracing.IdLifecycleTracker;
import com.distid.tracing.TraceContext;
import com.distid.tracing.TraceContextInterceptor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@Slf4j
@RestController
@RequestMapping("/api/id/snowflake")
public class SnowflakeController {

    private final SnowflakeIdService snowflakeIdService;
    private final IdMetrics metrics;
    private final IdFormatterService formatter;
    private final IdLifecycleTracker tracker;

    public SnowflakeController(SnowflakeIdService snowflakeIdService, IdMetrics metrics,
                                IdFormatterService formatter, IdLifecycleTracker tracker) {
        this.snowflakeIdService = snowflakeIdService;
        this.metrics = metrics;
        this.formatter = formatter;
        this.tracker = tracker;
    }

    @GetMapping
    public ResponseEntity<Map<String, Object>> nextId(
            @RequestParam(value = "bizTag", required = false) String bizTag) {
        try {
            long id = snowflakeIdService.generateId();
            FormattedId formatted = formatter.formatSnowflake(id, bizTag);

            TraceContext ctx = TraceContextInterceptor.currentContext();
            tracker.onGenerated(id, formatted.getReadableId(), "snowflake", bizTag, ctx);

            Map<String, Object> result = new HashMap<>();
            result.put("id", id);
            result.put("readableId", formatted.getReadableId());
            result.put("base62Id", formatted.getBase62Id());
            result.put("workerId", snowflakeIdService.getWorkerId());
            result.put("podName", snowflakeIdService.getPodName());
            result.put("mode", "snowflake");
            if (bizTag != null) result.put("bizTag", bizTag);
            return ResponseEntity.ok(result);
        } catch (ClockBackwardException e) {
            log.error("Clock backward detected: {}", e.getMessage());
            Map<String, Object> error = new HashMap<>();
            error.put("error", "CLOCK_BACKWARD");
            error.put("message", e.getMessage());
            error.put("backwardMs", e.getBackwardMs());
            return ResponseEntity.status(503).body(error);
        } catch (Exception e) {
            log.error("Failed to generate snowflake ID", e);
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.internalServerError().body(error);
        }
    }

    @GetMapping("/info")
    public ResponseEntity<Map<String, Object>> info() {
        Map<String, Object> info = new HashMap<>();
        info.put("workerId", snowflakeIdService.getWorkerId());
        info.put("podName", snowflakeIdService.getPodName());
        info.put("ntpSynchronized", snowflakeIdService.isNtpSynchronized());
        info.put("ntpOffsetMs", snowflakeIdService.getNtpOffsetMs());
        info.put("mode", "snowflake");
        return ResponseEntity.ok(info);
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> stats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("workerId", snowflakeIdService.getWorkerId());
        stats.put("podName", snowflakeIdService.getPodName());
        stats.put("ntpSynchronized", snowflakeIdService.isNtpSynchronized());
        stats.put("ntpOffsetMs", snowflakeIdService.getNtpOffsetMs());

        Map<String, Double> percentiles = new HashMap<>();
        percentiles.put("p50", metrics.getSnowflakePercentiles().getPercentile(0.50));
        percentiles.put("p75", metrics.getSnowflakePercentiles().getPercentile(0.75));
        percentiles.put("p90", metrics.getSnowflakePercentiles().getPercentile(0.90));
        percentiles.put("p95", metrics.getSnowflakePercentiles().getPercentile(0.95));
        percentiles.put("p99", metrics.getSnowflakePercentiles().getPercentile(0.99));
        percentiles.put("p999", metrics.getSnowflakePercentiles().getPercentile(0.999));
        stats.put("latencyMicros", percentiles);
        return ResponseEntity.ok(stats);
    }
}
