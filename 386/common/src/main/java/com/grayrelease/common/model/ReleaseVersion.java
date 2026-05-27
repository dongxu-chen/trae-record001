package com.grayrelease.common.model;

import com.grayrelease.common.enums.VersionStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReleaseVersion {

    private String id;

    private String serviceName;

    private String version;

    private String image;

    private VersionStatus status;

    private Map<String, String> metadata;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}