package com.pushplatform.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import com.pushplatform.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("message_aggregate")
public class MessageAggregate extends BaseEntity {

    private String userId;

    private String channel;

    private String aggregateType;

    private Integer windowSeconds;

    private Integer messageCount;

    @TableField(typeHandler = com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler.class)
    private String messages;

    private LocalDateTime firstReceiveTime;

    private LocalDateTime lastReceiveTime;

    private Integer status;
}
