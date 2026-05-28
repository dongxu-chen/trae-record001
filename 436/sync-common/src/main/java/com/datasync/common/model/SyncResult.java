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
public class SyncResult implements Serializable {
    private static final long serialVersionUID = 1L;

    private boolean success;

    private String message;

    private long processTime;

    private String eventId;

    private ConflictResult conflictResult;

    private Throwable error;

    public static SyncResult success(String eventId) {
        return SyncResult.builder()
                .success(true)
                .eventId(eventId)
                .build();
    }

    public static SyncResult success(String eventId, long processTime) {
        return SyncResult.builder()
                .success(true)
                .eventId(eventId)
                .processTime(processTime)
                .build();
    }

    public static SyncResult failure(String eventId, String message) {
        return SyncResult.builder()
                .success(false)
                .eventId(eventId)
                .message(message)
                .build();
    }

    public static SyncResult failure(String eventId, String message, Throwable error) {
        return SyncResult.builder()
                .success(false)
                .eventId(eventId)
                .message(message)
                .error(error)
                .build();
    }
}
