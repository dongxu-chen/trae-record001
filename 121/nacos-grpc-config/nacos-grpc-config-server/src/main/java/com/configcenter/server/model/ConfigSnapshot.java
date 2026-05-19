package com.configcenter.server.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.HashMap;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConfigSnapshot {
    private String dataId;
    private String group;
    private String namespace;
    private String content;
    private Map<String, String> parsedConfigs = new HashMap<>();
    private long version;
    private long timestamp;
    private String md5;
}
