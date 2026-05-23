package com.gateway.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Data
@Configuration
@ConfigurationProperties(prefix = "gateway")
public class GatewayProperties {

    private Jwt jwt = new Jwt();
    private RateLimit rateLimit = new RateLimit();
    private Log log = new Log();
    private Auth auth = new Auth();
    private CircuitBreaker circuitBreaker = new CircuitBreaker();
    private GrayRelease grayRelease = new GrayRelease();
    private Metrics metrics = new Metrics();

    @Data
    public static class Jwt {
        private String secret = "default-secret-key-must-be-at-least-32-characters";
        private String issuer = "api-gateway";
        private long expiration = 3600000;
    }

    @Data
    public static class RateLimit {
        private boolean enabled = true;
        private int requestsPerSecond = 10;
        private int windowSizeInSeconds = 1;
    }

    @Data
    public static class Log {
        private boolean enabled = true;
        private List<String> maskFields = new ArrayList<>();
        private int maxBodySize = 4096;
    }

    @Data
    public static class Auth {
        private List<String> excludePaths = new ArrayList<>();
    }

    @Data
    public static class CircuitBreaker {
        private boolean enabled = true;
        private float failureRateThreshold = 50.0f;
        private int waitDurationInOpenState = 30;
        private int permittedCallsInHalfOpenState = 3;
        private int slidingWindowSize = 10;
        private int minimumNumberOfCalls = 5;
        private int slowCallDurationThreshold = 5000;
        private float slowCallRateThreshold = 50.0f;
    }

    @Data
    public static class GrayRelease {
        private boolean enabled = true;
        private String versionHeader = "X-API-Version";
        private Map<String, String> versionRoutes = new HashMap<>();
    }

    @Data
    public static class Metrics {
        private boolean enabled = true;
    }
}
