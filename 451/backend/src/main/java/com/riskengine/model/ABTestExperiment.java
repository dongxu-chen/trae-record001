package com.riskengine.model;

import lombok.Data;
import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
public class ABTestExperiment implements Serializable {
    private Long id;
    private String experimentCode;
    private String experimentName;
    private String description;
    private String status;
    private List<String> baselineRuleCodes;
    private List<String> experimentRuleCodes;
    private Integer trafficPercentage;
    private String splitStrategy;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
    private Map<String, Object> baselineStats;
    private Map<String, Object> experimentStats;

    public ABTestExperiment() {
        this.status = "CREATED";
        this.trafficPercentage = 10;
        this.splitStrategy = "USER_ID_HASH";
        this.createTime = LocalDateTime.now();
        this.updateTime = LocalDateTime.now();
    }
}
