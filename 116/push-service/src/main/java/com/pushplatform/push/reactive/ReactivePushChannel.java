package com.pushplatform.push.reactive;

import com.pushplatform.entity.PushRecord;
import reactor.core.publisher.Mono;

public interface ReactivePushChannel {

    String getChannel();

    Mono<PushResult> send(PushRecord record);

    default Mono<PushResult> sendWithRetry(PushRecord record, int maxRetries) {
        return send(record)
                .retry(maxRetries, throwable -> isRetryable(throwable))
                .onErrorResume(e -> Mono.just(PushResult.fail(e.getMessage())));
    }

    default boolean isRetryable(Throwable throwable) {
        String message = throwable.getMessage();
        return message != null && (
                message.contains("timeout") ||
                message.contains("503") ||
                message.contains("429") ||
                message.contains("Connection reset")
        );
    }
}
