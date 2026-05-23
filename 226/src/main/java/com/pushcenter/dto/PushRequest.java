package com.pushcenter.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import java.util.Map;

@Data
public class PushRequest {

    @NotBlank(message = "userId cannot be blank")
    private String userId;

    @NotBlank(message = "templateCode cannot be blank")
    private String templateCode;

    private Map<String, Object> variables;

    private String preferredChannel;

    private String priority;

    private Boolean jumpQueue;
}
