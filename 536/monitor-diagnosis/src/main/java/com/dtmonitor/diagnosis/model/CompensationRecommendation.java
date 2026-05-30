package com.dtmonitor.diagnosis.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CompensationRecommendation {
    private String xid;
    private String failureReason;
    private ErrorType errorType;
    private List<CompensationStrategy> strategies;
    private CompensationStrategy recommendedStrategy;
    private String analysisDetail;

    public enum ErrorType {
        DEADLOCK,
        CONNECTION_TIMEOUT,
        NETWORK_ERROR,
        NULL_POINTER,
        DATA_CONSTRAINT,
        SERVICE_UNAVAILABLE,
        PERMISSION_DENIED,
        RESOURCE_EXHAUSTED,
        UNKNOWN
    }
}
