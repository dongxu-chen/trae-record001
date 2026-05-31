package com.dlq.platform.common.dto;

import com.dlq.platform.common.enums.MqTypeEnum;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ArchiveRequest {

    private List<String> messageIds;

    private MqTypeEnum mqType;

    private String topic;

    private ProcessStatusEnum processStatus;

    private LocalDateTime startTime;

    private LocalDateTime endTime;

    private String archiveLocation;

    private String operator;

    private String remark;
}
