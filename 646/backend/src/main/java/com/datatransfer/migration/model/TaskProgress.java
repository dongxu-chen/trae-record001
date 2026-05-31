package com.datatransfer.migration.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("task_progress")
public class TaskProgress {
    @TableId(type = IdType.AUTO)
    private Long id;

    private Long taskId;

    private Double progress;

    private Long totalRecords;

    private Long processedRecords;

    private Long errorRecords;

    private Double throughput;

    private String currentPositionType;

    private String currentPositionValue;

    private Long batchSize;

    private LocalDateTime updatedAt;
}
