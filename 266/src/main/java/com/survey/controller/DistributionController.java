package com.survey.controller;

import com.survey.service.DistributionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/distribution")
@RequiredArgsConstructor
@Tag(name = "问卷分发", description = "问卷链接、二维码生成接口")
public class DistributionController {

    private final DistributionService distributionService;

    @GetMapping("/link/{shareCode}")
    @Operation(summary = "获取问卷链接")
    public ResponseEntity<Map<String, String>> getSurveyLink(@PathVariable String shareCode) {
        Map<String, String> response = new HashMap<>();
        response.put("link", distributionService.getSurveyLink(shareCode));
        return ResponseEntity.ok(response);
    }

    @GetMapping("/qrcode/{surveyId}")
    @Operation(summary = "获取问卷二维码")
    public ResponseEntity<Map<String, String>> getQRCode(@PathVariable String surveyId) {
        String qrCodeBase64 = distributionService.generateQRCode(surveyId);
        Map<String, String> response = new HashMap<>();
        response.put("qrcode", qrCodeBase64);
        response.put("mimeType", "image/png");
        return ResponseEntity.ok(response);
    }

    @GetMapping(value = "/qrcode/{surveyId}/image", produces = MediaType.IMAGE_PNG_VALUE)
    @Operation(summary = "获取问卷二维码图片")
    public ResponseEntity<byte[]> getQRCodeImage(@PathVariable String surveyId) {
        String qrCodeBase64 = distributionService.generateQRCode(surveyId);
        byte[] imageBytes = Base64.getDecoder().decode(qrCodeBase64);
        return ResponseEntity.ok(imageBytes);
    }
}
