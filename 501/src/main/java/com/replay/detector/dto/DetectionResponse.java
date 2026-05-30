package com.replay.detector.dto;

import com.replay.detector.model.DetectionResult;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DetectionResponse {

    private boolean replay;

    private int replayCount;

    private String fingerprintHash;

    private long windowStart;

    private long windowEnd;

    private String message;

    private String requestId;

    public static DetectionResponse from(DetectionResult result, String requestId) {
        return DetectionResponse.builder()
                .replay(result.isReplay())
                .replayCount(result.getReplayCount())
                .fingerprintHash(result.getFingerprintHash())
                .windowStart(result.getWindowStart())
                .windowEnd(result.getWindowEnd())
                .message(result.getMessage())
                .requestId(requestId)
                .build();
    }
}
