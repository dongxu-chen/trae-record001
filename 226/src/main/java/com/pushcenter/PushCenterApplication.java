package com.pushcenter;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class PushCenterApplication {

    public static void main(String[] args) {
        SpringApplication.run(PushCenterApplication.class, args);
    }
}
