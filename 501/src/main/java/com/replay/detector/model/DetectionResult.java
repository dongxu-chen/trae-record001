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
public class DetectionResult implements Serializable {

    private static final long serialVersionUID = 1L;

    private boolean replay;

    private int replayCount;

    private String fingerprintHash;

    private long windowStart;

    private long windowEnd;

    private String message;

    public static DetectionResult safe(String fingerprintHash, long windowStart, long windowEnd) {
        return DetectionResult.builder()
                .replay(false)
                .replayCount(0)
                .fingerprintHash(fingerprintHash)
                .windowStart(windowStart)
                .windowEnd(windowEnd)
                .message("Request is not a replay")
                .build();
    }

    public static DetectionResult replay(String fingerprintHash, int replayCount, long windowStart, long windowEnd) {
        return DetectionResult.builder()
                .replay(true)
                .replayCount(replayCount)
                .fingerprintHash(fingerprintHash)
                .windowStart(windowStart)
                .windowEnd(windowEnd)
                .message("Replay attack detected: " + replayCount + " duplicate requests in window")
                .build();
    }
}
