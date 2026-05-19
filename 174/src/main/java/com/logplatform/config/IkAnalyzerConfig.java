package com.logplatform.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Data
@Configuration
@ConfigurationProperties(prefix = "elasticsearch.analysis")
public class IkAnalyzerConfig {

    private boolean useSmart = true;
    private boolean enableSynonym = true;
    private String synonymPath = "elasticsearch/analysis/synonyms.txt";
    private String stopwordPath = "elasticsearch/analysis/stopwords.txt";
    private List<String> customDictionaries;
    private List<String> remoteDictionaries;
}
