package com.shortlink.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;
import org.hibernate.validator.constraints.URL;

@Data
public class CreateShortLinkRequest {

    @NotBlank(message = "原始URL不能为空")
    @URL(message = "URL格式不正确")
    private String originUrl;

    private String customCode;

    private String description;

    private Integer expireDays;

    private Boolean enableStats = true;
}
