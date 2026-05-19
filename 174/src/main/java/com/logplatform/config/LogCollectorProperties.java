package com.logplatform.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.ArrayList;
import java.util.List;

@Data
@Configuration
@ConfigurationProperties(prefix = "log.collector")
public class LogCollectorProperties {

    private FileConfig file = new FileConfig();
    private KafkaConfig kafka = new KafkaConfig();
    private ElasticsearchConfig elasticsearch = new ElasticsearchConfig();

    @Data
    public static class FileConfig {
        private boolean enabled = true;
        private long scanInterval = 5000;
        private List<FileSource> sources = new ArrayList<>();
    }

    @Data
    public static class FileSource {
        private String name;
        private String path;
        private String encoding = "UTF-8";
        private String multilinePattern;
    }

    @Data
    public static class KafkaConfig {
        private boolean enabled = false;
        private String bootstrapServers;
        private List<KafkaTopic> topics = new ArrayList<>();
    }

    @Data
    public static class KafkaTopic {
        private String name;
        private String groupId = "log-collector-group";
        private int concurrency = 3;
    }

    @Data
    public static class ElasticsearchConfig {
        private boolean enabled = false;
        private String uris;
        private List<ElasticsearchIndex> indices = new ArrayList<>();
    }

    @Data
    public static class ElasticsearchIndex {
        private String name;
        private String alias;
    }
}
