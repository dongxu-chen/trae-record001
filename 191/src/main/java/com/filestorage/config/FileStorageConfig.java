package com.filestorage.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "file")
public class FileStorageConfig {

    private Chunk chunk = new Chunk();
    private Thumbnail thumbnail = new Thumbnail();
    private Recycle recycle = new Recycle();
    private Upload upload = new Upload();

    @Data
    public static class Chunk {
        private long size = 5 * 1024 * 1024;
    }

    @Data
    public static class Thumbnail {
        private Image image = new Image();

        @Data
        public static class Image {
            private boolean enabled = true;
            private int width = 200;
            private int height = 200;
            private float quality = 0.8f;
        }
    }

    @Data
    public static class Recycle {
        private int retentionDays = 30;
    }

    @Data
    public static class Upload {
        private int timeoutHours = 24;
    }
}
