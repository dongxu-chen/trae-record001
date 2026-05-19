package com.pushplatform.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import com.pushplatform.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("push_template")
public class PushTemplate extends BaseEntity {

    private String templateCode;

    private String templateName;

    private String channel;

    private String title;

    private String content;

    @TableField(typeHandler = com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler.class)
    private String extParams;

    private Integer status;

    private String remark;
}
