package com.mfa.dto;

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
public class RiskAssessment {

    private int score;
    private String level;
    private List<String> riskFactors;
    private Map<String, Object> details;
    private boolean stepUpRequired;
}
