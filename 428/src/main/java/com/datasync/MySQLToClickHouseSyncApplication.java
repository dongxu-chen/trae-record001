package com.datasync;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class MySQLToClickHouseSyncApplication {

    public static void main(String[] args) {
        SpringApplication.run(MySQLToClickHouseSyncApplication.class, args);
    }
}
