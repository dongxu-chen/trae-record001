package com.flink.recommender.flink.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class VertexDetails {

    @JsonProperty("id")
    private String id;

    @JsonProperty("name")
    private String name;

    @JsonProperty("parallelism")
    private int parallelism;

    @JsonProperty("status")
    private String status;

    @JsonProperty("tasks")
    private List<Task> tasks;

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Task {
        @JsonProperty("subtask")
        private int subtask;

        @JsonProperty("status")
        private String status;

        @JsonProperty("attempt")
        private int attempt;

        @JsonProperty("host")
        private String host;

        @JsonProperty("start-time")
        private long startTime;

        @JsonProperty("end-time")
        private long endTime;

        @JsonProperty("duration")
        private long duration;

        @JsonProperty("metrics")
        private TaskMetrics metrics;
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class TaskMetrics {
        @JsonProperty("read-bytes")
        private long readBytes;

        @JsonProperty("write-bytes")
        private long writeBytes;

        @JsonProperty("read-records")
        private long readRecords;

        @JsonProperty("write-records")
        private long writeRecords;

        @JsonProperty("buffers-in-pool-usage")
        private double buffersInPoolUsage;

        @JsonProperty("buffers-out-pool-usage")
        private double buffersOutPoolUsage;

        @JsonProperty("idle-time")
        private long idleTime;

        @JsonProperty("busy-time")
        private long busyTime;
    }
}
