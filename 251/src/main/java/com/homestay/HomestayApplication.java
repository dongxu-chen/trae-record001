package com.homestay;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@MapperScan("com.homestay.mapper")
@EnableAsync
@EnableScheduling
public class HomestayApplication {
    public static void main(String[] args) {
        SpringApplication.run(HomestayApplication.class, args);
    }
}
