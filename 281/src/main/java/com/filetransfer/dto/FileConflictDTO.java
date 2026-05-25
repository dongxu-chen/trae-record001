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
public class FileConflictDTO {
    private Boolean hasConflict;
    private String conflictType;
    private Long existingFileId;
    private String existingFileName;
    private String existingFileMd5;
    private Long existingFileSize;
    private String existingUsername;
    private LocalDateTime existingCreatedAt;
    private Integer existingVersion;
    private String suggestedAction;
    private String message;
}
