package com.dlq.platform.common.dto;

import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import com.dlq.platform.common.enums.MqTypeEnum;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DeadLetterQueryDTO {

    private String id;

    private MqTypeEnum mqType;

    private String topic;

    private String queueName;

    private String messageId;

    private DeadReasonTypeEnum deadReasonType;

    private ProcessStatusEnum processStatus;

    private LocalDateTime startTime;

    private LocalDateTime endTime;

    private Integer pageNum;

    private Integer pageSize;
}
