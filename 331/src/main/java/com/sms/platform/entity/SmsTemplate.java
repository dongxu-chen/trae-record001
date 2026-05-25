package com.sms.platform.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@TableName("sms_template")
public class SmsTemplate implements Serializable {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String templateCode;

    private String templateName;

    private String templateContent;

    private Integer smsType;

    private Integer channelCode;

    private String externalTemplateId;

    private String variableNames;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
