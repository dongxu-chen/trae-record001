package com.pushplatform.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import com.pushplatform.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("push_task")
public class PushTask extends BaseEntity {

    private String taskNo;

    private Long templateId;

    private String channel;

    private String title;

    private String content;

    private String targetType;

    private String targets;

    @TableField(typeHandler = com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler.class)
    private String extParams;

    private LocalDateTime scheduleTime;

    private Integer status;

    private Integer totalCount;

    private Integer successCount;

    private Integer failCount;

    private String remark;
}
