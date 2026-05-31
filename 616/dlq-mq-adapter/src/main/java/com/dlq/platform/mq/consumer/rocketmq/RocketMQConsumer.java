package com.dlq.platform.mq.consumer.rocketmq;

import com.dlq.platform.mq.config.RocketMQConfig;
import com.dlq.platform.mq.consumer.AbstractMessageConsumer;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.client.apis.ClientConfiguration;
import org.apache.rocketmq.client.apis.ClientException;
import org.apache.rocketmq.client.apis.consumer.ConsumeResult;
import org.apache.rocketmq.client.apis.consumer.FilterExpression;
import org.apache.rocketmq.client.apis.consumer.FilterExpressionType;
import org.apache.rocketmq.client.apis.consumer.PushConsumer;
import org.apache.rocketmq.client.apis.consumer.PushConsumerBuilder;
import org.apache.rocketmq.client.apis.message.MessageView;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
public class RocketMQConsumer extends AbstractMessageConsumer {

    private final RocketMQConfig config;
    private PushConsumer pushConsumer;
    private final Map<String, FilterExpression> filterExpressions = new ConcurrentHashMap<>();

    public RocketMQConsumer(RocketMQConfig config) {
        this.config = config;
    }

    private void initConsumer() throws ClientException {
        ClientConfiguration clientConfiguration = ClientConfiguration.newBuilder()
                .setEndpoints(config.getNameServer())
                .enableSsl(false)
                .build();

        PushConsumerBuilder builder = PushConsumer.newBuilder()
                .setConsumerGroup(config.getConsumerGroup())
                .setClientConfiguration(clientConfiguration)
                .setConsumeThreadCount(config.getConsumeThreadMax())
                .setConsumeTimeout(Duration.ofMinutes(config.getConsumeTimeout()));

        for (String topic : subscribedTopics) {
            FilterExpression filterExpression = filterExpressions.getOrDefault(
                    topic, new FilterExpression("*", FilterExpressionType.TAG));
            builder.setSubscriptionExpressions(Map.of(topic, filterExpression));
        }

        pushConsumer = builder.setMessageListener(messageView -> {
                    try {
                        String topic = messageView.getTopic();
                        String message = decodeMessage(messageView);
                        handleMessage(topic, message);
                        return ConsumeResult.SUCCESS;
                    } catch (Exception e) {
                        log.error("RocketMQ消费异常, messageId: {}", messageView.getMessageId(), e);
                        return ConsumeResult.FAILURE;
                    }
                })
                .build();
    }

    private String decodeMessage(MessageView messageView) {
        byte[] body = messageView.getBody().array();
        return new String(body, StandardCharsets.UTF_8);
    }

    @Override
    protected void doSubscribe(String topic) {
        filterExpressions.put(topic, new FilterExpression("*", FilterExpressionType.TAG));
        if (pushConsumer != null) {
            try {
                pushConsumer.subscribe(topic, new FilterExpression("*", FilterExpressionType.TAG));
            } catch (ClientException e) {
                log.error("RocketMQ订阅失败, topic: {}", topic, e);
            }
        }
    }

    @Override
    protected void doUnsubscribe(String topic) {
        filterExpressions.remove(topic);
        if (pushConsumer != null) {
            try {
                pushConsumer.unsubscribe(topic);
            } catch (ClientException e) {
                log.error("RocketMQ取消订阅失败, topic: {}", topic, e);
            }
        }
    }

    @Override
    protected void doConsume() {
        try {
            initConsumer();
            log.info("RocketMQ消费者启动成功, 已订阅topics: {}", subscribedTopics);
        } catch (ClientException e) {
            log.error("RocketMQ消费者启动失败", e);
            running.set(false);
        }
    }

    @Override
    protected void doStop() {
        if (pushConsumer != null) {
            try {
                pushConsumer.close();
            } catch (Exception e) {
                log.error("RocketMQ消费者关闭异常", e);
            }
        }
    }

    public void setFilterExpression(String topic, String expression, FilterExpressionType type) {
        filterExpressions.put(topic, new FilterExpression(expression, type));
    }
}
