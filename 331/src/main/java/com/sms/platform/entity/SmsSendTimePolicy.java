package com.sms.platform.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@TableName("sms_send_time_policy")
public class SmsSendTimePolicy implements Serializable {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String policyName;

    private Integer smsType;

    private String timeStart;

    private String timeEnd;

    private String weekdays;

    private String timezone;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
