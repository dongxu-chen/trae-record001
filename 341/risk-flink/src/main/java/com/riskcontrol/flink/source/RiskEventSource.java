package com.riskcontrol.flink.source;

import com.alibaba.fastjson.JSON;
import com.riskcontrol.common.model.RiskEvent;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaProducer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class RiskEventSource {

    private static final Logger logger = LoggerFactory.getLogger(RiskEventSource.class);

    private final KafkaTemplate<String, String> kafkaTemplate;

    @Autowired(required = false)
    public RiskEventSource(KafkaTemplate<String, String> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    public void sendEvent(RiskEvent event, String topic) {
        if (kafkaTemplate == null) {
            logger.debug("Kafka template not available, event not sent: {}", event.getEventId());
            return;
        }

        try {
            String eventJson = JSON.toJSONString(event);
            kafkaTemplate.send(topic, event.getUserId(), eventJson);
            logger.debug("Sent event to Kafka topic {}: {}", topic, event.getEventId());
        } catch (Exception e) {
            logger.error("Failed to send event to Kafka: {}", event.getEventId(), e);
        }
    }

    public void sendRiskEvent(RiskEvent event) {
        sendEvent(event, "risk-events");
    }
}
