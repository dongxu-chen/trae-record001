package com.filetransfer.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProgressMessage {
    private String uploadId;
    private String fileName;
    private Long fileSize;
    private Long uploadedSize;
    private Integer totalChunks;
    private Integer uploadedChunks;
    private Integer currentChunk;
    private Double progress;
    private String status;
    private String message;
    private Long fileId;
}
