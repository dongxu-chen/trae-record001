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
public class NodeInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    private String nodeId;
    private String datacenterId;
    private long startTime;
    private String status;
    private String host;
    private int port;
    private long lastHeartbeat;
}
