package com.sla.monitor.dto;

import lombok.Data;

import java.util.List;

@Data
public class PredictionResultDTO {
    private String serviceName;
    private List<SlaTrendDTO> historicalData;
    private List<SlaTrendDTO> predictedData;
    private Double predictedSlaRate;
    private String trendDirection;
    private boolean predictedViolation;
}
