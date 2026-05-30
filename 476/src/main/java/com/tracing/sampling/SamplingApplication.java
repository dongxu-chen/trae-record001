package com.tracing.sampling;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class SamplingApplication {

    public static void main(String[] args) {
        SpringApplication.run(SamplingApplication.class, args);
    }
}
