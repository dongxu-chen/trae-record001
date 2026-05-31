package com.datacheck;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class DataSyncCheckerApplication {

    public static void main(String[] args) {
        SpringApplication.run(DataSyncCheckerApplication.class, args);
    }
}
