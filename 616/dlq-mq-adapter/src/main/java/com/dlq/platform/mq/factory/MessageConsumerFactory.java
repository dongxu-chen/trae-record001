package com.dlq.platform.mq.factory;

import com.dlq.platform.mq.config.KafkaConfig;
import com.dlq.platform.mq.config.RabbitMQConfig;
import com.dlq.platform.mq.config.RocketMQConfig;
import com.dlq.platform.mq.consumer.MessageConsumer;
import com.dlq.platform.mq.consumer.kafka.KafkaConsumer;
import com.dlq.platform.mq.consumer.rabbitmq.RabbitMQConsumer;
import com.dlq.platform.mq.consumer.rocketmq.RocketMQConsumer;
import com.dlq.platform.common.enums.MqTypeEnum;
import com.dlq.platform.mq.producer.kafka.KafkaProducer;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class MessageConsumerFactory {

    @Autowired
    private KafkaConfig kafkaConfig;

    @Autowired
    private RocketMQConfig rocketMQConfig;

    @Autowired
    private RabbitMQConfig rabbitMQConfig;

    @Autowired
    private ConnectionFactory rabbitConnectionFactory;

    @Autowired
    private MessageConverter jsonMessageConverter;

    @Autowired
    private KafkaProducer kafkaDeadLetterProducer;

    public MessageConsumer createConsumer(MqTypeEnum mqType) {
        if (mqType == null) {
            throw new IllegalArgumentException("MQ类型不能为空");
        }
        return switch (mqType) {
            case KAFKA -> createKafkaConsumer();
            case ROCKETMQ -> createRocketMQConsumer();
            case RABBITMQ -> createRabbitMQConsumer();
        };
    }

    public MessageConsumer createConsumer(String mqTypeCode) {
        MqTypeEnum mqType = MqTypeEnum.getByCode(mqTypeCode);
        if (mqType == null) {
            throw new IllegalArgumentException("不支持的MQ类型: " + mqTypeCode);
        }
        return createConsumer(mqType);
    }

    private KafkaConsumer createKafkaConsumer() {
        return new KafkaConsumer(kafkaConfig, kafkaDeadLetterProducer);
    }

    private RocketMQConsumer createRocketMQConsumer() {
        return new RocketMQConsumer(rocketMQConfig);
    }

    private RabbitMQConsumer createRabbitMQConsumer() {
        return new RabbitMQConsumer(rabbitMQConfig, rabbitConnectionFactory, jsonMessageConverter);
    }
}
