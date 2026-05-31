package com.dlq.platform.mq.consumer;

public interface MessageHandler {

    void handle(String topic, Object message);

    void handleDeadLetter(String topic, Object message, Throwable throwable);
}
