package com.datatransfer.migration.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.Map;

@Data
@TableName(value = "task", autoResultMap = true)
public class Task {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;

    private Long sourceId;

    private Long targetId;

    private String mode;

    private String status;

    @TableField(typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> config;

    private Long creatorId;

    private LocalDateTime createdAt;

    private LocalDateTime startedAt;

    private LocalDateTime finishedAt;
}
