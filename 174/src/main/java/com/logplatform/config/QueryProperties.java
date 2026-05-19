package com.logplatform.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "query")
public class QueryProperties {

    private int defaultPageSize = 20;
    private int maxPageSize = 100;
    private int highlightFragmentSize = 150;
    private int highlightNumberOfFragments = 3;
    private String highlightPreTag = "<mark>";
    private String highlightPostTag = "</mark>";
    private int cacheExpireSeconds = 300;
    private int cacheMaxSize = 1000;
}
