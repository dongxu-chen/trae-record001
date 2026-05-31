package com.tracing.optimizer.service;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication(scanBasePackages = "com.tracing.optimizer")
@EnableScheduling
public class SamplingServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(SamplingServiceApplication.class, args);
    }
}
