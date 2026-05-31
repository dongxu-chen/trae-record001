package com.dlq.platform.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication(scanBasePackages = "com.dlq.platform")
@EnableScheduling
public class DlqPlatformApplication {

    public static void main(String[] args) {
        SpringApplication.run(DlqPlatformApplication.class, args);
    }
}
