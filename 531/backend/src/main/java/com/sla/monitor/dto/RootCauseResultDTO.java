package com.sla.monitor.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class RootCauseResultDTO {
    private String serviceName;
    private LocalDateTime timestamp;
    private String primaryCause;
    private Double confidenceScore;
    private List<String> contributingFactors;
    private List<String> recommendations;
}
