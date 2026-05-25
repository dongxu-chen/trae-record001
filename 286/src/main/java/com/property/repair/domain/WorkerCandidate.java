package com.property.repair.domain;

import lombok.Data;

@Data
public class WorkerCandidate {

    private Long workerId;
    private String workerName;
    private String skills;
    private Integer currentWorkload;
    private Double avgRating;
    private Double longitude;
    private Double latitude;
    private Double distance;
    private Integer skillScore;
    private Integer workloadScore;
    private Integer ratingScore;
    private Integer distanceScore;
    private Integer totalScore;
    private boolean selected;

    public WorkerCandidate(Long workerId, String workerName, String skills, Integer currentWorkload,
                           Double avgRating, Double longitude, Double latitude) {
        this.workerId = workerId;
        this.workerName = workerName;
        this.skills = skills;
        this.currentWorkload = currentWorkload;
        this.avgRating = avgRating;
        this.longitude = longitude;
        this.latitude = latitude;
        this.skillScore = 0;
        this.workloadScore = 0;
        this.ratingScore = 0;
        this.distanceScore = 0;
        this.totalScore = 0;
        this.selected = false;
    }
}
