package com.filetransfer.controller;

import com.filetransfer.entity.FileInfo;
import com.filetransfer.service.FileDownloadService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.tomcat.util.http.fileupload.IOUtils;
import org.springframework.web.bind.annotation.*;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

@Slf4j
@RestController
@RequestMapping("/download")
@RequiredArgsConstructor
public class FileDownloadController {
    private final FileDownloadService fileDownloadService;

    @GetMapping("/{fileId}")
    public void downloadFile(
            @PathVariable Long fileId,
            @RequestParam(defaultValue = "1") Long userId,
            HttpServletRequest request,
            HttpServletResponse response) {
        try {
            FileInfo fileInfo = fileDownloadService.getFileInfo(fileId);
            String fileName = URLEncoder.encode(fileInfo.getOriginalFilename(), StandardCharsets.UTF_8)
                    .replaceAll("\\+", "%20");

            String rangeHeader = request.getHeader("Range");
            if (rangeHeader != null && rangeHeader.startsWith("bytes=")) {
                handleRangeDownload(fileId, userId, fileInfo, rangeHeader, response, fileName);
            } else {
                handleFullDownload(fileId, userId, fileInfo, response, fileName);
            }
        } catch (Exception e) {
            log.error("文件下载失败", e);
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
        }
    }

    private void handleFullDownload(Long fileId, Long userId, FileInfo fileInfo,
                                    HttpServletResponse response, String fileName) throws Exception {
        response.setContentType(fileInfo.getContentType());
        response.setHeader("Content-Disposition", "attachment; filename*=UTF-8''" + fileName);
        response.setHeader("Content-Length", String.valueOf(fileInfo.getFileSize()));
        response.setHeader("Accept-Ranges", "bytes");

        try (InputStream inputStream = fileDownloadService.downloadFile(fileId, userId);
             OutputStream outputStream = response.getOutputStream()) {
            IOUtils.copy(inputStream, outputStream);
            outputStream.flush();
        }
    }

    private void handleRangeDownload(Long fileId, Long userId, FileInfo fileInfo,
                                     String rangeHeader, HttpServletResponse response, String fileName) throws Exception {
        String range = rangeHeader.substring("bytes=".length());
        String[] ranges = range.split("-");

        long start = ranges[0].isEmpty() ? 0 : Long.parseLong(ranges[0]);
        long end = ranges.length > 1 && !ranges[1].isEmpty()
                ? Long.parseLong(ranges[1])
                : fileInfo.getFileSize() - 1;

        if (start > end || start >= fileInfo.getFileSize()) {
            response.setStatus(HttpServletResponse.SC_REQUESTED_RANGE_NOT_SATISFIABLE);
            return;
        }

        long contentLength = end - start + 1;

        response.setStatus(HttpServletResponse.SC_PARTIAL_CONTENT);
        response.setContentType(fileInfo.getContentType());
        response.setHeader("Content-Disposition", "attachment; filename*=UTF-8''" + fileName);
        response.setHeader("Content-Length", String.valueOf(contentLength));
        response.setHeader("Content-Range", "bytes " + start + "-" + end + "/" + fileInfo.getFileSize());
        response.setHeader("Accept-Ranges", "bytes");

        try (InputStream inputStream = fileDownloadService.downloadFileRange(fileId, start, contentLength, userId);
             OutputStream outputStream = response.getOutputStream()) {
            IOUtils.copy(inputStream, outputStream);
            outputStream.flush();
        }
    }

    @GetMapping("/url/{fileId}")
    public String getDownloadUrl(@PathVariable Long fileId) {
        return fileDownloadService.getFileDownloadUrl(fileId);
    }
}
