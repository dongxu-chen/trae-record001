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
public class ReactiveFcmChannel implements ReactivePushChannel {

    private static final Logger logger = LoggerFactory.getLogger(ReactiveFcmChannel.class);

    @Override
    public String getChannel() {
        return PushChannelEnum.FCM.getCode();
    }

    @Override
    public Mono<PushResult> send(PushRecord record) {
        return Mono.fromCallable(() -> {
                    logger.debug("Sending FCM push to: {}", record.getTarget());

                    int latency = 50 + ThreadLocalRandom.current().nextInt(200);
                    Thread.sleep(latency);

                    if (ThreadLocalRandom.current().nextInt(100) < 5) {
                        throw new RuntimeException("FCM service unavailable");
                    }

                    return PushResult.success(UUID.randomUUID().toString());
                })
                .subscribeOn(Schedulers.boundedElastic())
                .timeout(Duration.ofSeconds(10))
                .doOnSuccess(result -> logger.debug("FCM push success: {}", record.getTarget()))
                .doOnError(e -> logger.error("FCM push failed: {}", record.getTarget(), e));
    }
}
