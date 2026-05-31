package com.datatransfer.migration.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("checkpoint")
public class Checkpoint {
    @TableId(type = IdType.AUTO)
    private Long id;

    private Long taskId;

    private String tableName;

    private String positionType;

    private String positionValue;

    private Long processedRecords;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
