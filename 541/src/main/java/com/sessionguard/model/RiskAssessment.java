package com.sessionguard.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RiskAssessment implements Serializable {

    private static final long serialVersionUID = 1L;

    private String sessionId;

    private String userId;

    private int totalScore;

    private RiskLevel riskLevel;

    private List<RiskFactor> riskFactors;

    private Map<String, Object> mlAnomalyResult;

    private LocalDateTime assessedAt;

    private boolean requiresAction;

    private String recommendedAction;

    private String businessScenario;

    private UserGuidance userGuidance;

    private Map<String, Object> extendedDetectionInfo;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UserGuidance implements Serializable {
        private static final long serialVersionUID = 1L;

        private String friendlyMessage;
        private String reauthUrl;
        private String supportContact;
        private int maxReauthAttempts;
        private int reauthCooldownMinutes;
    }

    public enum RiskLevel {
        LOW(0, 29),
        MEDIUM(30, 59),
        HIGH(60, 79),
        CRITICAL(80, 100);

        private final int min;
        private final int max;

        RiskLevel(int min, int max) {
            this.min = min;
            this.max = max;
        }

        public static RiskLevel fromScore(int score) {
            for (RiskLevel level : values()) {
                if (score >= level.min && score <= level.max) {
                    return level;
                }
            }
            return CRITICAL;
        }
    }
}
