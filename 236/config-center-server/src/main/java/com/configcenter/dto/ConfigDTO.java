package com.configcenter.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class ConfigDTO {
    private String application;
    private String profile;
    private String label;
    private String content;
    private String format;
    private String version;
    private String description;
    private LocalDateTime createTime;
    private String createdBy;
}
