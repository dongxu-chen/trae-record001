package com.pushplatform.push.reactive;

import com.pushplatform.entity.PushRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

import javax.annotation.PostConstruct;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class ReactivePushService {

    private static final Logger logger = LoggerFactory.getLogger(ReactivePushService.class);

    private final Map<String, ReactivePushChannel> channelMap = new ConcurrentHashMap<>();

    @Autowired
    private List<ReactivePushChannel> channels;

    @Autowired
    private BackPressureController backPressureController;

    @Autowired
    private PushMonitorService pushMonitorService;

    @PostConstruct
    public void init() {
        channels.forEach(channel -> channelMap.put(channel.getChannel(), channel));
        logger.info("ReactivePushService initialized with {} channels", channelMap.size());
    }

    public Mono<PushResult> push(PushRecord record) {
        ReactivePushChannel channel = channelMap.get(record.getChannel());
        if (channel == null) {
            return Mono.error(new IllegalArgumentException("Unknown channel: " + record.getChannel()));
        }

        return Mono.just(record)
                .flatMap(r -> pushMonitorService.monitor(r.getChannel(), channel.send(r)))
                .transformDeferred(mono -> backPressureController.applyBackPressure(record.getChannel(), mono))
                .doOnSuccess(result -> logger.debug("Push completed: {}", record.getTarget()))
                .doOnError(e -> logger.error("Push failed: {}", record.getTarget(), e));
    }

    public Flux<PushResult> batchPush(List<PushRecord> records, int concurrency) {
        return Flux.fromIterable(records)
                .parallel(concurrency)
                .runOn(Schedulers.parallel())
                .flatMap(this::push)
                .sequential();
    }

    public Flux<PushResult> pushWithRateLimit(List<PushRecord> records, int ratePerSecond) {
        long delayMs = 1000 / ratePerSecond;
        return Flux.fromIterable(records)
                .delayElements(Duration.ofMillis(delayMs))
                .flatMap(this::push, 10);
    }

    public Flux<PushResult> adaptivePush(List<PushRecord> records) {
        return Flux.fromIterable(records)
                .flatMap(record -> {
                    int factor = pushMonitorService.getDynamicConcurrencyFactor();
                    return push(record)
                            .subscribeOn(Schedulers.parallel())
                            .delaySubscription(Duration.ofMillis(Math.max(0, 100 - factor)));
                }, Math.max(1, pushMonitorService.getDynamicConcurrencyFactor() / 10));
    }
}
