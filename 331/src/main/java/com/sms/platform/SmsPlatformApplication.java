package com.sms.platform;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@MapperScan("com.sms.platform.mapper")
public class SmsPlatformApplication {
    public static void main(String[] args) {
        SpringApplication.run(SmsPlatformApplication.class, args);
    }
}
