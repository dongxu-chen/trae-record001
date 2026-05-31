package com.depguard;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync
public class DepGuardApplication {

    public static void main(String[] args) {
        SpringApplication.run(DepGuardApplication.class, args);
    }
}
