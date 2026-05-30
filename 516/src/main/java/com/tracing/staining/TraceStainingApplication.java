package com.tracing.staining;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync
public class TraceStainingApplication {

    public static void main(String[] args) {
        SpringApplication.run(TraceStainingApplication.class, args);
    }
}
