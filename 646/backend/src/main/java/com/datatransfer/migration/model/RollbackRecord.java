package com.datatransfer.migration.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("rollback_record")
public class RollbackRecord {
    @TableId(type = IdType.AUTO)
    private Long id;

    private Long taskId;

    private String tableName;

    private String backupTableName;

    private String rollbackStrategy;

    private Long backupRecords;

    private String rollbackStatus;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    private String errorMessage;
}
