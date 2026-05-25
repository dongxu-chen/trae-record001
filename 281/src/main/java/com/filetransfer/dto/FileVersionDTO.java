package com.filetransfer.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FileVersionDTO {
    private Long id;
    private Long fileId;
    private Integer versionNumber;
    private String fileMd5;
    private Long userId;
    private String username;
    private Long fileSize;
    private String changeDescription;
    private Boolean isCurrent;
    private LocalDateTime createdAt;
    private String downloadUrl;
}
