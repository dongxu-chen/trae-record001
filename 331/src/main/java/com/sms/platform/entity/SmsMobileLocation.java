package com.sms.platform.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@TableName("sms_mobile_location")
public class SmsMobileLocation implements Serializable {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String mobilePrefix;

    private String province;

    private String city;

    private Integer operator;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
