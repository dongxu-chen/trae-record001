package com.coupon.abtest.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "coupon.ab-test")
public class ABTestConfig {

    private String defaultExperiment = "default_coupon_exp";

    private String trafficSalt = "coupon_ab_test_2024";
}
