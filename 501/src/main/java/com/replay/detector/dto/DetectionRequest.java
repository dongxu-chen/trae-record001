package com.replay.detector.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DetectionRequest {

    @NotBlank(message = "Path is required")
    private String path;

    private Map<String, String> params;

    private String userAgent;

    @NotBlank(message = "Client IP is required")
    private String clientIp;

    private String httpMethod;

    private Long timestamp;

    @Min(value = 1, message = "Window size must be at least 1 second")
    private Integer windowSizeSeconds;

    @Min(value = 1, message = "Max replay count must be at least 1")
    private Integer maxReplayCount;
}
