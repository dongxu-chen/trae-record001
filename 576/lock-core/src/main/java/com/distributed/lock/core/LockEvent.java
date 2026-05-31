package com.distributed.lock.core;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LockEvent implements Serializable {

    private String eventId;

    private String lockKey;

    private String lockType;

    private EventType eventType;

    private String threadId;

    private String threadName;

    private String hostName;

    private String applicationName;

    private long timestamp;

    private Long waitTimeMs;

    private Long holdTimeMs;

    private Long leaseTimeMs;

    private boolean success;

    private String errorMessage;

    private String ownerId;

    public enum EventType {
        ACQUIRE_START,
        ACQUIRE_SUCCESS,
        ACQUIRE_FAIL,
        RELEASE_START,
        RELEASE_SUCCESS,
        RELEASE_FAIL,
        LOCK_EXPIRED,
        LOCK_RENEW
    }
}