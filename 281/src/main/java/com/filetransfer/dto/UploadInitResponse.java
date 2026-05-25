package com.filetransfer.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UploadInitResponse {
    private String uploadId;
    private String fileName;
    private Long fileSize;
    private Integer totalChunks;
    private Long chunkSize;
    private List<Integer> uploadedChunks;
    private Boolean needMerge;
    private Boolean rapidUpload;
    private Long fileId;
    private String fileUrl;
}
