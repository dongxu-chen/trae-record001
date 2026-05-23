package com.emailmarketing.controller;

import com.emailmarketing.entity.EmailSendLog;
import com.emailmarketing.entity.Recipient;
import com.emailmarketing.service.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;

@RestController
@RequestMapping("/api/tracking")
public class EmailTrackingController {

    @Autowired
    private EmailSendLogService sendLogService;

    @Autowired
    private RecipientService recipientService;

    @Autowired
    private EmailTaskService emailTaskService;

    @Autowired
    private AbTestService abTestService;

    @Autowired
    private UserBehaviorService userBehaviorService;

    @GetMapping("/open")
    public ResponseEntity<byte[]> trackOpen(
            @RequestParam Long taskId,
            @RequestParam Long logId,
            @RequestParam String email,
            @RequestParam(required = false) String category) {
        
        EmailSendLog log = sendLogService.getById(logId);
        if (log != null && log.getOpened() == 0) {
            log.setOpened(1);
            log.setOpenTime(LocalDateTime.now());
            sendLogService.updateById(log);

            try {
                abTestService.recordOpen(taskId, logId);
            } catch (Exception ignored) {}

            try {
                userBehaviorService.recordBehavior(
                        log.getRecipientId(), email, taskId, 2, category, null, null);
            } catch (Exception ignored) {}
        }

        byte[] pixel = new byte[]{
                0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00,
                (byte) 0x80, 0x00, 0x00, (byte) 0xff, (byte) 0xff, (byte) 0xff,
                0x00, 0x00, 0x00, 0x21, (byte) 0xf9, 0x04, 0x01, 0x00, 0x00,
                0x00, 0x00, 0x2c, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01,
                0x00, 0x00, 0x02, 0x02, 0x44, 0x01, 0x00, 0x3b
        };

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.IMAGE_GIF);
        headers.setCacheControl("no-cache, no-store, must-revalidate");
        return new ResponseEntity<>(pixel, headers, HttpStatus.OK);
    }

    @GetMapping("/click")
    public ResponseEntity<Void> trackClick(
            @RequestParam Long taskId,
            @RequestParam Long logId,
            @RequestParam String email,
            @RequestParam String url,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String itemId) {
        
        EmailSendLog log = sendLogService.getById(logId);
        if (log != null && log.getClicked() == 0) {
            log.setClicked(1);
            log.setClickTime(LocalDateTime.now());
            sendLogService.updateById(log);

            try {
                abTestService.recordClick(taskId, logId);
            } catch (Exception ignored) {}

            try {
                userBehaviorService.recordBehavior(
                        log.getRecipientId(), email, taskId, 3, category, itemId, null);
            } catch (Exception ignored) {}
        }

        String decodedUrl = URLDecoder.decode(url, StandardCharsets.UTF_8);
        HttpHeaders headers = new HttpHeaders();
        headers.add("Location", decodedUrl);
        return new ResponseEntity<>(headers, HttpStatus.FOUND);
    }

    @PostMapping("/unsubscribe")
    public ResponseEntity<String> unsubscribePost(
            @RequestParam Long taskId,
            @RequestParam Long logId,
            @RequestParam String email) {
        return handleUnsubscribe(taskId, logId, email);
    }

    @GetMapping("/unsubscribe")
    public ResponseEntity<String> unsubscribeGet(
            @RequestParam Long taskId,
            @RequestParam Long logId,
            @RequestParam String email) {
        return handleUnsubscribe(taskId, logId, email);
    }

    private ResponseEntity<String> handleUnsubscribe(Long taskId, Long logId, String email) {
        EmailSendLog log = sendLogService.getById(logId);
        if (log == null) {
            return ResponseEntity.ok(buildUnsubscribePage("退订失败", "无效的退订请求"));
        }

        if (log.getUnsubscribed() == 1) {
            return ResponseEntity.ok(buildUnsubscribePage("退订成功", "您已成功退订，无需重复操作"));
        }

        log.setUnsubscribed(1);
        log.setUnsubscribeTime(LocalDateTime.now());
        sendLogService.updateById(log);

        Recipient recipient = recipientService.getById(log.getRecipientId());
        if (recipient != null) {
            recipient.setUnsubscribed(1);
            recipientService.updateById(recipient);
        }

        emailTaskService.handleRecipientUnsubscribe(taskId, log.getRecipientId(), email);

        return ResponseEntity.ok(buildUnsubscribePage("退订成功", "您已成功退订此邮件，将不再收到相关推送"));
    }

    private String buildUnsubscribePage(String title, String message) {
        return "<!DOCTYPE html>" +
                "<html lang=\"zh-CN\">" +
                "<head>" +
                "<meta charset=\"UTF-8\">" +
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">" +
                "<title>" + title + "</title>" +
                "<style>" +
                "body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; }" +
                ".card { background: white; border-radius: 16px; padding: 48px 32px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); text-align: center; max-width: 400px; margin: 20px; }" +
                ".icon { width: 80px; height: 80px; background: #10b981; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px; }" +
                ".icon svg { width: 40px; height: 40px; fill: white; }" +
                "h1 { color: #1f2937; margin: 0 0 12px 0; font-size: 24px; }" +
                "p { color: #6b7280; margin: 0; font-size: 16px; line-height: 1.6; }" +
                "</style>" +
                "</head>" +
                "<body>" +
                "<div class=\"card\">" +
                "<div class=\"icon\">" +
                "<svg viewBox=\"0 0 24 24\"><path d=\"M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z\"/></svg>" +
                "</div>" +
                "<h1>" + title + "</h1>" +
                "<p>" + message + "</p>" +
                "</div>" +
                "</body>" +
                "</html>";
    }
}
