package com.health.task;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class TaskHealthApplication {
    public static void main(String[] args) {
        SpringApplication.run(TaskHealthApplication.class, args);
    }
}
