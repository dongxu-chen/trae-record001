package com.filestorage.controller;

import com.filestorage.common.Result;
import com.filestorage.dto.FileVersionDTO;
import com.filestorage.entity.FileInfo;
import com.filestorage.entity.FileVersion;
import com.filestorage.service.FileVersionService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletResponse;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URLEncoder;
import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/version")
public class FileVersionController {

    @Resource
    private FileVersionService fileVersionService;

    @GetMapping("/list/{fileId}")
    public Result<List<FileVersion>> getVersionList(
            @RequestParam String tenantCode,
            @PathVariable Long fileId) {
        try {
            List<FileVersion> versions = fileVersionService.getVersionList(tenantCode, fileId);
            return Result.success(versions);
        } catch (Exception e) {
            log.error("获取版本列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{fileId}/{versionNumber}")
    public Result<FileVersion> getVersion(
            @RequestParam String tenantCode,
            @PathVariable Long fileId,
            @PathVariable Integer versionNumber) {
        try {
            FileVersion version = fileVersionService.getVersion(tenantCode, fileId, versionNumber);
            return Result.success(version);
        } catch (Exception e) {
            log.error("获取版本信息失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/rollback/{fileId}/{versionNumber}")
    public Result<FileInfo> rollbackToVersion(
            @RequestParam String tenantCode,
            @PathVariable Long fileId,
            @PathVariable Integer versionNumber,
            @RequestParam(required = false) String operator) {
        try {
            FileInfo fileInfo = fileVersionService.rollbackToVersion(tenantCode, fileId, versionNumber, operator);
            return Result.success(fileInfo);
        } catch (Exception e) {
            log.error("回滚版本失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/download/{fileId}/{versionNumber}")
    public void downloadVersion(
            @RequestParam String tenantCode,
            @PathVariable Long fileId,
            @PathVariable Integer versionNumber,
            HttpServletResponse response) {
        try (InputStream inputStream = fileVersionService.downloadVersion(tenantCode, fileId, versionNumber);
             OutputStream outputStream = response.getOutputStream()) {

            FileVersion version = fileVersionService.getVersion(tenantCode, fileId, versionNumber);

            response.setContentType("application/octet-stream");
            response.setHeader("Content-Disposition",
                    "attachment; filename=\"" + URLEncoder.encode(
                            "v" + versionNumber + "_" + version.getFileName(), "UTF-8") + "\"");
            response.setContentLengthLong(version.getFileSize());

            byte[] buffer = new byte[8192];
            int bytesRead;
            while ((bytesRead = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, bytesRead);
            }
            outputStream.flush();
        } catch (Exception e) {
            log.error("下载版本失败", e);
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
        }
    }

    @GetMapping("/url/{fileId}/{versionNumber}")
    public Result<String> getVersionDownloadUrl(
            @RequestParam String tenantCode,
            @PathVariable Long fileId,
            @PathVariable Integer versionNumber,
            @RequestParam(defaultValue = "3600") int expiresInSeconds) {
        try {
            String url = fileVersionService.getVersionDownloadUrl(tenantCode, fileId, versionNumber, expiresInSeconds);
            return Result.success(url);
        } catch (Exception e) {
            log.error("获取版本下载链接失败", e);
            return Result.error(e.getMessage());
        }
    }
}
