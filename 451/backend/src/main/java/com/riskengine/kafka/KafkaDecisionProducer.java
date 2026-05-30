package com.riskengine.kafka;

import com.alibaba.fastjson.JSON;
import com.riskengine.model.RiskDecision;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class KafkaDecisionProducer {

    private final KafkaTemplate<String, String> kafkaTemplate;

    @Value("${risk.engine.kafka.output-topic}")
    private String outputTopic;

    public KafkaDecisionProducer(KafkaTemplate<String, String> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    public void sendDecision(RiskDecision decision) {
        try {
            String payload = JSON.toJSONString(decision);
            kafkaTemplate.send(outputTopic, decision.getEventId(), payload)
                    .addCallback(
                            result -> log.debug("Decision sent to Kafka: eventId={}", decision.getEventId()),
                            ex -> log.error("Failed to send decision to Kafka: eventId={}", decision.getEventId(), ex)
                    );
        } catch (Exception e) {
            log.error("Error sending decision to Kafka: eventId={}", decision.getEventId(), e);
        }
    }
}
