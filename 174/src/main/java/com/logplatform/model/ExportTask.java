package com.logplatform.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ExportTask {

    private String taskId;

    private ExportStatus status;

    private ExportFormat format;

    private LogQueryRequest queryRequest;

    private long totalRecords;

    private long exportedRecords;

    private String fileName;

    private String fileUrl;

    private long fileSize;

    private Instant createdAt;

    private Instant completedAt;

    private String errorMessage;

    public enum ExportStatus {
        PENDING,
        PROCESSING,
        COMPLETED,
        FAILED
    }

    public enum ExportFormat {
        CSV,
        JSON
    }
}
