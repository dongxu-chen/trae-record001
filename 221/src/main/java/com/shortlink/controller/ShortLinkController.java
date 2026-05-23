package com.shortlink.controller;

import com.shortlink.common.Result;
import com.shortlink.dto.BatchCreateResult;
import com.shortlink.dto.CreateShortLinkRequest;
import com.shortlink.dto.HourlyStatsResponse;
import com.shortlink.dto.StatsResponse;
import com.shortlink.entity.ShortLink;
import com.shortlink.service.AccessLogService;
import com.shortlink.service.ShortLinkService;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@RestController
@RequestMapping("/api/shortlink")
@RequiredArgsConstructor
public class ShortLinkController {

    private final ShortLinkService shortLinkService;
    private final AccessLogService accessLogService;

    @PostMapping("/create")
    public Result<String> createShortLink(@Valid @RequestBody CreateShortLinkRequest request) {
        String shortUrl = shortLinkService.createShortLink(request);
        return Result.success(shortUrl);
    }

    @PostMapping(value = "/batch-create", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<BatchCreateResult> batchCreateShortLink(@RequestParam("file") MultipartFile file) throws IOException {
        if (file.isEmpty()) {
            return Result.error("上传文件不能为空");
        }
        String filename = file.getOriginalFilename();
        if (filename == null || !filename.toLowerCase().endsWith(".csv")) {
            return Result.error("仅支持CSV格式文件");
        }
        BatchCreateResult result = shortLinkService.batchCreateShortLink(file);
        return Result.success(result);
    }

    @GetMapping("/batch-export/{shortCode}")
    public void exportMappingCsv(@PathVariable String shortCode,
                                 HttpServletResponse response) throws IOException {
        ShortLink shortLink = shortLinkService.getShortLinkInfo(shortCode);
        BatchCreateResult.ShortLinkMapping mapping = new BatchCreateResult.ShortLinkMapping(
                shortLink.getOriginUrl(),
                shortLink.getShortCode(),
                "http://localhost:8080/" + shortLink.getShortCode(),
                shortLink.getDescription()
        );
        byte[] csvData = shortLinkService.generateMappingCsv(java.util.Collections.singletonList(mapping));

        String filename = "shortlink_mapping_" + shortCode + "_" +
                LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss")) + ".csv";

        response.setContentType("text/csv;charset=UTF-8");
        response.setHeader(HttpHeaders.CONTENT_DISPOSITION,
                "attachment; filename=" + URLEncoder.encode(filename, StandardCharsets.UTF_8));
        response.getOutputStream().write(csvData);
        response.getOutputStream().flush();
    }

    @GetMapping("/info/{shortCode}")
    public Result<ShortLink> getShortLinkInfo(@PathVariable String shortCode) {
        ShortLink shortLink = shortLinkService.getShortLinkInfo(shortCode);
        return Result.success(shortLink);
    }

    @GetMapping("/stats/{shortCode}")
    public Result<StatsResponse> getStats(@PathVariable String shortCode,
                                          @RequestParam(defaultValue = "7") int days) {
        if (days <= 0 || days > 365) {
            days = 7;
        }
        StatsResponse stats = accessLogService.getStats(shortCode, days);
        return Result.success(stats);
    }

    @GetMapping("/stats-hourly/{shortCode}")
    public Result<HourlyStatsResponse> getHourlyStats(@PathVariable String shortCode,
                                                       @RequestParam(defaultValue = "7") int days) {
        if (days <= 0 || days > 30) {
            days = 7;
        }
        HourlyStatsResponse stats = accessLogService.getHourlyStats(shortCode, days);
        return Result.success(stats);
    }

    @GetMapping("/export/{shortCode}")
    public void exportStatsCsv(@PathVariable String shortCode,
                               @RequestParam(defaultValue = "7") int days,
                               HttpServletResponse response) throws IOException {
        if (days <= 0 || days > 365) {
            days = 7;
        }

        byte[] csvData = accessLogService.exportStatsCsv(shortCode, days);

        String filename = "shortlink_stats_" + shortCode + "_" + days + "days_" +
                LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss")) + ".csv";

        response.setContentType("text/csv;charset=UTF-8");
        response.setHeader(HttpHeaders.CONTENT_DISPOSITION,
                "attachment; filename=" + URLEncoder.encode(filename, StandardCharsets.UTF_8));
        response.getOutputStream().write(csvData);
        response.getOutputStream().flush();
    }

    @DeleteMapping("/cleanup-expired")
    public Result<Integer> cleanupExpiredLinks() {
        int count = shortLinkService.deleteExpiredLinks();
        return Result.success(count);
    }
}
