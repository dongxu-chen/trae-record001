package com.replay.detector;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class ReplayDetectorApplication {
    public static void main(String[] args) {
        SpringApplication.run(ReplayDetectorApplication.class, args);
    }
}
