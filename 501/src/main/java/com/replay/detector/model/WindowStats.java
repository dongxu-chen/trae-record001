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
public class WindowStats implements Serializable {

    private static final long serialVersionUID = 1L;

    private String fingerprintHash;

    private long windowStart;

    private long windowEnd;

    private int requestCount;

    private int currentWindowCount;

    private int previousWindowCount;

    private boolean overlapActive;

    private int uniqueCount;

    private int duplicateCount;

    private double duplicateRate;
}
