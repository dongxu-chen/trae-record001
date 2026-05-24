package com.abtest.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.Map;

@Data
public class EventDTO {

    @NotBlank(message = "用户ID不能为空")
    private String userId;

    @NotBlank(message = "事件名称不能为空")
    private String eventName;

    @NotNull(message = "实验ID不能为空")
    private Long experimentId;

    private String variantName;

    private Map<String, Object> properties;

    private LocalDateTime timestamp = LocalDateTime.now();
}
