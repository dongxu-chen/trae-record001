package com.apigateway.mock.common;

import com.apigateway.mock.config.MockProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Random;

@Slf4j
@Component
@RequiredArgsConstructor
public class MockService {

    private final MockProperties mockProperties;
    private final Random random = new Random();

    public void simulateDelay() {
        if (!mockProperties.getDelay().isEnabled()) {
            return;
        }
        long minMs = mockProperties.getDelay().getMinMs();
        long maxMs = mockProperties.getDelay().getMaxMs();
        if (maxMs <= minMs) {
            sleep(minMs);
            return;
        }
        long delay = minMs + (long) (random.nextDouble() * (maxMs - minMs));
        sleep(delay);
    }

    private void sleep(long ms) {
        if (ms <= 0) {
            return;
        }
        try {
            log.debug("模拟延迟: {}ms", ms);
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    public void simulateError() {
        if (!mockProperties.getError().isEnabled()) {
            return;
        }
        double rate = mockProperties.getError().getRate();
        if (rate <= 0) {
            return;
        }
        if (random.nextDouble() < rate) {
            String message = mockProperties.getError().getMessage();
            log.warn("模拟错误: {}", message);
            throw new RuntimeException(message);
        }
    }

    public void simulate() {
        simulateDelay();
        simulateError();
    }
}
