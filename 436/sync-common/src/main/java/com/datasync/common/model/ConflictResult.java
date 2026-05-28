package com.datasync.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConflictResult implements Serializable {
    private static final long serialVersionUID = 1L;

    private boolean hasConflict;

    private ConflictResolution resolution;

    private String conflictReason;

    private String winnerEventId;

    private String loserEventId;

    private long winnerTimestamp;

    private long loserTimestamp;

    public enum ConflictResolution {
        APPLY_NEWER,
        APPLY_OLDER,
        DISCARD_BOTH,
        MERGE,
        MANUAL_REQUIRED
    }

    public static ConflictResult noConflict() {
        return ConflictResult.builder()
                .hasConflict(false)
                .build();
    }

    public static ConflictResult conflict(ConflictResolution resolution, String reason) {
        return ConflictResult.builder()
                .hasConflict(true)
                .resolution(resolution)
                .conflictReason(reason)
                .build();
    }
}
