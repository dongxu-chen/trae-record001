package com.datasync.common.model;

import com.datasync.common.enums.DatabaseType;
import com.datasync.common.enums.OperationType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DataChangeEvent implements Serializable {
    private static final long serialVersionUID = 1L;

    private String eventId;

    private String globalTransactionId;

    private List<String> visitedDatacenters;

    private String sourceDatacenterId;

    private String sourceDatabaseId;

    private DatabaseType sourceDatabaseType;

    private String schemaName;

    private String tableName;

    private OperationType operationType;

    private Long timestamp;

    private Long executionTime;

    private Long hlcTimestamp;

    private Long logicalClock;

    private Long wallClock;

    private List<String> primaryKeys;

    private Map<String, ColumnMetaData> columnMetaData;

    private List<RowData> rowDataList;

    private String businessKey;

    private Long businessVersion;

    private Long syncTimestamp;

    private boolean isRetry;

    private int retryCount;

    public String getFullTableName() {
        return schemaName + "." + tableName;
    }

    public String getUniqueKey() {
        if (businessKey != null && !businessKey.isEmpty()) {
            return sourceDatacenterId + "_" + sourceDatabaseId + "_" + getFullTableName() + "_" + businessKey;
        }
        return sourceDatacenterId + "_" + sourceDatabaseId + "_" + getFullTableName() + "_" + eventId;
    }

    public void addVisitedDatacenter(String datacenterId) {
        if (visitedDatacenters == null) {
            visitedDatacenters = new ArrayList<>();
        }
        if (!visitedDatacenters.contains(datacenterId)) {
            visitedDatacenters.add(datacenterId);
        }
    }

    public boolean hasVisitedDatacenter(String datacenterId) {
        return visitedDatacenters != null && visitedDatacenters.contains(datacenterId);
    }

    public String getHlcKey() {
        if (hlcTimestamp != null && logicalClock != null) {
            return hlcTimestamp + "_" + logicalClock;
        }
        return null;
    }

    public int compareHlc(DataChangeEvent other) {
        if (other == null) {
            return 1;
        }
        if (this.hlcTimestamp == null && other.hlcTimestamp == null) {
            return 0;
        }
        if (this.hlcTimestamp == null) {
            return -1;
        }
        if (other.hlcTimestamp == null) {
            return 1;
        }
        int timestampCompare = Long.compare(this.hlcTimestamp, other.hlcTimestamp);
        if (timestampCompare != 0) {
            return timestampCompare;
        }
        return Long.compare(this.logicalClock != null ? this.logicalClock : 0,
                other.logicalClock != null ? other.logicalClock : 0);
    }
}
