package com.filestorage.dto;

import lombok.Data;

@Data
public class FileVersionDTO {

    private String tenantCode;
    private Long fileId;
    private Integer versionNumber;
    private String uploadUser;
    private String changeDescription;
}
