package com.tracing.sampling.controller;

import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.api.trace.StatusCode;
import io.opentelemetry.context.Scope;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.Random;

@RestController
@RequestMapping("/api/demo")
public class DemoController {

    private static final Logger logger = LoggerFactory.getLogger(DemoController.class);

    private final Tracer tracer;
    private final Random random;

    public DemoController(OpenTelemetry openTelemetry) {
        this.tracer = openTelemetry.getTracer("demo-controller", "1.0.0");
        this.random = new Random();
    }

    @GetMapping("/hello")
    public ResponseEntity<Map<String, Object>> hello() {
        Span span = tracer.spanBuilder("hello").startSpan();
        try (Scope scope = span.makeCurrent()) {
            span.setAttribute("http.method", "GET");
            span.setAttribute("http.route", "/api/demo/hello");
            
            Map<String, Object> response = new HashMap<>();
            response.put("message", "Hello from Distributed Tracing Sampling Tool!");
            response.put("traceId", span.getSpanContext().getTraceId());
            response.put("spanId", span.getSpanContext().getSpanId());
            response.put("sampled", span.getSpanContext().isSampled());
            
            return ResponseEntity.ok(response);
        } finally {
            span.end();
        }
    }

    @GetMapping("/fast")
    public ResponseEntity<Map<String, Object>> fastEndpoint() {
        Span span = tracer.spanBuilder("fast-endpoint").startSpan();
        try (Scope scope = span.makeCurrent()) {
            span.setAttribute("http.method", "GET");
            span.setAttribute("http.route", "/api/demo/fast");
            span.setAttribute("endpoint.type", "fast");
            
            Map<String, Object> response = new HashMap<>();
            response.put("message", "This is a fast endpoint");
            response.put("latencyMs", 0);
            response.put("traceId", span.getSpanContext().getTraceId());
            response.put("sampled", span.getSpanContext().isSampled());
            
            return ResponseEntity.ok(response);
        } finally {
            span.end();
        }
    }

    @GetMapping("/slow")
    public ResponseEntity<Map<String, Object>> slowEndpoint() {
        Span span = tracer.spanBuilder("slow-endpoint").startSpan();
        try (Scope scope = span.makeCurrent()) {
            span.setAttribute("http.method", "GET");
            span.setAttribute("http.route", "/api/demo/slow");
            span.setAttribute("endpoint.type", "slow");
            
            long delay = 600 + random.nextInt(400);
            simulateWork(delay);
            
            span.setAttribute("simulated.delay_ms", delay);
            
            Map<String, Object> response = new HashMap<>();
            response.put("message", "This is a slow endpoint (high latency)");
            response.put("latencyMs", delay);
            response.put("traceId", span.getSpanContext().getTraceId());
            response.put("sampled", span.getSpanContext().isSampled());
            response.put("note", "High latency requests should be fully sampled");
            
            return ResponseEntity.ok(response);
        } finally {
            span.end();
        }
    }

    @GetMapping("/variable")
    public ResponseEntity<Map<String, Object>> variableLatencyEndpoint(
            @RequestParam(defaultValue = "100") int minMs,
            @RequestParam(defaultValue = "1000") int maxMs) {
        
        Span span = tracer.spanBuilder("variable-latency-endpoint").startSpan();
        try (Scope scope = span.makeCurrent()) {
            span.setAttribute("http.method", "GET");
            span.setAttribute("http.route", "/api/demo/variable");
            span.setAttribute("latency.min_ms", minMs);
            span.setAttribute("latency.max_ms", maxMs);
            
            long delay = minMs + random.nextInt(Math.max(1, maxMs - minMs));
            simulateWork(delay);
            
            span.setAttribute("simulated.delay_ms", delay);
            
            Map<String, Object> response = new HashMap<>();
            response.put("message", "Variable latency endpoint");
            response.put("requestedMinMs", minMs);
            response.put("requestedMaxMs", maxMs);
            response.put("actualLatencyMs", delay);
            response.put("traceId", span.getSpanContext().getTraceId());
            response.put("sampled", span.getSpanContext().isSampled());
            
            return ResponseEntity.ok(response);
        } finally {
            span.end();
        }
    }

