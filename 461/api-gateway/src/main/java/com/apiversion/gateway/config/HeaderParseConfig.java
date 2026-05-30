package com.apiversion.gateway.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Data
@Component
@ConfigurationProperties(prefix = "api.version.header")
public class HeaderParseConfig {

    private List<HeaderParseRule> rules = new ArrayList<>();

    @Data
    public static class HeaderParseRule {
        private String headerName;
        private String parseStrategy;
        private String pattern;
        private String defaultValue;
        private Integer priority;
    }
}
