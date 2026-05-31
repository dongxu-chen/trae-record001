package com.dlq.platform.mq.producer.kafka;

import com.dlq.platform.mq.config.KafkaConfig;
import com.dlq.platform.mq.producer.MessageProducer;
import com.dlq.platform.mq.producer.SendCallback;
import com.fasterxml.jackson.core.JsonProcessingException;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.producer.Callback;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;

import java.util.Properties;
import java.util.concurrent.CompletableFuture;

@Slf4j
public class KafkaProducer implements MessageProducer {

    private final KafkaConfig config;
    private org.apache.kafka.clients.producer.KafkaProducer<String, String> producer;
    private volatile boolean running = false;
    private SendCallback sendCallback;

    public KafkaProducer(KafkaConfig config) {
        this.config = config;
        initProducer();
    }

    private void initProducer() {
        Properties props = config.buildProducerProperties();
        producer = new org.apache.kafka.clients.producer.KafkaProducer<>(props);
    }

    public void setSendCallback(SendCallback sendCallback) {
        this.sendCallback = sendCallback;
    }

    @Override
    public void send(String topic, Object message) {
        sendAsync(topic, message).whenComplete((v, e) -> {
            if (e != null) {
                log.error("Kafka同步发送失败, topic: {}, message: {}", topic, message, e);
                if (sendCallback != null) {
                    sendCallback.onFailure(topic, message, e);
                }
            } else {
                if (sendCallback != null) {
                    sendCallback.onSuccess(topic, message);
                }
            }
        });
    }

    @Override
    public CompletableFuture<Void> sendAsync(String topic, Object message) {
        CompletableFuture<Void> future = new CompletableFuture<>();
        try {
            String messageStr = convertMessage(message);
            ProducerRecord<String, String> record = new ProducerRecord<>(topic, messageStr);

            producer.send(record, new Callback() {
                @Override
                public void onCompletion(RecordMetadata metadata, Exception exception) {
                    if (exception != null) {
                        log.error("Kafka异步发送失败, topic: {}, partition: {}, offset: {}",
                                topic, metadata != null ? metadata.partition() : -1,
                                metadata != null ? metadata.offset() : -1, exception);
                        future.completeExceptionally(exception);
                        if (sendCallback != null) {
                            sendCallback.onFailure(topic, message, exception);
                        }
                    } else {
                        log.debug("Kafka异步发送成功, topic: {}, partition: {}, offset: {}",
                                topic, metadata.partition(), metadata.offset());
                        future.complete(null);
                        if (sendCallback != null) {
                            sendCallback.onSuccess(topic, message);
                        }
                    }
                }
            });
        } catch (Exception e) {
            log.error("Kafka发送消息异常, topic: {}, message: {}", topic, message, e);
            future.completeExceptionally(e);
            if (sendCallback != null) {
                sendCallback.onFailure(topic, message, e);
            }
        }
        return future;
    }

    @Override
    public void sendWithDelay(String topic, Object message, long delayMs) {
        CompletableFuture<Void> future = new CompletableFuture<>();
        try {
            Thread.sleep(delayMs);
            sendAsync(topic, message).whenComplete((v, e) -> {
                if (e != null) {
                    future.completeExceptionally(e);
                } else {
                    future.complete(null);
                }
            });
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("延迟发送被中断, topic: {}, message: {}", topic, message, e);
            future.completeExceptionally(e);
        }
    }

    private String convertMessage(Object message) throws JsonProcessingException {
        if (message instanceof String) {
            return (String) message;
        }
        return new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(message);
    }

    @Override
    public void start() {
        running = true;
        log.info("KafkaProducer已启动");
    }

    @Override
    public void stop() {
        running = false;
        if (producer != null) {
            producer.flush();
            producer.close();
        }
        log.info("KafkaProducer已停止");
    }

    public void flush() {
        if (producer != null) {
            producer.flush();
        }
    }
}
