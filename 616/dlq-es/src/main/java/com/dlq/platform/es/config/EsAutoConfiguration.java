package com.dlq.platform.es.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.Configuration;

@Configuration
@ComponentScan(basePackages = "com.dlq.platform.es")
@ConditionalOnProperty(prefix = "elasticsearch", name = "enabled", havingValue = "true", matchIfMissing = true)
public class EsAutoConfiguration {
}
