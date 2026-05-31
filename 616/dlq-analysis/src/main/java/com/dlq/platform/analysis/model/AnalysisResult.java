package com.dlq.platform.analysis.model;

import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AnalysisResult {

    private DeadReasonTypeEnum reasonType;

    private double confidence;

    private String suggestedAction;

    private List<String> repairSteps;

    private String rootCause;

    private Map<String, Object> details;
}
