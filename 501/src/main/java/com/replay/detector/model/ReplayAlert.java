package com.replay.detector.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReplayAlert implements Serializable {

    private static final long serialVersionUID = 1L;

    private String alertId;

    private AlertLevel level;

    private String fingerprintHash;

    private String path;

    private String clientIp;

    private int replayCount;

    private int windowSizeSeconds;

    private long detectedAt;

    private String message;

    public enum AlertLevel {
        LOW,
        MEDIUM,
        HIGH,
        CRITICAL
    }
}
