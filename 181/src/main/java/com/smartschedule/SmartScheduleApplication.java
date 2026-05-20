package com.smartschedule;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync
public class SmartScheduleApplication {
    public static void main(String[] args) {
        SpringApplication.run(SmartScheduleApplication.class, args);
    }
}
