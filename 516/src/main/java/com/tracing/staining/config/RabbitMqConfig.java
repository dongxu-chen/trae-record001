package com.tracing.staining.config;

import com.tracing.staining.mq.rabbit.RabbitTraceMessagePostProcessor;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Slf4j
@Configuration
@RequiredArgsConstructor
public class RabbitMqConfig {

    private final RabbitTraceMessagePostProcessor rabbitTraceMessagePostProcessor;

    @Bean
    public RabbitTemplate rabbitTemplate(org.springframework.amqp.rabbit.connection.ConnectionFactory connectionFactory) {
        RabbitTemplate rabbitTemplate = new RabbitTemplate(connectionFactory);
        rabbitTemplate.addBeforePublishPostProcessors(rabbitTraceMessagePostProcessor);
        log.info("RabbitTemplate configured with trace message post processor");
        return rabbitTemplate;
    }
}
