package com.dlq.platform.mq.consumer.rabbitmq;

import com.dlq.platform.mq.config.RabbitMQConfig;
import com.dlq.platform.mq.consumer.AbstractMessageConsumer;
import com.rabbitmq.client.Channel;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.core.AcknowledgeMode;
import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.DirectExchange;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.listener.SimpleMessageListenerContainer;
import org.springframework.amqp.rabbit.listener.api.ChannelAwareMessageListener;
import org.springframework.amqp.support.converter.MessageConverter;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
public class RabbitMQConsumer extends AbstractMessageConsumer {

    private final RabbitMQConfig config;
    private final ConnectionFactory connectionFactory;
    private final MessageConverter messageConverter;
    private final Map<String, SimpleMessageListenerContainer> listenerContainers = new ConcurrentHashMap<>();
    private final Map<String, Queue> queues = new ConcurrentHashMap<>();
    private final Map<String, DirectExchange> exchanges = new ConcurrentHashMap<>();
    private final Map<String, Binding> bindings = new ConcurrentHashMap<>();
    private DirectExchange deadLetterExchange;

    public RabbitMQConsumer(RabbitMQConfig config, ConnectionFactory connectionFactory, MessageConverter messageConverter) {
        this.config = config;
        this.connectionFactory = connectionFactory;
        this.messageConverter = messageConverter;
        initDeadLetterExchange();
    }

    private void initDeadLetterExchange() {
        deadLetterExchange = new DirectExchange(config.getDeadLetterExchange(), true, false);
    }

    @Override
    protected void doSubscribe(String topic) {
        try {
            createQueueAndBinding(topic);
            createListenerContainer(topic);
            log.info("RabbitMQ订阅队列成功: {}", topic);
        } catch (Exception e) {
            log.error("RabbitMQ订阅队列失败: {}", topic, e);
        }
    }

    private void createQueueAndBinding(String queueName) {
        Map<String, Object> args = new HashMap<>();
        args.put("x-dead-letter-exchange", config.getDeadLetterExchange());
        args.put("x-dead-letter-routing-key", config.getDeadLetterRoutingKey());

        Queue queue = new Queue(queueName, true, false, false, args);
        queues.put(queueName, queue);

        DirectExchange exchange = new DirectExchange(queueName + ".exchange", true, false);
        exchanges.put(queueName, exchange);

        Binding binding = BindingBuilder.bind(queue).to(exchange).with(queueName);
        bindings.put(queueName, binding);

        String dlqName = queueName + config.getDeadLetterQueueSuffix();
        Queue dlq = new Queue(dlqName, true, false, false);
        queues.put(dlqName, dlq);

        Binding dlqBinding = BindingBuilder.bind(dlq).to(deadLetterExchange).with(config.getDeadLetterRoutingKey());
        bindings.put(dlqName, dlqBinding);
    }

    private void createListenerContainer(String queueName) {
        SimpleMessageListenerContainer container = new SimpleMessageListenerContainer();
        container.setConnectionFactory(connectionFactory);
        container.setQueueNames(queueName);
        container.setConcurrentConsumers(config.getConcurrentConsumers());
        container.setMaxConcurrentConsumers(config.getMaxConcurrentConsumers());
        container.setPrefetchCount(config.getConsumerPrefetchCount());
        container.setAcknowledgeMode(config.isAcknowledgeModeManual() ? AcknowledgeMode.MANUAL : AcknowledgeMode.AUTO);
        container.setMessageListener(new ChannelAwareMessageListener() {
            @Override
            public void onMessage(Message message, Channel channel) throws Exception {
                long deliveryTag = message.getMessageProperties().getDeliveryTag();
                try {
                    Object messageBody = messageConverter.fromMessage(message);
                    handleMessage(queueName, messageBody);
                    if (config.isAcknowledgeModeManual()) {
                        channel.basicAck(deliveryTag, false);
                    }
                } catch (Exception e) {
                    log.error("RabbitMQ消费异常, queue: {}, deliveryTag: {}", queueName, deliveryTag, e);
                    if (config.isAcknowledgeModeManual()) {
                        channel.basicNack(deliveryTag, false, false);
                    }
                    MessageProperties properties = message.getMessageProperties();
                    handleDeadLetter(queueName, messageConverter.fromMessage(message), e);
                }
            }
        });
        listenerContainers.put(queueName, container);
    }

    @Override
    protected void doUnsubscribe(String topic) {
        SimpleMessageListenerContainer container = listenerContainers.remove(topic);
        if (container != null) {
            container.stop();
            container.destroy();
            log.info("RabbitMQ取消订阅队列成功: {}", topic);
        }
    }

    @Override
    protected void doConsume() {
        for (String topic : subscribedTopics) {
            SimpleMessageListenerContainer container = listenerContainers.get(topic);
            if (container != null && !container.isRunning()) {
                container.start();
                log.info("RabbitMQ消费容器启动成功, queue: {}", topic);
            }
        }
    }

    @Override
    protected void doStop() {
        for (Map.Entry<String, SimpleMessageListenerContainer> entry : listenerContainers.entrySet()) {
            SimpleMessageListenerContainer container = entry.getValue();
            if (container.isRunning()) {
                container.stop();
                log.info("RabbitMQ消费容器停止成功, queue: {}", entry.getKey());
            }
        }
    }

    public DirectExchange getDeadLetterExchange() {
        return deadLetterExchange;
    }

    public Queue getQueue(String queueName) {
        return queues.get(queueName);
    }

    public DirectExchange getExchange(String exchangeName) {
        return exchanges.get(exchangeName);
    }

    public Binding getBinding(String queueName) {
        return bindings.get(queueName);
    }
}
