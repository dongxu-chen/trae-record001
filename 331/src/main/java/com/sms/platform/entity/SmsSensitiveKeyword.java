package com.sms.platform.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@TableName("sms_sensitive_keyword")
public class SmsSensitiveKeyword implements Serializable {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String keyword;

    private Integer category;

    private Integer riskLevel;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
