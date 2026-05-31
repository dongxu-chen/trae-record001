package com.depguard.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ConflictResponse {
    private String groupId;
    private String artifactId;
    private List<String> versions;
    private List<ServiceVersion> serviceVersions;
    private Integer conflictCount;
    private String recommendedVersion;
    private String severity;
    private String conflictType;

    public ConflictResponse(String groupId, String artifactId, List<String> versions,
                            List<ServiceVersion> serviceVersions, Integer conflictCount) {
        this.groupId = groupId;
        this.artifactId = artifactId;
        this.versions = versions;
        this.serviceVersions = serviceVersions;
        this.conflictCount = conflictCount;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ServiceVersion {
        private Long serviceId;
        private String serviceName;
        private String version;
    }
}
