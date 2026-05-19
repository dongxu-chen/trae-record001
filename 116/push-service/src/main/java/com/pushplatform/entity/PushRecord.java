package com.pushplatform.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import com.pushplatform.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("push_record")
public class PushRecord extends BaseEntity {

    private Long taskId;

    private String taskNo;

    private String channel;

    private String target;

    private String title;

    private String content;

    private Integer status;

    private String errorMsg;

    private String messageId;

    private LocalDateTime callbackTime;

    @TableField(typeHandler = com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler.class)
    private String callbackResult;
}
