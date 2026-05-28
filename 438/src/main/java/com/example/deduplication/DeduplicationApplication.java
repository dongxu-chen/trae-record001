package com.example.deduplication;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class DeduplicationApplication {
    public static void main(String[] args) {
        SpringApplication.run(DeduplicationApplication.class, args);
    }
}
