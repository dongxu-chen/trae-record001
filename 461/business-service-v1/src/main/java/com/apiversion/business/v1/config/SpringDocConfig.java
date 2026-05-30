package com.apiversion.business.v1.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import org.springdoc.core.GroupedOpenApi;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class SpringDocConfig {

    @Bean
    public GroupedOpenApi v1Api() {
        return GroupedOpenApi.builder()
                .group("v1")
                .pathsToMatch("/**")
                .packagesToScan("com.apiversion.business.v1.controller")
                .build();
    }

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("业务服务V1 API")
                        .version("1.0.0")
                        .description("业务服务V1 - 提供用户和订单的CRUD接口")
                        .contact(new Contact()
                                .name("API Version Manager")
                                .email("admin@apiversion.com")));
    }
}
