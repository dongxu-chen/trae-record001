package com.homestay.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class HostApplyDTO {

    @NotBlank(message = "身份证号不能为空")
    private String idCard;

    @NotBlank(message = "真实姓名不能为空")
    private String name;

    private String applyReason;
}
