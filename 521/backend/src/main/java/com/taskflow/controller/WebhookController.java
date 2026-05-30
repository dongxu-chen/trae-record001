package com.taskflow.controller;

import com.taskflow.dto.ApiResponse;
import com.taskflow.dto.TriggerDto;
import com.taskflow.service.TriggerService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.BufferedReader;
import java.io.IOException;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequestMapping("/webhook")
@RequiredArgsConstructor
public class WebhookController {

    private final TriggerService triggerService;

    @PostMapping("/{webhookPath}")
    public ResponseEntity<ApiResponse<TriggerDto>> receiveWebhook(
            @PathVariable String webhookPath,
            HttpServletRequest request) throws IOException {

        String payload = request.getReader().lines().collect(Collectors.joining());
        String signature = request.getHeader("X-Webhook-Signature");

        log.info("Webhook received: path={}, payloadLength={}", webhookPath, payload.length());

        try {
            TriggerDto result = triggerService.handleWebhook(webhookPath, payload, signature);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (RuntimeException e) {
            log.warn("Webhook handling failed: {}", e.getMessage());
            return ResponseEntity.status(400)
                    .body(ApiResponse.error(400, e.getMessage()));
        }
    }
}
