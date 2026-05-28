package com.datasync.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TableSyncChannel implements Serializable {
    private static final long serialVersionUID = 1L;

    private String channelId;
    private String tableName;
    private String topicName;
    private String consumerGroupId;
    private int priority;
    private boolean isLargeTable;
    private long expectedRowCount;
    private int partitionCount;
    private List<String> sourceDatacenters;
    private boolean enabled;
}
