package com.platform.points.mq;

import com.alibaba.fastjson.JSON;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.messaging.Message;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class PointsMQProducer {

    @Autowired
    private RocketMQTemplate rocketMQTemplate;

    @Value("${points.mq.topic.points-grant}")
    private String grantTopic;

    @Value("${points.mq.topic.points-deduct}")
    private String deductTopic;

    @Value("${points.mq.topic.points-expire}")
    private String expireTopic;

    public void sendGrantMessage(Object message) {
        sendMessage(grantTopic, message);
    }

    public void sendDeductMessage(Object message) {
        sendMessage(deductTopic, message);
    }

    public void sendExpireMessage(Object message) {
        sendMessage(expireTopic, message);
    }

    private void sendMessage(String topic, Object message) {
        String json = JSON.toJSONString(message);
        Message<String> msg = MessageBuilder.withPayload(json).build();
        try {
            rocketMQTemplate.syncSend(topic, msg);
            log.info("发送MQ消息成功, topic: {}, message: {}", topic, json);
        } catch (Exception e) {
            log.error("发送MQ消息失败, topic: {}, message: {}", topic, json, e);
            throw new RuntimeException("发送消息队列失败", e);
        }
    }
}
