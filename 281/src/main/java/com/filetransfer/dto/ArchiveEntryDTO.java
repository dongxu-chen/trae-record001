package com.filetransfer.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ArchiveEntryDTO {
    private String name;
    private String path;
    private Long size;
    private Boolean isDirectory;
    private String lastModified;
    private Integer level;
}
