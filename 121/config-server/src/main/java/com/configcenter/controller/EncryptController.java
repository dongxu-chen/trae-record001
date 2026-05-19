package com.configcenter.controller;

import org.jasypt.encryption.StringEncryptor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/encrypt")
public class EncryptController {

    private static final Logger logger = LoggerFactory.getLogger(EncryptController.class);

    @Autowired
    private StringEncryptor stringEncryptor;

    @PostMapping
    public ResponseEntity<Map<String, Object>> encrypt(@RequestBody Map<String, String> request) {
        Map<String, Object> result = new HashMap<>();

        try {
            String plainText = request.get("value");
            if (plainText == null || plainText.trim().isEmpty()) {
                result.put("status", "error");
                result.put("message", "Value cannot be empty");
                return ResponseEntity.badRequest().body(result);
            }

            String encrypted = stringEncryptor.encrypt(plainText);
            result.put("status", "success");
            result.put("encrypted", "ENC(" + encrypted + ")");
            result.put("plain", "***");
            return ResponseEntity.ok(result);

        } catch (Exception e) {
            logger.error("Error encrypting value", e);
            result.put("status", "error");
            result.put("message", e.getMessage());
            return ResponseEntity.badRequest().body(result);
        }
    }

    @PostMapping("/batch")
    public ResponseEntity<Map<String, Object>> encryptBatch(@RequestBody Map<String, String> request) {
        Map<String, Object> result = new HashMap<>();
        Map<String, String> encryptedValues = new HashMap<>();

        try {
            for (Map.Entry<String, String> entry : request.entrySet()) {
                String key = entry.getKey();
                String value = entry.getValue();
                if (value != null && !value.trim().isEmpty()) {
                    String encrypted = stringEncryptor.encrypt(value);
                    encryptedValues.put(key, "ENC(" + encrypted + ")");
                }
            }

            result.put("status", "success");
            result.put("encrypted", encryptedValues);
            return ResponseEntity.ok(result);

        } catch (Exception e) {
            logger.error("Error encrypting values", e);
            result.put("status", "error");
            result.put("message", e.getMessage());
            return ResponseEntity.badRequest().body(result);
        }
    }
}
