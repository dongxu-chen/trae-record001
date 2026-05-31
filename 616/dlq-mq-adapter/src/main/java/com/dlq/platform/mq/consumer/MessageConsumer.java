package com.dlq.platform.mq.consumer;

public interface MessageConsumer {

    void consume(MessageHandler handler);

    void subscribe(String topic);

    void unsubscribe(String topic);

    void start();

    void stop();
}
