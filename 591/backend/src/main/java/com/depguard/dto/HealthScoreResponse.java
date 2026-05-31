package com.depguard.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class HealthScoreResponse {
    private String dependencyKey;
    private double overallScore;
    private String grade;
    private double vulnerabilityScore;
    private double freshnessScore;
    private double popularityScore;
    private List<String> recommendations;
}
