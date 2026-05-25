package com.sms.platform.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@TableName("sms_signature")
public class SmsSignature implements Serializable {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String signatureName;

    private String signatureContent;

    private Integer smsType;

    private Integer channelCode;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
