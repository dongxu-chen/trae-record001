package com.sms.platform.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@TableName("sms_send_record")
public class SmsSendRecord implements Serializable {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String serialNo;

    private String mobile;

    private Integer smsType;

    private Long signatureId;

    private Long templateId;

    private String templateCode;

    private Integer channelCode;

    private String sendContent;

    private String variableParams;

    private Integer status;

    private String errorMsg;

    private String externalSerialNo;

    private LocalDateTime sendTime;

    private Integer receiptStatus;

    private LocalDateTime receiptTime;

    private LocalDateTime receiptExpireTime;

    private String receiptContent;

    private Integer contentSecurityStatus;

    private Integer contentSecurityRiskLevel;

    private String contentSecurityKeywords;

    private String mobileProvince;

    private String mobileCity;

    private Integer mobileOperator;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
