package com.filetransfer.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class UploadInitRequest {
    @NotBlank(message = "文件名不能为空")
    private String fileName;

    @NotNull(message = "文件大小不能为空")
    private Long fileSize;

    private String fileMd5;

    private String contentType;

    private Long userId = 1L;
}
