package com.medical.stockwarning;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class MedicineStockWarningApplication {

    public static void main(String[] args) {
        SpringApplication.run(MedicineStockWarningApplication.class, args);
    }
}
