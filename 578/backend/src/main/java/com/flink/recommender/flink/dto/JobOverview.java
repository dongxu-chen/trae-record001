package com.flink.recommender.flink.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class JobOverview {

    @JsonProperty("jobs")
    private List<Job> jobs;

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Job {
        @JsonProperty("jid")
        private String jobId;

        @JsonProperty("name")
        private String name;

        @JsonProperty("state")
        private String state;

        @JsonProperty("start-time")
        private long startTime;

        @JsonProperty("end-time")
        private long endTime;

        @JsonProperty("duration")
        private long duration;

        @JsonProperty("last-modification")
        private long lastModification;

        @JsonProperty("tasks")
        private TaskSummary tasks;
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class TaskSummary {
        @JsonProperty("total")
        private int total;

        @JsonProperty("created")
        private int created;

        @JsonProperty("scheduled")
        private int scheduled;

        @JsonProperty("deploying")
        private int deploying;

        @JsonProperty("running")
        private int running;

        @JsonProperty("failing")
        private int failing;

        @JsonProperty("failed")
        private int failed;

        @JsonProperty("cancelling")
        private int cancelling;

        @JsonProperty("canceled")
        private int canceled;

        @JsonProperty("finished")
        private int finished;

        @JsonProperty("reconciling")
        private int reconciling;

        @JsonProperty("initializing")
        private int initializing;
    }
}
