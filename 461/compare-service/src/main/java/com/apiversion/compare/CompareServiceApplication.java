package com.apiversion.compare;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication
@EnableDiscoveryClient
@MapperScan("com.apiversion.compare.mapper")
public class CompareServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(CompareServiceApplication.class, args);
    }
}
