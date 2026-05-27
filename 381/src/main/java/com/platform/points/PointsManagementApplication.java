package com.platform.points;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@MapperScan("com.platform.points.mapper")
public class PointsManagementApplication {

    public static void main(String[] args) {
        SpringApplication.run(PointsManagementApplication.class, args);
    }
}
