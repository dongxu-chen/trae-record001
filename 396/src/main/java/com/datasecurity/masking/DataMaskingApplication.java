package com.datasecurity.masking;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class DataMaskingApplication {

    public static void main(String[] args) {
        SpringApplication.run(DataMaskingApplication.class, args);
    }
}
