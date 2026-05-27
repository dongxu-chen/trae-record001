package com.grayrelease.common.dto;

import com.grayrelease.common.enums.VersionStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class VersionRequest {

    private String serviceName;

    private String version;

    private String image;

    private VersionStatus status;

    private Map<String, String> metadata;
}