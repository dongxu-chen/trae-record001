package com.health.task.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ScoreTrendPoint {
    private String timestamp;
    private int overallScore;
    private int durationScore;
    private int successRateScore;
    private int frequencyScore;
    private int resourceScore;
}
