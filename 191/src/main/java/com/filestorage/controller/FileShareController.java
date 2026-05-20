package com.filestorage.controller;

import com.filestorage.common.Result;
import com.filestorage.dto.FileShareDTO;
import com.filestorage.entity.FileShare;
import com.filestorage.service.FileShareService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.*;

import jakarta.annotation.Resource;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/share")
public class FileShareController {

    @Resource
    private FileShareService fileShareService;

    @PostMapping("/create")
    public Result<Map<String, Object>> createShare(@RequestBody FileShareDTO dto) {
        try {
            Map<String, Object> result = fileShareService.createShare(dto);
            return Result.success(result);
        } catch (Exception e) {
            log.error("创建分享失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/info/{shareCode}")
    public Result<Map<String, Object>> getShareInfo(
            @PathVariable String shareCode,
            @RequestParam(required = false) String extractCode) {
        try {
            Map<String, Object> result = fileShareService.getShareInfo(shareCode, extractCode);
            return Result.success(result);
        } catch (Exception e) {
            log.error("获取分享信息失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/download/{shareCode}")
    public Result<String> getShareDownloadUrl(
            @PathVariable String shareCode,
            @RequestParam(required = false) String extractCode,
            @RequestParam(defaultValue = "3600") int expiresInSeconds) {
        try {
            String url = fileShareService.getShareDownloadUrl(shareCode, extractCode, expiresInSeconds);
            return Result.success(url);
        } catch (Exception e) {
            log.error("获取分享下载链接失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/list")
    public Result<Page<FileShare>> getShareList(
            @RequestParam String tenantCode,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        try {
            Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
            Page<FileShare> shareList = fileShareService.getShareList(tenantCode, pageable);
            return Result.success(shareList);
        } catch (Exception e) {
            log.error("获取分享列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping("/{shareId}")
    public Result<Void> cancelShare(
            @RequestParam String tenantCode,
            @PathVariable Long shareId) {
        try {
            fileShareService.cancelShare(tenantCode, shareId);
            return Result.success();
        } catch (Exception e) {
            log.error("取消分享失败", e);
            return Result.error(e.getMessage());
        }
    }
}
