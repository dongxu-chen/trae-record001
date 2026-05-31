package com.flink.recommender.flink.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class JobDetails {

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

    @JsonProperty("maxParallelism")
    private int maxParallelism;

    @JsonProperty("now")
    private long now;

    @JsonProperty("timestamps")
    private Map<String, Long> timestamps;

    @JsonProperty("vertices")
    private List<Vertex> vertices;

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Vertex {
        @JsonProperty("id")
        private String id;

        @JsonProperty("name")
        private String name;

        @JsonProperty("parallelism")
        private int parallelism;

        @JsonProperty("status")
        private String status;

        @JsonProperty("start-time")
        private long startTime;

        @JsonProperty("end-time")
        private long endTime;

        @JsonProperty("duration")
        private long duration;

        @JsonProperty("tasks")
        private TaskSummary tasks;

        @JsonProperty("metrics")
        private Metrics metrics;
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

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Metrics {
        @JsonProperty("read-bytes")
        private long readBytes;

        @JsonProperty("write-bytes")
        private long writeBytes;

        @JsonProperty("read-records")
        private long readRecords;

        @JsonProperty("write-records")
        private long writeRecords;
    }
}
