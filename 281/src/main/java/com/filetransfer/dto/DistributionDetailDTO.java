package com.filetransfer.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DistributionDetailDTO {
    private String distributionId;
    private String title;
    private String message;
    private String sourceUsername;
    private Integer totalFiles;
    private Long totalSize;
    private Integer totalRecipients;
    private Integer viewCount;
    private Integer downloadCount;
    private LocalDateTime createdAt;
    private LocalDateTime expiredAt;
    private Boolean isActive;
    private List<DistributionFileDTO> files;
    private List<DistributionRecipientDTO> recipients;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DistributionFileDTO {
        private Long fileId;
        private String fileName;
        private Long fileSize;
        private String contentType;
        private Integer viewCount;
        private Integer downloadCount;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DistributionRecipientDTO {
        private String type;
        private String identifier;
        private String name;
        private Boolean hasViewed;
        private Boolean hasDownloaded;
        private LocalDateTime viewedAt;
        private LocalDateTime downloadedAt;
    }
}
