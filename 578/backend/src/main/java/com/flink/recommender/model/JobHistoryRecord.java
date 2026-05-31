package com.flink.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "job_history_records")
public class JobHistoryRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String jobId;

    @Column(nullable = false)
    private String jobName;

    private String jobType;

    private int parallelism;
    private int taskManagerMemoryMb;
    private double taskManagerCpuCores;
    private int numTaskManagers;

    private long totalRecordsProcessed;
    private long totalBytesProcessed;
    private double avgThroughputRecordsPerSec;
    private double avgThroughputBytesPerSec;
    private double avgLatencyMs;

    private double avgCpuUtilization;
    private double avgMemoryUtilization;
    private double maxCpuUtilization;
    private double maxMemoryUtilization;

    private boolean hasDataSkew;
    private double dataSkewFactor;

    private long jobDurationMs;
    private boolean succeeded;

    @Column(nullable = false)
    private LocalDateTime recordedAt;

    @PrePersist
    protected void onCreate() {
        recordedAt = LocalDateTime.now();
    }
}
