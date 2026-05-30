package com.riskengine.kafka;

import com.alibaba.fastjson.JSON;
import com.riskengine.model.RiskEvent;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

import java.util.List;

@Slf4j
@Component
public class RiskEventConsumer {

    private final KafkaEventProcessor eventProcessor;

    public RiskEventConsumer(KafkaEventProcessor eventProcessor) {
        this.eventProcessor = eventProcessor;
    }

    @KafkaListener(topics = "${risk.engine.kafka.input-topic}", groupId = "${spring.kafka.consumer.group-id}")
    public void consume(List<ConsumerRecord<String, String>> records, Acknowledgment ack) {
        log.debug("Received {} risk events from Kafka", records.size());

        for (ConsumerRecord<String, String> record : records) {
            try {
                RiskEvent event = JSON.parseObject(record.value(), RiskEvent.class);
                if (event != null) {
                    eventProcessor.process(event);
                }
            } catch (Exception e) {
                log.error("Failed to process risk event: {}", record.value(), e);
            }
        }

        try {
            ack.acknowledge();
        } catch (Exception e) {
            log.error("Failed to acknowledge Kafka offset", e);
        }
    }
}
