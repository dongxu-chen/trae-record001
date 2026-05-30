package com.dtmonitor.api.controller;

import com.dtmonitor.trace.model.TraceDag;
import com.dtmonitor.trace.model.TraceSpan;
import com.dtmonitor.trace.service.TraceService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/trace")
@RequiredArgsConstructor
public class TraceController {

    private final TraceService traceService;

    @GetMapping("/{traceId}/spans")
    public ResponseEntity<List<TraceSpan>> getSpans(@PathVariable String traceId) {
        List<TraceSpan> spans = traceService.getTraceSpans(traceId);
        return ResponseEntity.ok(spans);
    }

    @GetMapping("/{traceId}/dag")
    public ResponseEntity<TraceDag> getDag(@PathVariable String traceId) {
        TraceDag dag = traceService.buildDag(traceId);
        return ResponseEntity.ok(dag);
    }
}
