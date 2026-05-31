package com.datacheck.messagequeue;

import com.alibaba.fastjson2.JSON;
import com.datacheck.model.DiffResult;
import com.datacheck.model.WebSocketMessage;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class MessageQueueService {

    @Value("${message-queue.type:kafka}")
    private String mqType;

    private final KafkaProducerService kafkaProducerService;
    private final RocketMQProducerService rocketMQProducerService;

    @Autowired
    public MessageQueueService(ObjectProvider<KafkaProducerService> kafkaProvider,
                               ObjectProvider<RocketMQProducerService> rocketMQProvider) {
        this.kafkaProducerService = kafkaProvider.getIfAvailable();
        this.rocketMQProducerService = rocketMQProvider.getIfAvailable();
    }

    public void sendDiffToQueue(DiffResult diff) {
        try {
            WebSocketMessage<DiffResult> message = WebSocketMessage.of("DIFF", diff);
            String payload = JSON.toJSONString(message);

            switch (mqType.toLowerCase()) {
                case "kafka":
                    if (kafkaProducerService != null) {
                        kafkaProducerService.send(payload);
                    }
                    break;
                case "rocketmq":
                    if (rocketMQProducerService != null) {
                        rocketMQProducerService.send(payload);
                    }
                    break;
                default:
                    log.warn("Unknown message queue type: {}", mqType);
            }
            log.debug("Sent diff to {} queue: {}", mqType, diff.getId());
        } catch (Exception e) {
            log.error("Failed to send diff to message queue", e);
        }
    }

    public void sendCheckResultToQueue(Object result) {
        try {
            WebSocketMessage<Object> message = WebSocketMessage.of("CHECK_RESULT", result);
            String payload = JSON.toJSONString(message);

            switch (mqType.toLowerCase()) {
                case "kafka":
                    if (kafkaProducerService != null) {
                        kafkaProducerService.send(payload);
                    }
                    break;
                case "rocketmq":
                    if (rocketMQProducerService != null) {
                        rocketMQProducerService.send(payload);
                    }
                    break;
                default:
                    log.warn("Unknown message queue type: {}", mqType);
            }
            log.debug("Sent check result to {} queue", mqType);
        } catch (Exception e) {
            log.error("Failed to send check result to message queue", e);
        }
    }
}
