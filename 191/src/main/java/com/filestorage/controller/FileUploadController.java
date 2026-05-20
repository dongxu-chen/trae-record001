package com.filestorage.controller;

import com.filestorage.common.Result;
import com.filestorage.dto.FileUploadDTO;
import com.filestorage.entity.FileInfo;
import com.filestorage.service.FileUploadService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import jakarta.annotation.Resource;
import java.io.IOException;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/upload")
public class FileUploadController {

    @Resource
    private FileUploadService fileUploadService;

    @GetMapping("/check")
    public Result<Map<String, Object>> checkFile(
            @RequestParam String tenantCode,
            @RequestParam String fileMd5,
            @RequestParam(required = false) String fileName) {
        try {
            Map<String, Object> result = fileUploadService.checkFileByMd5(tenantCode, fileMd5, fileName);
            return Result.success(result);
        } catch (Exception e) {
            log.error("文件检查失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/init")
    public Result<String> initUpload(@RequestBody FileUploadDTO dto) {
        try {
            String uploadId = fileUploadService.initUpload(dto);
            return Result.success(uploadId);
        } catch (Exception e) {
            log.error("初始化上传失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/chunk")
    public Result<Map<String, Object>> uploadChunk(
            @RequestParam String tenantCode,
            @RequestParam String uploadId,
            @RequestParam String fileMd5,
            @RequestParam String fileName,
            @RequestParam int chunkNumber,
            @RequestParam int totalChunks,
            @RequestParam long chunkSize,
            @RequestParam(required = false) String uploadUser,
            @RequestParam("file") MultipartFile file) {
        try {
            Map<String, Object> result = fileUploadService.uploadChunk(
                    tenantCode, uploadId, file, chunkNumber, totalChunks,
                    chunkSize, fileMd5, fileName, uploadUser);
            return Result.success(result);
        } catch (IOException e) {
            log.error("上传分片失败", e);
            return Result.error("文件读取失败");
        } catch (Exception e) {
            log.error("上传分片失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/merge")
    public Result<FileInfo> mergeChunks(
            @RequestParam String tenantCode,
            @RequestParam String uploadId,
            @RequestParam String fileMd5,
            @RequestParam String fileName,
            @RequestParam(required = false) String uploadUser) {
        try {
            FileInfo fileInfo = fileUploadService.mergeChunks(tenantCode, uploadId, fileMd5, fileName, uploadUser);
            return Result.success(fileInfo);
        } catch (Exception e) {
            log.error("合并分片失败", e);
            return Result.error(e.getMessage());
        }
    }
}
