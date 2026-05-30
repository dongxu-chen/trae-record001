package com.sessionguard.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WebhookPayload implements Serializable {

    private static final long serialVersionUID = 1L;

    private String alertId;

    private String sessionId;

    private String userId;

    private RiskAssessment.RiskLevel riskLevel;

    private int riskScore;

    private String alertType;

    private String message;

    private Map<String, Object> details;

    private LocalDateTime timestamp;
}
