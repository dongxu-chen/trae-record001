package com.datasync.coordinator.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LinkInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    private String linkId;
    private String sourceDatacenterId;
    private String targetDatacenterId;
    private String status;
    private long latencyMs;
    private long lastCheckTime;
    private int priority;
    private boolean isActive;
}
