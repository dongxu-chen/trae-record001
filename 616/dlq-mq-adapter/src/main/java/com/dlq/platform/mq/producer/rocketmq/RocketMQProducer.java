package com.dlq.platform.mq.producer.rocketmq;

import com.dlq.platform.mq.config.RocketMQConfig;
import com.dlq.platform.mq.producer.MessageProducer;
import com.dlq.platform.mq.producer.SendCallback;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.client.apis.ClientConfiguration;
import org.apache.rocketmq.client.apis.ClientException;
import org.apache.rocketmq.client.apis.message.Message;
import org.apache.rocketmq.client.apis.message.MessageBuilder;
import org.apache.rocketmq.client.apis.producer.Producer;
import org.apache.rocketmq.client.apis.producer.ProducerBuilder;
import org.apache.rocketmq.client.apis.producer.SendReceipt;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.CompletableFuture;

@Slf4j
public class RocketMQProducer implements MessageProducer {

    private final RocketMQConfig config;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private Producer producer;
    private volatile boolean running = false;
    private SendCallback sendCallback;

    public RocketMQProducer(RocketMQConfig config) {
        this.config = config;
    }

    public void setSendCallback(SendCallback sendCallback) {
        this.sendCallback = sendCallback;
    }

    private void initProducer() throws ClientException {
        ClientConfiguration clientConfiguration = ClientConfiguration.newBuilder()
                .setEndpoints(config.getNameServer())
                .enableSsl(false)
                .build();

        ProducerBuilder builder = Producer.newBuilder()
                .setClientConfiguration(clientConfiguration)
                .setTopics(config.getNamespace())
                .setSendReceiptEnabled(true);

        producer = builder.build();
    }

    @Override
    public void send(String topic, Object message) {
        try {
            if (producer == null) {
                initProducer();
            }
            Message rocketMsg = buildMessage(topic, message);
            SendReceipt sendReceipt = producer.send(rocketMsg);
            log.debug("RocketMQ同步发送成功, topic: {}, messageId: {}", topic, sendReceipt.getMessageId());
            if (sendCallback != null) {
                sendCallback.onSuccess(topic, message);
            }
        } catch (Exception e) {
            log.error("RocketMQ同步发送失败, topic: {}, message: {}", topic, message, e);
            if (sendCallback != null) {
                sendCallback.onFailure(topic, message, e);
            }
        }
    }

    @Override
    public CompletableFuture<Void> sendAsync(String topic, Object message) {
        CompletableFuture<Void> future = new CompletableFuture<>();
        try {
            if (producer == null) {
                initProducer();
            }
            Message rocketMsg = buildMessage(topic, message);
            producer.sendAsync(rocketMsg)
                    .thenAccept(sendReceipt -> {
                        log.debug("RocketMQ异步发送成功, topic: {}, messageId: {}", topic, sendReceipt.getMessageId());
                        future.complete(null);
                        if (sendCallback != null) {
                            sendCallback.onSuccess(topic, message);
                        }
                    })
                    .exceptionally(throwable -> {
                        log.error("RocketMQ异步发送失败, topic: {}, message: {}", topic, message, throwable);
                        future.completeExceptionally(throwable);
                        if (sendCallback != null) {
                            sendCallback.onFailure(topic, message, throwable);
                        }
                        return null;
                    });
        } catch (Exception e) {
            log.error("RocketMQ异步发送异常, topic: {}, message: {}", topic, message, e);
            future.completeExceptionally(e);
            if (sendCallback != null) {
                sendCallback.onFailure(topic, message, e);
            }
        }
        return future;
    }

    public void sendOneway(String topic, Object message) {
        try {
            if (producer == null) {
                initProducer();
            }
            Message rocketMsg = buildMessage(topic, message);
            producer.sendOneway(rocketMsg);
            log.debug("RocketMQ单向发送成功, topic: {}", topic);
        } catch (Exception e) {
            log.error("RocketMQ单向发送失败, topic: {}, message: {}", topic, message, e);
        }
    }

    @Override
    public void sendWithDelay(String topic, Object message, long delayMs) {
        try {
            Thread.sleep(delayMs);
            send(topic, message);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("延迟发送被中断, topic: {}, message: {}", topic, message, e);
        }
    }

    private Message buildMessage(String topic, Object message) throws JsonProcessingException {
        String body = convertMessage(message);
        MessageBuilder builder = producer.getMessageBuilder();
        return builder.setTopic(topic)
                .setBody(body.getBytes(StandardCharsets.UTF_8))
                .setTag("")
                .setKeys(String.valueOf(System.currentTimeMillis()))
                .build();
    }

    private String convertMessage(Object message) throws JsonProcessingException {
        if (message instanceof String) {
            return (String) message;
        }
        return objectMapper.writeValueAsString(message);
    }

    @Override
    public void start() {
        try {
            if (producer == null) {
                initProducer();
            }
            running = true;
            log.info("RocketMQProducer已启动");
        } catch (ClientException e) {
            log.error("RocketMQProducer启动失败", e);
        }
    }

    @Override
    public void stop() {
        running = false;
        if (producer != null) {
            try {
                producer.close();
            } catch (Exception e) {
                log.error("RocketMQProducer关闭异常", e);
            }
        }
        log.info("RocketMQProducer已停止");
    }
}
