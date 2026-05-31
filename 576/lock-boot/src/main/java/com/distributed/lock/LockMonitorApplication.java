package com.distributed.lock;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.data.elasticsearch.ElasticsearchDataAutoConfiguration;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication(exclude = {ElasticsearchDataAutoConfiguration.class})
@ComponentScan(basePackages = "com.distributed.lock")
public class LockMonitorApplication {

    public static void main(String[] args) {
        SpringApplication.run(LockMonitorApplication.class, args);
    }
}