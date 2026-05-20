package com.filestorage.controller;

import com.filestorage.common.Result;
import com.filestorage.entity.FileInfo;
import com.filestorage.service.FileService;
import com.filestorage.service.MinioStorageService;
import com.filestorage.service.RecycleBinService;
import com.filestorage.service.ThumbnailService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.*;

import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletResponse;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URLEncoder;

@Slf4j
@RestController
@RequestMapping("/api/file")
public class FileController {

    @Resource
    private FileService fileService;

    @Resource
    private ThumbnailService thumbnailService;

    @Resource
    private RecycleBinService recycleBinService;

    @Resource
    private MinioStorageService minioStorageService;

    @GetMapping("/list")
    public Result<Page<FileInfo>> getFileList(
            @RequestParam String tenantCode,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        try {
            Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
            Page<FileInfo> fileList = fileService.getFileList(tenantCode, pageable);
            return Result.success(fileList);
        } catch (Exception e) {
            log.error("获取文件列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{fileId}")
    public Result<FileInfo> getFileInfo(
            @RequestParam String tenantCode,
            @PathVariable Long fileId) {
        try {
            FileInfo fileInfo = fileService.getFileById(tenantCode, fileId);
            return Result.success(fileInfo);
        } catch (Exception e) {
            log.error("获取文件信息失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/download/{fileId}")
    public void downloadFile(
            @RequestParam String tenantCode,
            @PathVariable Long fileId,
            HttpServletResponse response) {
        try (InputStream inputStream = fileService.downloadFile(tenantCode, fileId);
             OutputStream outputStream = response.getOutputStream()) {
            FileInfo fileInfo = fileService.getFileById(tenantCode, fileId);

            response.setContentType("application/octet-stream");
            response.setHeader("Content-Disposition",
                    "attachment; filename=\"" + URLEncoder.encode(fileInfo.getFileName(), "UTF-8") + "\"");
            response.setContentLengthLong(fileInfo.getFileSize());

            byte[] buffer = new byte[8192];
            int bytesRead;
            while ((bytesRead = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, bytesRead);
            }
            outputStream.flush();
        } catch (Exception e) {
            log.error("下载文件失败", e);
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
        }
    }

    @GetMapping("/url/{fileId}")
    public Result<String> getDownloadUrl(
            @RequestParam String tenantCode,
            @PathVariable Long fileId,
            @RequestParam(defaultValue = "3600") int expiresInSeconds) {
        try {
            String url = fileService.getDownloadUrl(tenantCode, fileId, expiresInSeconds);
            return Result.success(url);
        } catch (Exception e) {
            log.error("获取下载链接失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/thumbnail/{fileMd5}")
    public void getThumbnail(
            @RequestParam String tenantCode,
            @PathVariable String fileMd5,
            HttpServletResponse response) {
        try (InputStream inputStream = thumbnailService.getThumbnail(tenantCode, fileMd5);
             OutputStream outputStream = response.getOutputStream()) {
            response.setContentType("image/jpeg");
            byte[] buffer = new byte[8192];
            int bytesRead;
            while ((bytesRead = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, bytesRead);
            }
            outputStream.flush();
        } catch (Exception e) {
            log.error("获取缩略图失败", e);
            response.setStatus(HttpServletResponse.SC_NOT_FOUND);
        }
    }

    @DeleteMapping("/{fileId}")
    public Result<Void> deleteFile(
            @RequestParam String tenantCode,
            @PathVariable Long fileId,
            @RequestParam(required = false) String deleteUser) {
        try {
            recycleBinService.moveToRecycleBin(tenantCode, fileId, deleteUser);
            return Result.success();
        } catch (Exception e) {
            log.error("删除文件失败", e);
            return Result.error(e.getMessage());
        }
    }
}
