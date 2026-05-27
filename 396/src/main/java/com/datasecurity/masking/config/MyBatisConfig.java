package com.datasecurity.masking.config;

import com.datasecurity.masking.interceptor.MyBatisMaskInterceptor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class MyBatisConfig {

    @Bean
    public MyBatisMaskInterceptor myBatisMaskInterceptor() {
        return new MyBatisMaskInterceptor();
    }
}
