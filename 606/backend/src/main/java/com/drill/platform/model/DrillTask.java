package com.drill.platform.model;

import lombok.Data;
import java.util.Date;

@Data
public class DrillTask {

    private String id;
    private String name;
    private String description;
    private DrillStatus status;
    private TrafficProfile trafficProfile;
    private String strategyId;
    private Date createTime;
    private Date startTime;
    private Date endTime;
    private DrillResult result;

    public enum DrillStatus {
        CREATED, RUNNING, COMPLETED, FAILED, CANCELLED
    }
}
