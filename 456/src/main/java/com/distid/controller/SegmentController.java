package com.distid.controller;

import com.distid.readable.FormattedId;
import com.distid.readable.IdFormatterService;
import com.distid.segment.SegmentIdService;
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
@RequestMapping("/api/id/segment")
public class SegmentController {

    private final SegmentIdService segmentIdService;
    private final IdMetrics metrics;
    private final IdFormatterService formatter;
    private final IdLifecycleTracker tracker;

    public SegmentController(SegmentIdService segmentIdService, IdMetrics metrics,
                              IdFormatterService formatter, IdLifecycleTracker tracker) {
        this.segmentIdService = segmentIdService;
        this.metrics = metrics;
        this.formatter = formatter;
        this.tracker = tracker;
    }

    @GetMapping("/{bizTag}")
    public ResponseEntity<Map<String, Object>> nextId(@PathVariable String bizTag) {
        long start = System.nanoTime();
        try {
            long id = segmentIdService.nextId(bizTag);
            metrics.recordSegmentSuccess(System.nanoTime() - start);

            FormattedId formatted = formatter.formatSegment(id, bizTag);
            TraceContext ctx = TraceContextInterceptor.currentContext();
            tracker.onGenerated(id, formatted.getReadableId(), "segment", bizTag, ctx);

            Map<String, Object> result = new HashMap<>();
            result.put("id", id);
            result.put("readableId", formatted.getReadableId());
            result.put("base62Id", formatted.getBase62Id());
            result.put("bizTag", bizTag);
            result.put("mode", "segment");
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            metrics.recordSegmentError();
            log.error("Failed to generate segment ID for bizTag={}", bizTag, e);
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            error.put("bizTag", bizTag);
            return ResponseEntity.internalServerError().body(error);
        }
    }

    @GetMapping("/{bizTag}/batch")
    public ResponseEntity<Map<String, Object>> nextIds(@PathVariable String bizTag,
                                                        @RequestParam(defaultValue = "100") int count) {
        long start = System.nanoTime();
        try {
            if (count <= 0 || count > 10000) {
                Map<String, Object> error = new HashMap<>();
                error.put("error", "count must be between 1 and 10000");
                return ResponseEntity.badRequest().body(error);
            }
            List<Long> ids = segmentIdService.nextIds(bizTag, count);
            metrics.recordSegmentSuccess(System.nanoTime() - start);

            TraceContext ctx = TraceContextInterceptor.currentContext();
            List<Map<String, Object>> formattedIds = new ArrayList<>();
            for (Long id : ids) {
                FormattedId formatted = formatter.formatSegment(id, bizTag);
                tracker.onGenerated(id, formatted.getReadableId(), "segment", bizTag, ctx);
                Map<String, Object> item = new HashMap<>();
                item.put("id", id);
                item.put("readableId", formatted.getReadableId());
                item.put("base62Id", formatted.getBase62Id());
                formattedIds.add(item);
            }

            Map<String, Object> result = new HashMap<>();
            result.put("ids", formattedIds);
            result.put("count", ids.size());
            result.put("bizTag", bizTag);
            result.put("mode", "segment");
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            metrics.recordSegmentError();
            log.error("Failed to generate batch segment IDs for bizTag={}", bizTag, e);
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            error.put("bizTag", bizTag);
            return ResponseEntity.internalServerError().body(error);
        }
    }
}
