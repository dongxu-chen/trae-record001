package com.emailmarketing;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@MapperScan("com.emailmarketing.mapper")
public class EmailMarketingApplication {
    public static void main(String[] args) {
        SpringApplication.run(EmailMarketingApplication.class, args);
    }
}
