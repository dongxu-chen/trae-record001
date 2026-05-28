package com.ratelimit.center;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class RateLimitCenterApplication {

    public static void main(String[] args) {
        SpringApplication.run(RateLimitCenterApplication.class, args);
    }
}
