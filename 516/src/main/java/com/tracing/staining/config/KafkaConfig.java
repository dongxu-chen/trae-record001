package com.tracing.staining.config;

import com.tracing.staining.mq.kafka.KafkaTraceConsumerInterceptor;
import com.tracing.staining.mq.kafka.KafkaTraceProducerInterceptor;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;

@Slf4j
@Configuration
@RequiredArgsConstructor
public class KafkaConfig {

    private final KafkaTraceProducerInterceptor kafkaTraceProducerInterceptor;
    private final KafkaTraceConsumerInterceptor kafkaTraceConsumerInterceptor;

    @Bean
    public KafkaTemplate<String, Object> kafkaTemplate(ProducerFactory<String, Object> producerFactory) {
        KafkaTemplate<String, Object> kafkaTemplate = new KafkaTemplate<>(producerFactory);
        kafkaTemplate.setProducerInterceptor(kafkaTraceProducerInterceptor);
        log.info("KafkaTemplate configured with trace producer interceptor");
        return kafkaTemplate;
    }
}
