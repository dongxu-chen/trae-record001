package com.tracing.staining.controller;

import com.tracing.staining.service.DemoService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;

@Slf4j
@RestController
@RequestMapping("/api/trace")
@RequiredArgsConstructor
public class TraceDemoController {

    private final DemoService demoService;

    @GetMapping("/context")
    public ResponseEntity<Map<String, Object>> getCurrentContext() {
        log.info("Getting current trace context");
        Map<String, Object> context = demoService.getCurrentTraceContext();
        return ResponseEntity.ok(context);
    }

    @GetMapping("/stained")
    public ResponseEntity<Map<String, Object>> isStained() {
        log.info("Checking if current request is stained");
        Map<String, Object> result = new HashMap<>();
        result.put("stained", demoService.isCurrentRequestStained());
        result.put("context", demoService.getCurrentTraceContext());
        return ResponseEntity.ok(result);
    }

    @GetMapping("/async")
    public ResponseEntity<Map<String, Object>> asyncDemo() throws ExecutionException, InterruptedException {
        log.info("Starting async demo");
        CompletableFuture<Map<String, Object>> future = demoService.asyncMethodDemo();
        Map<String, Object> result = new HashMap<>();
        result.put("mainThreadContext", demoService.getCurrentTraceContext());
        result.put("asyncResult", future.get());
        return ResponseEntity.ok(result);
    }

    @GetMapping("/threadpool")
    public ResponseEntity<Map<String, Object>> threadPoolDemo() throws ExecutionException, InterruptedException {
        log.info("Starting thread pool demo");
        CompletableFuture<Map<String, Object>> future = demoService.threadPoolDemo();
        Map<String, Object> result = new HashMap<>();
        result.put("mainThreadContext", demoService.getCurrentTraceContext());
        result.put("threadPoolResult", future.get());
        return ResponseEntity.ok(result);
    }

    @GetMapping("/downstream")
    public ResponseEntity<Map<String, Object>> downstreamDemo(@RequestParam(defaultValue = "http://localhost:8080/api/trace/context") String url) {
        log.info("Starting downstream service call demo");
        Map<String, Object> result = demoService.restTemplateDemo(url);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/kafka")
    public ResponseEntity<Map<String, Object>> kafkaDemo(
            @RequestParam(defaultValue = "trace-demo-topic") String topic,
            @RequestBody Map<String, Object> message) {
        log.info("Starting Kafka message demo");
        Map<String, Object> result = demoService.sendKafkaMessage(topic, message);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/rabbit")
    public ResponseEntity<Map<String, Object>> rabbitDemo(
            @RequestParam(defaultValue = "trace-demo-exchange") String exchange,
            @RequestParam(defaultValue = "trace.demo.routing") String routingKey,
            @RequestBody Map<String, Object> message) {
        log.info("Starting RabbitMQ message demo");
        Map<String, Object> result = demoService.sendRabbitMessage(exchange, routingKey, message);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/nested")
    public ResponseEntity<Map<String, Object>> nestedDemo() {
        log.info("Starting nested call demo");
        Map<String, Object> result = demoService.nestedCallDemo();
        return ResponseEntity.ok(result);
    }

    @PostMapping("/manual")
    public ResponseEntity<Map<String, Object>> manualStainingDemo(
            @RequestParam(defaultValue = "true") boolean stainingFlag,
            @RequestParam(required = false) String stainingColor,
            @RequestParam(required = false) String userId,
            @RequestParam(required = false) String bizType) {
        log.info("Starting manual staining demo");
        Map<String, Object> result = demoService.manualStainingDemo(
                stainingFlag, stainingColor, userId, bizType);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/full-demo")
    public ResponseEntity<Map<String, Object>> fullDemo() throws ExecutionException, InterruptedException {
        log.info("Starting full trace staining demo");

        Map<String, Object> result = new HashMap<>();

        result.put("initialContext", demoService.getCurrentTraceContext());

        CompletableFuture<Map<String, Object>> asyncFuture = demoService.asyncMethodDemo();
        result.put("asyncDemo", asyncFuture.get());

        CompletableFuture<Map<String, Object>> threadPoolFuture = demoService.threadPoolDemo();
        result.put("threadPoolDemo", threadPoolFuture.get());

        result.put("nestedDemo", demoService.nestedCallDemo());

        result.put("isStained", demoService.isCurrentRequestStained());

        log.info("Full demo completed, traceId: {}",
                demoService.getCurrentTraceContext().get("traceId"));

        return ResponseEntity.ok(result);
    }

    @GetMapping("/sampler-status")
    public ResponseEntity<Map<String, Object>> getSamplerStatus() {
        log.info("Getting adaptive sampler status");
        Map<String, Object> status = demoService.getSamplerStatus();
        return ResponseEntity.ok(status);
    }
}
