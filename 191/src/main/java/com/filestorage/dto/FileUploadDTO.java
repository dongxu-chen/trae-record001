package com.filestorage.dto;

import lombok.Data;

@Data
public class FileUploadDTO {

    private String tenantCode;
    private String uploadId;
    private String fileMd5;
    private String fileName;
    private Long fileSize;
    private Integer chunkNumber;
    private Integer totalChunks;
    private Long chunkSize;
    private String uploadUser;
}
