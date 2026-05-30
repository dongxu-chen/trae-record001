package com.hotconfig.sample;

import com.hotconfig.annotation.EnableHotConfig;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@EnableHotConfig(enableFileWatch = true, enableApollo = false)
public class HotConfigSampleApplication {

    public static void main(String[] args) {
        SpringApplication.run(HotConfigSampleApplication.class, args);
    }
}
