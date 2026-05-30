package com.sessionguard.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LocationJumpDetection implements Serializable {

    private static final long serialVersionUID = 1L;

    private String userId;
    private String sessionId;
    private JumpLevel jumpLevel;
    private double calculatedSpeedKmh;
    private double distanceKm;
    private long timeGapMinutes;
    private String fromLocation;
    private String toLocation;
    private String fromIp;
    private String toIp;
    private LocalDateTime detectedAt;
    private String description;
    private int riskScoreContribution;

    public enum JumpLevel {
        NONE(0, "正常"),
        LOW(1, "轻微区域切换"),
        MEDIUM(2, "跨区域切换"),
        HIGH(3, "跨省/跨州切换"),
        IMPOSSIBLE(4, "物理不可能的位置跳跃");

        private final int level;
        private final String description;

        JumpLevel(int level, String description) {
            this.level = level;
            this.description = description;
        }

        public int getLevel() { return level; }
        public String getDescription() { return description; }
    }
}
