package com.dlq.platform.mq.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "dlq.mq.rocketmq")
public class RocketMQConfig {

    private String nameServer = "localhost:9876";
    private String group = "dlq-producer-group";
    private String consumerGroup = "dlq-consumer-group";
    private int consumeThreadMin = 20;
    private int consumeThreadMax = 64;
    private int consumeMessageBatchMaxSize = 1;
    private int maxReconsumeTimes = 3;
    private long consumeTimeout = 15L;
    private int sendMsgTimeout = 3000;
    private int retryTimesWhenSendFailed = 2;
    private int retryTimesWhenSendAsyncFailed = 2;
    private boolean retryAnotherBrokerWhenNotStoreOK = true;
    private String deadLetterTopicSuffix = "%DLQ%";
    private String namespace = "";

    public String buildDeadLetterTopic(String originalTopic) {
        return "%" + consumerGroup + "%" + originalTopic;
    }
}
