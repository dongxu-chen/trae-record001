package com.dlq.platform.mq.producer;

import java.util.concurrent.CompletableFuture;

public interface MessageProducer {

    void send(String topic, Object message);

    CompletableFuture<Void> sendAsync(String topic, Object message);

    void sendWithDelay(String topic, Object message, long delayMs);

    void start();

    void stop();
}
