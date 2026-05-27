package com.security.replayguard;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class ReplayGuardApplication {

    public static void main(String[] args) {
        SpringApplication.run(ReplayGuardApplication.class, args);
    }
}
