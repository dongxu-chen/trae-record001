package com.property.repair;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class RepairSystemApplication {

    public static void main(String[] args) {
        SpringApplication.run(RepairSystemApplication.class, args);
    }

}
