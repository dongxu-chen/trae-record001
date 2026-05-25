package com.sms.platform.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@TableName("sms_channel_config")
public class SmsChannelConfig implements Serializable {
    @TableId(type = IdType.AUTO)
    private Long id;

    private Integer channelCode;

    private String channelName;

    private Integer isMaster;

    private Integer weight;

    private Integer maxSendPerSecond;

    private Integer maxSendPerMinute;

    private Integer maxSendPerHour;

    private Integer tokenBucketCapacity;

    private Integer tokenBucketRate;

    private Integer receiptTimeoutSeconds;

    private Integer maxReceiptTimeoutCount;

    private Integer status;

    private Integer isHealthy;

    private Integer failCount;

    private Integer receiptTimeoutCount;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
