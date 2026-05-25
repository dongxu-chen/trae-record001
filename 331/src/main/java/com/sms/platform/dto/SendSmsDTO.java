package com.sms.platform.dto;

import lombok.Data;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.io.Serializable;
import java.util.Map;

@Data
public class SendSmsDTO implements Serializable {
    @NotBlank(message = "手机号不能为空")
    private String mobile;

    @NotNull(message = "短信类型不能为空")
    private Integer smsType;

    @NotBlank(message = "模板编码不能为空")
    private String templateCode;

    private Map<String, String> variableParams;
}
