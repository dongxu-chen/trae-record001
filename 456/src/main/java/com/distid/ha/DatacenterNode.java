package com.distid.ha;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class DatacenterNode {

    public enum Status {
        ACTIVE,
        STANDBY,
        DRAINING,
        OFFLINE
    }

    private final String dcCode;
    private final String region;
    private final String zkConnectString;
    private final String redisHost;
    private final int redisPort;
    private final long segmentOffset;
    private final long segmentStep;
    private final Status status;
    private final long lastHeartbeat;
    private final int priority;

    public boolean isAvailable() {
        return status == Status.ACTIVE || status == Status.STANDBY;
    }

    public boolean isActive() {
        return status == Status.ACTIVE;
    }
}
