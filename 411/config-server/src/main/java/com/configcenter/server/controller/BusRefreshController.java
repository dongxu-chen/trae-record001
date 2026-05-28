package com.configcenter.server.controller;

import com.configcenter.server.service.BusRefreshService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/config/bus")
public class BusRefreshController {

    @Autowired
    private BusRefreshService busRefreshService;

    @PostMapping("/refresh/{application}")
    public ResponseEntity<Map<String, Object>> refreshConfig(@PathVariable String application) {
        busRefreshService.refreshConfig(application);
        return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "配置刷新事件已发布",
                "application", application
        ));
    }

    @PostMapping("/refresh-all")
    public ResponseEntity<Map<String, Object>> refreshAllConfigs() {
        busRefreshService.refreshAllConfigs();
        return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "全局配置刷新事件已发布"
        ));
    }

    @PostMapping("/service/{serviceName}")
    public ResponseEntity<Map<String, Object>> refreshConfigByService(
            @PathVariable String serviceName) {
        busRefreshService.refreshConfigByService(serviceName);
        return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "服务配置刷新事件已发布",
                "service", serviceName
        ));
    }

    @PostMapping("/custom-message")
    public ResponseEntity<Map<String, Object>> sendCustomBusMessage(
            @RequestBody Map<String, String> request) {
        String routingKey = request.get("routingKey");
        String message = request.get("message");
        busRefreshService.sendCustomBusMessage(routingKey, message);
        return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "自定义Bus消息已发送",
                "routingKey", routingKey
        ));
    }
}
