package com.sms.platform.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@TableName("sms_blacklist")
public class SmsBlacklist implements Serializable {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String mobile;

    private Integer smsType;

    private Integer isPrefixMatch;

    private String reason;

    private LocalDateTime expireTime;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
