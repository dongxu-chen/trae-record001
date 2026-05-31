package com.dlq.platform.mq.factory;

import com.dlq.platform.mq.config.KafkaConfig;
import com.dlq.platform.mq.config.RabbitMQConfig;
import com.dlq.platform.mq.config.RocketMQConfig;
import com.dlq.platform.common.enums.MqTypeEnum;
import com.dlq.platform.mq.producer.MessageProducer;
import com.dlq.platform.mq.producer.kafka.KafkaProducer;
import com.dlq.platform.mq.producer.rabbitmq.RabbitMQProducer;
import com.dlq.platform.mq.producer.rocketmq.RocketMQProducer;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class MessageProducerFactory {

    @Autowired
    private KafkaConfig kafkaConfig;

    @Autowired
    private RocketMQConfig rocketMQConfig;

    @Autowired
    private RabbitMQConfig rabbitMQConfig;

    @Autowired
    private RabbitTemplate rabbitTemplate;

    public MessageProducer createProducer(MqTypeEnum mqType) {
        if (mqType == null) {
            throw new IllegalArgumentException("MQ类型不能为空");
        }
        return switch (mqType) {
            case KAFKA -> createKafkaProducer();
            case ROCKETMQ -> createRocketMQProducer();
            case RABBITMQ -> createRabbitMQProducer();
        };
    }

    public MessageProducer createProducer(String mqTypeCode) {
        MqTypeEnum mqType = MqTypeEnum.getByCode(mqTypeCode);
        if (mqType == null) {
            throw new IllegalArgumentException("不支持的MQ类型: " + mqTypeCode);
        }
        return createProducer(mqType);
    }

    public KafkaProducer createKafkaProducer() {
        return new KafkaProducer(kafkaConfig);
    }

    public RocketMQProducer createRocketMQProducer() {
        return new RocketMQProducer(rocketMQConfig);
    }

    public RabbitMQProducer createRabbitMQProducer() {
        return new RabbitMQProducer(rabbitMQConfig, rabbitTemplate);
    }
}
