package com.filetransfer.service;

import com.filetransfer.entity.FileInfo;
import com.filetransfer.repository.FileInfoRepository;
import com.filetransfer.util.TokenBucketLimitedInputStream;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.InputStream;

@Slf4j
@Service
@RequiredArgsConstructor
public class FileDownloadService {
    private final FileInfoRepository fileInfoRepository;
    private final MinIOService minIOService;
    private final AuditLogService auditLogService;

    @Value("${file.rate-limit.enabled:true}")
    private boolean rateLimitEnabled;

    @Value("${file.rate-limit.max-download-speed:10485760}")
    private long maxDownloadSpeed;

    public FileInfo getFileInfo(Long fileId) {
        return fileInfoRepository.findByIdAndIsDeletedFalse(fileId)
                .orElseThrow(() -> new RuntimeException("文件不存在"));
    }

    public InputStream downloadFile(Long fileId, Long userId) {
        FileInfo fileInfo = getFileInfo(fileId);
        InputStream inputStream = minIOService.getObject(fileInfo.getObjectName());

        if (rateLimitEnabled && maxDownloadSpeed > 0) {
            inputStream = new TokenBucketLimitedInputStream(inputStream, maxDownloadSpeed);
        }

        auditLogService.logOperation(userId, "DOWNLOAD", fileInfo.getId(),
                fileInfo.getOriginalFilename(), fileInfo.getFileSize(), "SUCCESS", null);

        return inputStream;
    }

    public InputStream downloadFileRange(Long fileId, long offset, long length, Long userId) {
        FileInfo fileInfo = getFileInfo(fileId);

        long fileSize = fileInfo.getFileSize();
        if (offset >= fileSize) {
            throw new RuntimeException("偏移量超出文件大小");
        }

        long actualLength = Math.min(length, fileSize - offset);
        InputStream inputStream = minIOService.getObjectRange(fileInfo.getObjectName(), offset, actualLength);

        if (rateLimitEnabled && maxDownloadSpeed > 0) {
            inputStream = new TokenBucketLimitedInputStream(inputStream, maxDownloadSpeed);
        }

        return inputStream;
    }

    public String getFileDownloadUrl(Long fileId) {
        FileInfo fileInfo = getFileInfo(fileId);
        return minIOService.getPresignedUrl(fileInfo.getObjectName(), 1, java.util.concurrent.TimeUnit.HOURS);
    }
}
