package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConnectionLeakAlert {
    private long timestamp;
    private String alertId;
    private String severity;
    private String message;
    private int connectionId;
    private long holdDurationMs;
    private long borrowTimestamp;
    private String threadName;
    private String sqlPreview;
    private double poolUtilizationAtAlert;
    private int activeConnectionsAtAlert;
    private List<String> recommendations;
    private boolean acknowledged;
}
