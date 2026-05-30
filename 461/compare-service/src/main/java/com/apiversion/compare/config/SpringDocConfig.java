package com.apiversion.compare.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class SpringDocConfig {

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("版本对比服务 API")
                        .version("1.0.0")
                        .description("API版本对比服务 - 提供OpenAPI差异对比、兼容性检测等功能")
                        .contact(new Contact()
                                .name("API Version Manager")
                                .email("admin@apiversion.com")));
    }
}
