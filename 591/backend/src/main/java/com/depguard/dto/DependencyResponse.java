package com.depguard.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class DependencyResponse {
    private Long id;
    private Long scanId;
    private String groupId;
    private String artifactId;
    private String version;
    private String latestVersion;
    private String scope;
    private Boolean isDirect;
    private Boolean isOutdated;
}
