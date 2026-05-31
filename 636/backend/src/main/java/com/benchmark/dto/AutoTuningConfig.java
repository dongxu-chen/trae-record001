package com.benchmark.dto;

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
public class AutoTuningConfig {
    private String algorithm;
    private int maxRounds;
    private int testDurationSeconds;
    private String optimizationTarget;
    private ParamRange threadCountRange;
    private Map<String, ParamRange> algorithmParamRanges;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ParamRange {
        private int min;
        private int max;
        private int step;
    }
}
