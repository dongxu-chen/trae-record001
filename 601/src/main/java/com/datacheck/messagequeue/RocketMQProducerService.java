package com.datacheck.messagequeue;

import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.client.producer.DefaultMQProducer;
import org.apache.rocketmq.client.producer.SendResult;
import org.apache.rocketmq.common.message.Message;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import java.nio.charset.StandardCharsets;

@Slf4j
@Service
@ConditionalOnProperty(name = "message-queue.type", havingValue = "rocketmq")
public class RocketMQProducerService {

    @Value("${message-queue.rocketmq.namesrv-addr:localhost:9876}")
    private String namesrvAddr;

    @Value("${message-queue.rocketmq.producer-group:data-sync-producer-group}")
    private String producerGroup;

    @Value("${message-queue.rocketmq.topic:data-sync-topic}")
    private String topic;

    private DefaultMQProducer producer;

    @PostConstruct
    public void init() {
        try {
            producer = new DefaultMQProducer(producerGroup);
            producer.setNamesrvAddr(namesrvAddr);
            producer.setRetryTimesWhenSendFailed(3);
            producer.start();
            log.info("RocketMQ producer initialized, namesrv: {}", namesrvAddr);
        } catch (Exception e) {
            log.warn("Failed to initialize RocketMQ producer, will use fallback mode", e);
        }
    }

    public void send(String message) {
        if (producer == null) {
            log.debug("RocketMQ producer not available, skipping message: {}", message);
            return;
        }
        try {
            Message msg = new Message(topic, message.getBytes(StandardCharsets.UTF_8));
            SendResult result = producer.send(msg);
            log.debug("RocketMQ message sent successfully, msgId: {}", result.getMsgId());
        } catch (Exception e) {
            log.error("Error sending RocketMQ message", e);
        }
    }

    @PreDestroy
    public void destroy() {
        if (producer != null) {
            producer.shutdown();
            log.info("RocketMQ producer closed");
        }
    }
}
