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
@TableName(value = "datasource", autoResultMap = true)
public class DataSource {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;

    private String type;

    @TableField(typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> config;

    private String status;

    private Long creatorId;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
