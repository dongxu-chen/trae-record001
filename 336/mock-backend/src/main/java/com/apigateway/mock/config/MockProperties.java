package com.apigateway.mock.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "mock")
public class MockProperties {

    private Delay delay = new Delay();
    private Error error = new Error();

    @Data
    public static class Delay {
        private long minMs = 0;
        private long maxMs = 0;
        private boolean enabled = false;
    }

    @Data
    public static class Error {
        private double rate = 0.0;
        private boolean enabled = false;
        private String message = "模拟错误";
    }
}
