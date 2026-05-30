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
public class AdaptiveThresholdState implements Serializable {

    private static final long serialVersionUID = 1L;

    private double currentQps;

    private double baselineQps;

    private int adjustedMaxReplayCount;

    private int originalMaxReplayCount;

    private double sensitivityMultiplier;

    private long lastUpdatedAt;

    private String adjustmentReason;

    private boolean adaptiveEnabled;
}
