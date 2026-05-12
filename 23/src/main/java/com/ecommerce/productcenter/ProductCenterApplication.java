package com.ecommerce.productcenter;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;

@SpringBootApplication
@EnableCaching
public class ProductCenterApplication {
    public static void main(String[] args) {
        SpringApplication.run(ProductCenterApplication.class, args);
    }
}
