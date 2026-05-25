package com.filetransfer.controller;

import com.filetransfer.common.Result;
import com.filetransfer.dto.CreateShareLinkRequest;
import com.filetransfer.entity.FileShareLink;
import com.filetransfer.repository.FileInfoRepository;
import com.filetransfer.service.FileShareService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.apache.tomcat.util.http.fileupload.IOUtils;
import org.springframework.web.bind.annotation.*;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;

@RestController
@RequestMapping("/share")
@RequiredArgsConstructor
public class FileShareController {
    private final FileShareService fileShareService;
    private final FileInfoRepository fileInfoRepository;

    @PostMapping("/create")
    public Result<FileShareLink> createShareLink(@Valid @RequestBody CreateShareLinkRequest request) {
        FileShareLink shareLink = fileShareService.createShareLink(request);
        return Result.success(shareLink);
    }

    @GetMapping("/info/{shareCode}")
    public Result<FileShareLink> getShareInfo(
            @PathVariable String shareCode,
            @RequestParam(required = false) String password) {
        FileShareLink shareLink = fileShareService.getShareLink(shareCode, password);
        return Result.success(shareLink);
    }

    @GetMapping("/preview/{shareCode}")
    public void previewFile(
            @PathVariable String shareCode,
            @RequestParam(required = false) String visitorInfo,
            @RequestParam(required = false) String password,
            HttpServletRequest request,
            HttpServletResponse response) {
        try {
            String ipAddress = getClientIpAddress(request);
            InputStream inputStream = fileShareService.previewFileWithWatermark(
                    shareCode, visitorInfo, ipAddress, password);

            var fileInfo = fileInfoRepository.findById(
                    fileShareService.getShareLink(shareCode, password).getFileId()).orElseThrow();

            response.setContentType(fileInfo.getContentType());
            response.setHeader("Content-Disposition", "inline; filename*=UTF-8''"
                    + URLEncoder.encode(fileInfo.getOriginalFilename(), StandardCharsets.UTF_8));

            try (OutputStream outputStream = response.getOutputStream()) {
                IOUtils.copy(inputStream, outputStream);
                outputStream.flush();
            }
        } catch (Exception e) {
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
        }
    }

    @GetMapping("/download/{shareCode}")
    public void downloadFile(
            @PathVariable String shareCode,
            @RequestParam(required = false) String password,
            HttpServletResponse response) {
        try {
            var shareLink = fileShareService.getShareLink(shareCode, password);
            var fileInfo = fileInfoRepository.findById(shareLink.getFileId()).orElseThrow();
            InputStream inputStream = fileShareService.downloadFile(shareCode, password);

            response.setContentType(fileInfo.getContentType());
            response.setHeader("Content-Disposition", "attachment; filename*=UTF-8''"
                    + URLEncoder.encode(fileInfo.getOriginalFilename(), StandardCharsets.UTF_8));

            try (OutputStream outputStream = response.getOutputStream()) {
                IOUtils.copy(inputStream, outputStream);
                outputStream.flush();
            }
        } catch (Exception e) {
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
        }
    }

    @GetMapping("/user/list")
    public Result<List<FileShareLink>> getUserShareLinks(
            @RequestParam(defaultValue = "1") Long userId) {
        List<FileShareLink> links = fileShareService.getUserShareLinks(userId);
        return Result.success(links);
    }

    @PostMapping("/deactivate/{shareCode}")
    public Result<Void> deactivateShareLink(
            @PathVariable String shareCode,
            @RequestParam(defaultValue = "1") Long userId) {
        fileShareService.deactivateShareLink(shareCode, userId);
        return Result.success();
    }

    private String getClientIpAddress(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        return ip;
    }
}
