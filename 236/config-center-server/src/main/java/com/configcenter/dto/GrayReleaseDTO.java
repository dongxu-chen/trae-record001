package com.configcenter.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class GrayReleaseDTO {
    private String id;
    private String application;
    private String profile;
    private String grayVersion;
    private String stableVersion;
    private GrayStrategy strategy;
    private int percentage;
    private List<String> ipList;
    private String content;
    private String format;
    private String description;
    private LocalDateTime createTime;
    private String createdBy;
    private LocalDateTime expireTime;
    private boolean enabled;

    public enum GrayStrategy {
        PERCENTAGE,
        IP_LIST
    }
}
