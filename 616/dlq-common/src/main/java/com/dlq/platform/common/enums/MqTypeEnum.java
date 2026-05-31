package com.dlq.platform.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum MqTypeEnum {

    KAFKA("KAFKA", "Kafka消息队列"),
    ROCKETMQ("ROCKETMQ", "RocketMQ消息队列"),
    RABBITMQ("RABBITMQ", "RabbitMQ消息队列");

    private final String code;
    private final String desc;

    public static MqTypeEnum getByCode(String code) {
        for (MqTypeEnum type : values()) {
            if (type.getCode().equalsIgnoreCase(code)) {
                return type;
            }
        }
        return null;
    }
}
