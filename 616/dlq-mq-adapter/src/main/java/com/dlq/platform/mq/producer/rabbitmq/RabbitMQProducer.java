package com.dlq.platform.mq.producer.rabbitmq;

import com.dlq.platform.mq.config.RabbitMQConfig;
import com.dlq.platform.mq.producer.MessageProducer;
import com.dlq.platform.mq.producer.SendCallback;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageBuilder;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

@Slf4j
public class RabbitMQProducer implements MessageProducer {

    private final RabbitMQConfig config;
    private final RabbitTemplate rabbitTemplate;
    private volatile boolean running = false;
    private SendCallback sendCallback;

    public RabbitMQProducer(RabbitMQConfig config, RabbitTemplate rabbitTemplate) {
        this.config = config;
        this.rabbitTemplate = rabbitTemplate;
        initConfirmCallback();
    }

    public void setSendCallback(SendCallback sendCallback) {
        this.sendCallback = sendCallback;
    }

    private void initConfirmCallback() {
        rabbitTemplate.setConfirmCallback((CorrelationData correlationData, boolean ack, String cause) -> {
            if (correlationData == null) {
                return;
            }
            String id = correlationData.getId();
            if (ack) {
                log.debug("RabbitMQ消息确认成功, id: {}", id);
            } else {
                log.error("RabbitMQ消息确认失败, id: {}, cause: {}", id, cause);
            }
        });

        rabbitTemplate.setReturnsCallback(returned -> {
            Message message = returned.getMessage();
            String replyCode = String.valueOf(returned.getReplyCode());
            String replyText = returned.getReplyText();
            String exchange = returned.getExchange();
            String routingKey = returned.getRoutingKey();
            log.error("RabbitMQ消息被退回, exchange: {}, routingKey: {}, replyCode: {}, replyText: {}, message: {}",
                    exchange, routingKey, replyCode, replyText, new String(message.getBody(), StandardCharsets.UTF_8));
        });
    }

    @Override
    public void send(String topic, Object message) {
        try {
            CorrelationData correlationData = new CorrelationData(UUID.randomUUID().toString());
            String exchange = topic + ".exchange";
            rabbitTemplate.convertAndSend(exchange, topic, message, correlationData);
            log.debug("RabbitMQ同步发送成功, exchange: {}, routingKey: {}", exchange, topic);
            if (sendCallback != null) {
                sendCallback.onSuccess(topic, message);
            }
        } catch (Exception e) {
            log.error("RabbitMQ同步发送失败, topic: {}, message: {}", topic, message, e);
            if (sendCallback != null) {
                sendCallback.onFailure(topic, message, e);
            }
        }
    }

    @Override
    public CompletableFuture<Void> sendAsync(String topic, Object message) {
        CompletableFuture<Void> future = new CompletableFuture<>();
        try {
            CorrelationData correlationData = new CorrelationData(UUID.randomUUID().toString());
            String exchange = topic + ".exchange";

            correlationData.getFuture().whenComplete((result, throwable) -> {
                if (throwable != null) {
                    log.error("RabbitMQ异步发送失败, topic: {}, message: {}", topic, message, throwable);
                    future.completeExceptionally(throwable);
                    if (sendCallback != null) {
                        sendCallback.onFailure(topic, message, throwable);
                    }
                } else if (result.isAck()) {
                    log.debug("RabbitMQ异步发送成功, topic: {}", topic);
                    future.complete(null);
                    if (sendCallback != null) {
                        sendCallback.onSuccess(topic, message);
                    }
                } else {
                    String reason = result.getReason() != null ? result.getReason() : "未知错误";
                    Exception ex = new Exception("消息未被确认: " + reason);
                    future.completeExceptionally(ex);
                    if (sendCallback != null) {
                        sendCallback.onFailure(topic, message, ex);
                    }
                }
            });

            rabbitTemplate.convertAndSend(exchange, topic, message, correlationData);
        } catch (Exception e) {
            log.error("RabbitMQ异步发送异常, topic: {}, message: {}", topic, message, e);
            future.completeExceptionally(e);
            if (sendCallback != null) {
                sendCallback.onFailure(topic, message, e);
            }
        }
        return future;
    }

    @Override
    public void sendWithDelay(String topic, Object message, long delayMs) {
        try {
            String exchange = topic + ".exchange";
            MessageProperties properties = new MessageProperties();
            properties.setDelay((int) delayMs);
            properties.setHeader("x-delay", delayMs);

            String messageStr = message instanceof String ? (String) message : message.toString();
            Message amqpMessage = MessageBuilder.withBody(messageStr.getBytes(StandardCharsets.UTF_8))
                    .andProperties(properties)
                    .build();

            CorrelationData correlationData = new CorrelationData(UUID.randomUUID().toString());
            rabbitTemplate.convertAndSend(exchange, topic, amqpMessage, correlationData);
            log.debug("RabbitMQ延迟发送成功, exchange: {}, routingKey: {}, delayMs: {}", exchange, topic, delayMs);
            if (sendCallback != null) {
                sendCallback.onSuccess(topic, message);
            }
        } catch (Exception e) {
            log.error("RabbitMQ延迟发送失败, topic: {}, message: {}, delayMs: {}", topic, message, delayMs, e);
            if (sendCallback != null) {
                sendCallback.onFailure(topic, message, e);
            }
        }
    }

    @Override
    public void start() {
        running = true;
        log.info("RabbitMQProducer已启动");
    }

    @Override
    public void stop() {
        running = false;
        log.info("RabbitMQProducer已停止");
    }
}
