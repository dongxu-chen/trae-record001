package com.pushplatform.push.reactive;

import com.pushplatform.common.enums.PushChannelEnum;
import com.pushplatform.entity.PushRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

import java.time.Duration;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

@Component
public class ReactiveApnsChannel implements ReactivePushChannel {

    private static final Logger logger = LoggerFactory.getLogger(ReactiveApnsChannel.class);

    @Override
    public String getChannel() {
        return PushChannelEnum.APNS.getCode();
    }

    @Override
    public Mono<PushResult> send(PushRecord record) {
        return Mono.fromCallable(() -> {
                    logger.debug("Sending APNS push to: {}", record.getTarget());

                    int latency = 30 + ThreadLocalRandom.current().nextInt(150);
                    Thread.sleep(latency);

                    if (ThreadLocalRandom.current().nextInt(100) < 3) {
                        throw new RuntimeException("APNS service timeout");
                    }

                    return PushResult.success(UUID.randomUUID().toString());
                })
                .subscribeOn(Schedulers.boundedElastic())
                .timeout(Duration.ofSeconds(8))
                .doOnSuccess(result -> logger.debug("APNS push success: {}", record.getTarget()))
                .doOnError(e -> logger.error("APNS push failed: {}", record.getTarget(), e));
    }
}
