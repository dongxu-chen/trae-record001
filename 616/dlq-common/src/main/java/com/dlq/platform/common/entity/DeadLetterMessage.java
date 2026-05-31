package com.dlq.platform.common.entity;

import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import com.dlq.platform.common.enums.MqTypeEnum;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DeadLetterMessage {

    private String id;

    private MqTypeEnum mqType;

    private String topic;

    private String queueName;

    private String messageId;

    private String messageBody;

    private Map<String, Object> headers;

    private String deadReason;

    private DeadReasonTypeEnum deadReasonType;

    private String stackTrace;

    private String originalTopic;

    private String originalQueue;

    private Integer retryCount;

    private ProcessStatusEnum processStatus;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
