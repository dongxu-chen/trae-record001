package com.filetransfer.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class ChunkUploadRequest {
    private String uploadId;

    @NotNull(message = "分片号不能为空")
    private Integer chunkNumber;

    @NotNull(message = "总分片数不能为空")
    private Integer totalChunks;

    @NotNull(message = "分片大小不能为空")
    private Long chunkSize;

    @NotNull(message = "文件大小不能为空")
    private Long fileSize;

    @NotBlank(message = "文件名不能为空")
    private String fileName;

    private String fileMd5;

    private String contentType;

    private Long userId = 1L;
}
