package com.filestorage.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class FileShareDTO {

    private String tenantCode;
    private Long fileId;
    private String shareUser;
    private String extractCode;
    private Integer expireHours;
}
