package com.logplatform.model;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

@Data
public class ExportRequest {

    private LogQueryRequest query;

    @Min(value = 1, message = "导出数量不能小于1")
    @Max(value = 100000, message = "单次最大导出100000条")
    private int maxRecords = 10000;

    private ExportTask.ExportFormat format = ExportTask.ExportFormat.CSV;
}
