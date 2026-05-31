package com.dlq.platform;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableAsync
@EnableScheduling
@SpringBootApplication(scanBasePackages = "com.dlq.platform")
public class DlqServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(DlqServiceApplication.class, args);
    }
}
