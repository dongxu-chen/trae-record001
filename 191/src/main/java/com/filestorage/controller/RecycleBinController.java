package com.filestorage.controller;

import com.filestorage.common.Result;
import com.filestorage.entity.RecycleBin;
import com.filestorage.service.RecycleBinService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.*;

import jakarta.annotation.Resource;

@Slf4j
@RestController
@RequestMapping("/api/recycle")
public class RecycleBinController {

    @Resource
    private RecycleBinService recycleBinService;

    @GetMapping("/list")
    public Result<Page<RecycleBin>> getRecycleBinList(
            @RequestParam String tenantCode,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        try {
            Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
            Page<RecycleBin> recycleBinList = recycleBinService.getRecycleBinList(tenantCode, pageable);
            return Result.success(recycleBinList);
        } catch (Exception e) {
            log.error("获取回收站列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/restore/{recycleId}")
    public Result<Void> restoreFile(
            @RequestParam String tenantCode,
            @PathVariable Long recycleId) {
        try {
            recycleBinService.restoreFile(tenantCode, recycleId);
            return Result.success();
        } catch (Exception e) {
            log.error("恢复文件失败", e);
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping("/{recycleId}")
    public Result<Void> permanentlyDelete(
            @RequestParam String tenantCode,
            @PathVariable Long recycleId) {
        try {
            recycleBinService.permanentlyDelete(tenantCode, recycleId);
            return Result.success();
        } catch (Exception e) {
            log.error("永久删除文件失败", e);
            return Result.error(e.getMessage());
        }
    }
}
