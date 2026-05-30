package com.migration.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ServiceInstance {

    private String serviceId;
    private String instanceId;
    private String host;
    private int port;
    private String scheme;
    private String status;
    private Map<String, String> metadata;
    private String registrySource;

    public String getInstanceId() {
        if (instanceId != null && !instanceId.isEmpty()) {
            return instanceId;
        }
        return host + ":" + serviceId + ":" + port;
    }
}
