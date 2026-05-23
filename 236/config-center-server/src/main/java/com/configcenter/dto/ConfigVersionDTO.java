package com.configcenter.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class ConfigVersionDTO {
    private String version;
    private String application;
    private String profile;
    private String content;
    private String format;
    private String description;
    private LocalDateTime createTime;
    private String createdBy;
    private boolean isCurrent;
}
