package com.property.repair.domain;

import lombok.Data;
import java.util.List;

@Data
public class DispatchRequest {

    private String repairType;
    private Integer priority;
    private Integer maxWorkload;
    private Double orderLongitude;
    private Double orderLatitude;
    private List<WorkerCandidate> candidates;
    private WorkerCandidate selectedWorker;

    public DispatchRequest(String repairType, Integer priority, Integer maxWorkload,
                           Double orderLongitude, Double orderLatitude, List<WorkerCandidate> candidates) {
        this.repairType = repairType;
        this.priority = priority;
        this.maxWorkload = maxWorkload;
        this.orderLongitude = orderLongitude;
        this.orderLatitude = orderLatitude;
        this.candidates = candidates;
    }
}
