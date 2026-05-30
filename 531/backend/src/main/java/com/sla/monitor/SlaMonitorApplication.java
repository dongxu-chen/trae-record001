package com.sla.monitor;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class SlaMonitorApplication {

    public static void main(String[] args) {
        SpringApplication.run(SlaMonitorApplication.class, args);
    }
}
