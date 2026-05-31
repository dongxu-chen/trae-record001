package com.dlq.platform.mq.consumer;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;

@Slf4j
public abstract class AbstractMessageConsumer implements MessageConsumer {

    protected final Set<String> subscribedTopics = ConcurrentHashMap.newKeySet();
    protected final AtomicBoolean running = new AtomicBoolean(false);
    protected final ObjectMapper objectMapper = new ObjectMapper();
    protected volatile MessageHandler messageHandler;
    protected int maxRetryTimes = 3;

    @Override
    public void subscribe(String topic) {
        if (StringUtils.isBlank(topic)) {
            return;
        }
        subscribedTopics.add(topic);
        doSubscribe(topic);
        log.info("订阅topic成功: {}", topic);
    }

    @Override
    public void unsubscribe(String topic) {
        if (StringUtils.isBlank(topic)) {
            return;
        }
        subscribedTopics.remove(topic);
        doUnsubscribe(topic);
        log.info("取消订阅topic成功: {}", topic);
    }

    @Override
    public void consume(MessageHandler handler) {
        if (handler == null) {
            throw new IllegalArgumentException("消息处理器不能为空");
        }
        this.messageHandler = handler;
        if (running.compareAndSet(false, true)) {
            doConsume();
            log.info("启动消息消费成功, 已订阅topics: {}", subscribedTopics);
        }
    }

    @Override
    public void start() {
        if (messageHandler == null) {
            throw new IllegalStateException("请先设置消息处理器");
        }
        if (running.compareAndSet(false, true)) {
            doConsume();
            log.info("启动消息消费成功, 已订阅topics: {}", subscribedTopics);
        }
    }

    @Override
    public void stop() {
        if (running.compareAndSet(true, false)) {
            doStop();
            log.info("停止消息消费成功");
        }
    }

    protected Object preprocessMessage(String topic, Object message) {
        if (message == null) {
            return null;
        }
        log.debug("预处理消息, topic: {}, 原始消息: {}", topic, message);
        return message;
    }

    protected void handleMessage(String topic, Object message) {
        try {
            Object processedMessage = preprocessMessage(topic, message);
            if (processedMessage == null) {
                return;
            }
            messageHandler.handle(topic, processedMessage);
        } catch (Exception e) {
            log.error("处理消息异常, topic: {}, message: {}", topic, message, e);
            handleDeadLetter(topic, message, e);
        }
    }

    protected void handleDeadLetter(String topic, Object message, Throwable throwable) {
        try {
            messageHandler.handleDeadLetter(topic, message, throwable);
        } catch (Exception ex) {
            log.error("死信处理异常, topic: {}, message: {}", topic, message, ex);
        }
    }

    protected boolean isRunning() {
        return running.get();
    }

    protected Set<String> getSubscribedTopics() {
        return subscribedTopics;
    }

    protected abstract void doSubscribe(String topic);

    protected abstract void doUnsubscribe(String topic);

    protected abstract void doConsume();

    protected abstract void doStop();
}
