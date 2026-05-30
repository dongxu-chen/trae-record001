package com.apiversion.version.config;

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
                        .title("版本管理服务 API")
                        .version("1.0.0")
                        .description("API版本管理服务 - 提供版本CRUD、发布、废弃、下线等功能")
                        .contact(new Contact()
                                .name("API Version Manager")
                                .email("admin@apiversion.com")));
    }
}
