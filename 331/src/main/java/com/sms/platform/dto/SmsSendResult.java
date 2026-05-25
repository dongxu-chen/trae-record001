package com.sms.platform.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.io.Serializable;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SmsSendResult implements Serializable {
    private boolean success;
    private String serialNo;
    private String externalSerialNo;
    private String errorMsg;
    private Integer channelCode;
}
