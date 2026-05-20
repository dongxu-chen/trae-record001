package com.filestorage.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "file.watermark")
public class WatermarkConfig {

    private boolean enabled = true;
    private String text = "CONFIDENTIAL";
    private float opacity = 0.3f;
    private int fontSize = 30;
    private String color = "#cccccc";
    private int rotation = -30;
    private int intervalX = 200;
    private int intervalY = 150;
}
