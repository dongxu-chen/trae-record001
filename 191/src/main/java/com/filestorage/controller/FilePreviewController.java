package com.filestorage.controller;

import com.filestorage.common.Result;
import com.filestorage.entity.FileInfo;
import com.filestorage.entity.FileVersion;
import com.filestorage.service.FilePreviewService;
import com.filestorage.service.FileService;
import com.filestorage.service.FileVersionService;
import com.filestorage.util.FileUtil;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletResponse;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/preview")
public class FilePreviewController {

    @Resource
    private FilePreviewService filePreviewService;

    @Resource
    private FileService fileService;

    @Resource
    private FileVersionService fileVersionService;

    @GetMapping("/info/{fileId}")
    public Result<Map<String, Object>> getPreviewInfo(
            @RequestParam String tenantCode,
            @PathVariable Long fileId,
            @RequestParam(required = false) String username,
            HttpServletRequest request) {
        try {
            String ip = getClientIp(request);
            Map<String, Object> previewInfo = filePreviewService.getPreviewInfo(tenantCode, fileId, username, ip);
            return Result.success(previewInfo);
        } catch (Exception e) {
            log.error("获取预览信息失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{fileId}")
    public void previewFile(
            @RequestParam String tenantCode,
            @PathVariable Long fileId,
            @RequestParam(required = false) String username,
            HttpServletRequest request,
            HttpServletResponse response) {
        try (InputStream inputStream = filePreviewService.previewFile(tenantCode, fileId, username, getClientIp(request));
             OutputStream outputStream = response.getOutputStream()) {

            FileInfo fileInfo = fileService.getFileById(tenantCode, fileId);
            String extension = fileInfo.getFileExtension();

            setResponseContentType(response, extension);
            response.setHeader("Content-Disposition", "inline; filename=\"" + fileInfo.getFileName() + "\"");
            response.setContentLengthLong(fileInfo.getFileSize());

            byte[] buffer = new byte[8192];
            int bytesRead;
            while ((bytesRead = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, bytesRead);
            }
            outputStream.flush();
        } catch (Exception e) {
            log.error("文件预览失败", e);
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
        }
    }

    @GetMapping("/version/{fileId}/{versionNumber}")
    public void previewVersion(
            @RequestParam String tenantCode,
            @PathVariable Long fileId,
            @PathVariable Integer versionNumber,
            @RequestParam(required = false) String username,
            HttpServletRequest request,
            HttpServletResponse response) {
        try (InputStream inputStream = filePreviewService.previewVersion(
                tenantCode, fileId, versionNumber, username, getClientIp(request));
             OutputStream outputStream = response.getOutputStream()) {

            FileVersion version = fileVersionService.getVersion(tenantCode, fileId, versionNumber);
            String extension = version.getFileExtension();

            setResponseContentType(response, extension);
            response.setHeader("Content-Disposition",
                    "inline; filename=\"v" + versionNumber + "_" + version.getFileName() + "\"");
            response.setContentLengthLong(version.getFileSize());

            byte[] buffer = new byte[8192];
            int bytesRead;
            while ((bytesRead = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, bytesRead);
            }
            outputStream.flush();
        } catch (Exception e) {
            log.error("版本预览失败", e);
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
        }
    }

    @GetMapping("/office/{fileId}")
    public Result<String> getOfficePreviewUrl(
            @RequestParam String tenantCode,
            @PathVariable Long fileId) {
        try {
            String url = filePreviewService.getOfficePreviewUrl(tenantCode, fileId);
            return Result.success(url);
        } catch (Exception e) {
            log.error("获取Office预览链接失败", e);
            return Result.error(e.getMessage());
        }
    }

    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        return ip;
    }

    private void setResponseContentType(HttpServletResponse response, String extension) {
        if (FileUtil.isImageFile(extension)) {
            response.setContentType("image/jpeg");
        } else if ("pdf".equalsIgnoreCase(extension)) {
            response.setContentType("application/pdf");
        } else {
            response.setContentType("application/octet-stream");
        }
    }
}
