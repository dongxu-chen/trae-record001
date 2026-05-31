package com.dlq.platform.mq.producer;

public interface SendCallback {

    void onSuccess(String topic, Object message);

    void onFailure(String topic, Object message, Throwable throwable);
}
