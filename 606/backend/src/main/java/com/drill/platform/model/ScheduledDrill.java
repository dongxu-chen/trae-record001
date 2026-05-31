package com.drill.platform.model;

import lombok.Data;
import java.util.Date;
import java.util.List;

@Data
public class ScheduledDrill {
    private String id;
    private String name;
    private String description;
    private String cronExpression;
    private String frequency;
    
    private DrillTask taskTemplate;
    private TrafficProfile trafficProfile;
    private String strategyId;
    private List<String> notificationEmails;
    
    private Boolean enabled;
    private String status;
    private Date lastExecutionTime;
    private Date nextExecutionTime;
    private Integer executionCount;
    private Integer successCount;
    
    private Boolean autoPauseOnFailure;
    private Integer consecutiveFailures;
    private Date createTime;
    private Date updateTime;
    private String createdBy;
    
    public enum Frequency {
        HOURLY, DAILY, WEEKLY, MONTHLY, CUSTOM
    }
    
    public enum Status {
        ACTIVE, PAUSED, COMPLETED, ERROR
    }
}
