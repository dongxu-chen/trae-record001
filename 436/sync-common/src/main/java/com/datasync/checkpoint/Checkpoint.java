package com.datasync.checkpoint;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Checkpoint implements Serializable {
    private static final long serialVersionUID = 1L;

    private String checkpointId;
    private String nodeId;
    private String datacenterId;
    private String tableName;
    private String channelId;
    private String topicName;
    private Map<Integer, Long> partitionOffsets;
    private long lastProcessedHlcTimestamp;
    private long lastProcessedLogicalClock;
    private LocalDateTime checkpointTime;
    private long processedEventCount;
    private long failedEventCount;
    private String status;
    private String lastEventId;
}
