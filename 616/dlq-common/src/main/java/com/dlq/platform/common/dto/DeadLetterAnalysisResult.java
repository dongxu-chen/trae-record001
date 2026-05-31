package com.dlq.platform.common.dto;

import com.dlq.platform.common.enums.AlertLevelEnum;
import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import com.dlq.platform.common.enums.MqTypeEnum;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DeadLetterAnalysisResult {

    private String messageId;

    private MqTypeEnum mqType;

    private String topic;

    private DeadReasonTypeEnum deadReasonType;

    private String rootCause;

    private String suggestedAction;

    private AlertLevelEnum riskLevel;

    private Map<String, Object> analysisDetails;

    private LocalDateTime analysisTime;

    private double confidence;

    private List<String> repairSteps;
}
