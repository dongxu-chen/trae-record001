package com.apiversion.business.v2.config;

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
                        .title("业务服务V2 API")
                        .version("2.0.0")
                        .description("业务服务V2版本 - 提供用户和订单的v2版本接口")
                        .contact(new Contact()
                                .name("Business Service V2")
                                .email("admin@apiversion.com")));
    }
}
