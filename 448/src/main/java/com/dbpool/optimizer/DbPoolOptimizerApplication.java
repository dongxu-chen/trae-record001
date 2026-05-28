package com.dbpool.optimizer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync
public class DbPoolOptimizerApplication {
    public static void main(String[] args) {
        SpringApplication.run(DbPoolOptimizerApplication.class, args);
    }
}
