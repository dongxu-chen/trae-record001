package com.drill.platform.model;

import lombok.Data;
import java.util.Date;

@Data
public class DrillReport {

    private String id;
    private String taskId;
    private String taskName;
    private Date generateTime;
    private TrafficProfile trafficProfile;
    private RateLimitStrategy strategy;
    private DrillResult result;
    private String conclusion;
    private String recommendation;
}
