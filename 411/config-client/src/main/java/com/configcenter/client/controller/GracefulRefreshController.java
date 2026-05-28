package com.configcenter.client.controller;

import com.configcenter.client.config.GracefulRefreshHandler;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/refresh")
public class GracefulRefreshController {

    private final GracefulRefreshHandler gracefulRefreshHandler;

    public GracefulRefreshController(GracefulRefreshHandler gracefulRefreshHandler) {
        this.gracefulRefreshHandler = gracefulRefreshHandler;
    }

    @PostMapping("/graceful")
    public ResponseEntity<Map<String, Object>> triggerGracefulRefresh() {
        gracefulRefreshHandler.triggerGracefulRefresh();
        return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "优雅刷新已触发",
                "activeRequests", gracefulRefreshHandler.getActiveRequests(),
                "refreshPending", gracefulRefreshHandler.isRefreshPending()
        ));
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getRefreshStatus() {
        return ResponseEntity.ok(Map.of(
                "activeRequests", gracefulRefreshHandler.getActiveRequests(),
                "refreshPending", gracefulRefreshHandler.isRefreshPending()
        ));
    }
}
