package com.dlq.platform.mq.config;

import com.dlq.platform.mq.producer.kafka.KafkaProducer;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.Configuration;

@Configuration
@ComponentScan(basePackages = "com.dlq.platform.mq")
public class MqAdapterAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public KafkaProducer kafkaDeadLetterProducer(KafkaConfig kafkaConfig) {
        return new KafkaProducer(kafkaConfig);
    }
}
