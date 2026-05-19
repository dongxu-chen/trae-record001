package com.pushplatform;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@MapperScan("com.pushplatform.mapper")
public class PushServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(PushServiceApplication.class, args);
    }
}
