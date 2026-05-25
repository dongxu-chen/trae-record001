package com.filetransfer.controller;

import com.filetransfer.common.Result;
import com.filetransfer.entity.FileInfo;
import com.filetransfer.repository.FileInfoRepository;
import com.filetransfer.service.MinIOService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.concurrent.TimeUnit;

@RestController
@RequestMapping("/files")
@RequiredArgsConstructor
public class FileController {
    private final FileInfoRepository fileInfoRepository;
    private final MinIOService minIOService;

    @GetMapping("/user/{userId}")
    public Result<List<FileInfo>> getUserFiles(@PathVariable Long userId) {
        List<FileInfo> files = fileInfoRepository.findByUserIdAndIsDeletedFalse(userId);
        files.forEach(file -> {
            String url = minIOService.getPresignedUrl(file.getObjectName(), 1, TimeUnit.HOURS);
            file.setFileUrl(url);
        });
        return Result.success(files);
    }

    @GetMapping("/{fileId}")
    public Result<FileInfo> getFileInfo(@PathVariable Long fileId) {
        FileInfo fileInfo = fileInfoRepository.findByIdAndIsDeletedFalse(fileId)
                .orElseThrow(() -> new RuntimeException("文件不存在"));
        String url = minIOService.getPresignedUrl(fileInfo.getObjectName(), 1, TimeUnit.HOURS);
        fileInfo.setFileUrl(url);
        return Result.success(fileInfo);
    }

    @DeleteMapping("/{fileId}")
    public Result<Void> deleteFile(@PathVariable Long fileId, @RequestParam(defaultValue = "1") Long userId) {
        FileInfo fileInfo = fileInfoRepository.findByIdAndIsDeletedFalse(fileId)
                .orElseThrow(() -> new RuntimeException("文件不存在"));

        if (!fileInfo.getUserId().equals(userId)) {
            return Result.error("无权限删除");
        }

        fileInfo.setIsDeleted(true);
        fileInfoRepository.save(fileInfo);

        return Result.success();
    }
}