    @GetMapping("/error")
    public ResponseEntity<Map<String, Object>> errorEndpoint() {
        Span span = tracer.spanBuilder("error-endpoint").startSpan();
        try (Scope scope = span.makeCurrent()) {
            span.setAttribute("http.method", "GET");
            span.setAttribute("http.route", "/api/demo/error");
            span.setAttribute("error", true);
            span.setStatus(StatusCode.ERROR, "Simulated error for testing");
            
            Map<String, Object> response = new HashMap<>();
            response.put("message", "This is an error endpoint for testing");
            response.put("error", true);
            response.put("traceId", span.getSpanContext().getTraceId());
            response.put("sampled", span.getSpanContext().isSampled());
            response.put("note", "Error requests should be fully sampled");
            
            return ResponseEntity.status(500).body(response);
        } finally {
            span.end();
        }
    }

    @GetMapping("/nested")
    public ResponseEntity<Map<String, Object>> nestedSpansEndpoint() {
        Span parentSpan = tracer.spanBuilder("nested-spans-parent").startSpan();
        try (Scope parentScope = parentSpan.makeCurrent()) {
            parentSpan.setAttribute("http.method", "GET");
            parentSpan.setAttribute("http.route", "/api/demo/nested");
            parentSpan.setAttribute("operation.type", "nested-demo");
            
            Map<String, Object> childResults = new HashMap<>();
            
            for (int i = 1; i <= 3; i++) {
                Span childSpan = tracer.spanBuilder("child-operation-" + i).startSpan();
                try (Scope childScope = childSpan.makeCurrent()) {
                    childSpan.setAttribute("child.index", i);
                    long childDelay = 50 + random.nextInt(100);
                    simulateWork(childDelay);
                    childSpan.setAttribute("delay_ms", childDelay);
                    
                    childResults.put("child-" + i, Map.of(
                            "traceId", childSpan.getSpanContext().getTraceId(),
                            "spanId", childSpan.getSpanContext().getSpanId(),
                            "sampled", childSpan.getSpanContext().isSampled(),
                            "delayMs", childDelay
                    ));
                } finally {
                    childSpan.end();
                }
            }
            
            Map<String, Object> response = new HashMap<>();
            response.put("message", "Nested spans demo");
            response.put("parentTraceId", parentSpan.getSpanContext().getTraceId());
            response.put("parentSpanId", parentSpan.getSpanContext().getSpanId());
            response.put("parentSampled", parentSpan.getSpanContext().isSampled());
            response.put("childSpans", childResults);
            
            return ResponseEntity.ok(response);
        } finally {
            parentSpan.end();
        }
    }

    @PostMapping("/work")
    public ResponseEntity<Map<String, Object>> doWork(@RequestBody Map<String, Object> request) {
        String operationName = (String) request.getOrDefault("name", "work-operation");
        int durationMs = (int) request.getOrDefault("durationMs", 100);
        boolean shouldFail = (boolean) request.getOrDefault("shouldFail", false);
        
        Span span = tracer.spanBuilder(operationName).startSpan();
        try (Scope scope = span.makeCurrent()) {
            span.setAttribute("http.method", "POST");
            span.setAttribute("http.route", "/api/demo/work");
            span.setAttribute("operation.name", operationName);
            span.setAttribute("requested.duration_ms", durationMs);
            
            if (shouldFail) {
                span.setStatus(StatusCode.ERROR, "Operation failed as requested");
                span.setAttribute("error", true);
                
                Map<String, Object> response = new HashMap<>();
                response.put("message", "Work failed");
                response.put("operation", operationName);
                response.put("traceId", span.getSpanContext().getTraceId());
                response.put("sampled", span.getSpanContext().isSampled());
                
                return ResponseEntity.status(500).body(response);
            }
            
            simulateWork(durationMs);
            span.setAttribute("actual.duration_ms", durationMs);
            
            Map<String, Object> response = new HashMap<>();
            response.put("message", "Work completed");
            response.put("operation", operationName);
            response.put("durationMs", durationMs);
            response.put("traceId", span.getSpanContext().getTraceId());
            response.put("sampled", span.getSpanContext().isSampled());
            
            return ResponseEntity.ok(response);
        } finally {
            span.end();
        }
    }

    private void simulateWork(long delayMs) {
        try {
            Thread.sleep(delayMs);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            logger.warn("Sleep interrupted", e);
        }
    }
}
