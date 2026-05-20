package com.pushplatform.controller.reactive;

import com.pushplatform.entity.PushRecord;
import com.pushplatform.push.reactive.BackPressureController;
import com.pushplatform.push.reactive.PushMonitorService;
import com.pushplatform.push.reactive.PushResult;
import com.pushplatform.push.reactive.ReactivePushService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v2/push")
public class ReactivePushController {

    @Autowired
    private ReactivePushService reactivePushService;

    @Autowired
    private PushMonitorService pushMonitorService;

    @Autowired
    private BackPressureController backPressureController;

    @PostMapping("/single")
    public Mono<PushResult> singlePush(@RequestBody PushRecord record) {
        return reactivePushService.push(record);
    }

    @PostMapping(value = "/batch", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<PushResult> batchPush(@RequestBody List<PushRecord> records,
                                       @RequestParam(defaultValue = "10") int concurrency) {
        return reactivePushService.batchPush(records, concurrency)
                .delayElements(Duration.ofMillis(10));
    }

    @PostMapping("/rate-limited")
    public Flux<PushResult> rateLimitedPush(@RequestBody List<PushRecord> records,
                                             @RequestParam(defaultValue = "100") int ratePerSecond) {
        return reactivePushService.pushWithRateLimit(records, ratePerSecond);
    }

    @PostMapping("/adaptive")
    public Flux<PushResult> adaptivePush(@RequestBody List<PushRecord> records) {
        return reactivePushService.adaptivePush(records);
    }

    @GetMapping("/stats/{channel}")
    public Mono<Map<String, Object>> getChannelStats(@PathVariable String channel) {
        return Mono.just(pushMonitorService.getChannelStats(channel));
    }

    @GetMapping("/stats/all")
    public Mono<Map<String, Map<String, Object>>> getAllChannelStats() {
        return Mono.just(Map.of(
                "fcm", pushMonitorService.getChannelStats("fcm"),
                "apns", pushMonitorService.getChannelStats("apns"),
                "websocket", pushMonitorService.getChannelStats("websocket")
        ));
    }

    @GetMapping("/circuit-breaker/{channel}")
    public Mono<Map<String, Object>> getCircuitBreakerState(@PathVariable String channel) {
        return Mono.just(Map.of(
                "state", backPressureController.getCircuitBreakerState(channel).name(),
                "inflight", backPressureController.getInflightRequests(channel)
        ));
    }

    @PostMapping("/concurrency/{channel}")
    public Mono<Map<String, Object>> updateConcurrencyLimit(@PathVariable String channel,
                                                              @RequestParam int limit) {
        backPressureController.updateConcurrencyLimit(channel, limit);
        return Mono.just(Map.of(
                "channel", channel,
                "newLimit", limit,
                "status", "updated"
        ));
    }

    @GetMapping("/health")
    public Mono<Map<String, Object>> healthCheck() {
        return Mono.just(Map.of(
                "status", "UP",
                "timestamp", System.currentTimeMillis(),
                "concurrencyFactor", pushMonitorService.getDynamicConcurrencyFactor()
        ));
    }
}
