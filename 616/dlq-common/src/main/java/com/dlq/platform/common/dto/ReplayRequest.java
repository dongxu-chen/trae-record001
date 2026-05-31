package com.dlq.platform.common.dto;

import com.dlq.platform.common.enums.MqTypeEnum;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReplayRequest {

    private List<String> messageIds;

    private MqTypeEnum mqType;

    private String targetTopic;

    private String targetQueue;

    private Boolean useOriginalDestination;

    private String operator;

    private String remark;
}
