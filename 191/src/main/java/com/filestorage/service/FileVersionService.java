package com.filestorage.service;

import com.filestorage.dto.FileVersionDTO;
import com.filestorage.entity.FileInfo;
import com.filestorage.entity.FileVersion;
import com.filestorage.repository.FileInfoRepository;
import com.filestorage.repository.FileVersionRepository;
import com.filestorage.util.FileUtil;
import com.filestorage.util.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import jakarta.annotation.Resource;
import java.io.InputStream;
import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
public class FileVersionService {

    private static final int MAX_VERSIONS = 10;
    private static final String FILE_CACHE_PREFIX = "file:info:";

    @Resource
    private FileVersionRepository fileVersionRepository;

    @Resource
    private FileInfoRepository fileInfoRepository;

    @Resource
    private MinioStorageService minioStorageService;

    @Resource
    private TenantService tenantService;

    @Resource
    private RedisUtil redisUtil;

    @Transactional
    public FileVersion saveVersion(String tenantCode, FileInfo fileInfo, String uploadUser,
                                   String changeDescription) {
        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();

        Integer currentMaxVersion = fileVersionRepository.findMaxVersionNumber(fileInfo.getId());
        int newVersionNumber = currentMaxVersion + 1;

        String versionPath = "versions/" + fileInfo.getId() + "/" + newVersionNumber + "/" +
                FileUtil.generateObjectPath(tenantCode, fileInfo.getFileMd5(), fileInfo.getFileName());

        String bucketName = minioStorageService.getBucketName(tenantCode);
        try (InputStream inputStream = minioStorageService.downloadFile(bucketName, fileInfo.getFilePath())) {
            minioStorageService.uploadFile(bucketName, versionPath, inputStream,
                    fileInfo.getFileSize(), "application/octet-stream");
        } catch (Exception e) {
            log.error("保存文件版本失败: fileId={}, version={}", fileInfo.getId(), newVersionNumber, e);
            throw new RuntimeException("保存文件版本失败", e);
        }

        FileVersion fileVersion = new FileVersion();
        fileVersion.setTenantId(tenantId);
        fileVersion.setFileId(fileInfo.getId());
        fileVersion.setVersionNumber(newVersionNumber);
        fileVersion.setFileMd5(fileInfo.getFileMd5());
        fileVersion.setFileName(fileInfo.getFileName());
        fileVersion.setFilePath(versionPath);
        fileVersion.setFileSize(fileInfo.getFileSize());
        fileVersion.setFileExtension(fileInfo.getFileExtension());
        fileVersion.setUploadUser(uploadUser);
        fileVersion.setChangeDescription(changeDescription);
        fileVersion = fileVersionRepository.save(fileVersion);

        cleanupOldVersions(fileInfo.getId());

        return fileVersion;
    }

    @Transactional
    public void saveVersionBeforeUpdate(String tenantCode, Long fileId, String uploadUser) {
        FileInfo fileInfo = fileInfoRepository.findById(fileId)
                .orElseThrow(() -> new RuntimeException("文件不存在"));
        saveVersion(tenantCode, fileInfo, uploadUser, "文件更新前自动备份");
    }

    private void cleanupOldVersions(Long fileId) {
        List<FileVersion> allVersions = fileVersionRepository.findByFileIdOrderByVersionNumberDesc(fileId);
        if (allVersions.size() > MAX_VERSIONS) {
            int versionToDelete = allVersions.get(MAX_VERSIONS - 1).getVersionNumber();

            for (int i = MAX_VERSIONS; i < allVersions.size(); i++) {
                FileVersion oldVersion = allVersions.get(i);
                try {
                    String bucketName = minioStorageService.getBucketName(
                            tenantService.getTenantByCode(oldVersion.getTenantId().toString()).getTenantCode()
                    );
                    minioStorageService.deleteFile(bucketName, oldVersion.getFilePath());
                } catch (Exception e) {
                    log.warn("删除旧版本文件失败: versionId={}", oldVersion.getId(), e);
                }
            }

            fileVersionRepository.deleteOldVersions(fileId, versionToDelete);
            log.info("清理文件旧版本完成: fileId={}, 保留最近{}个版本", fileId, MAX_VERSIONS);
        }
    }

    public List<FileVersion> getVersionList(String tenantCode, Long fileId) {
        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        return fileVersionRepository.findByTenantIdAndFileIdOrderByVersionNumberDesc(tenantId, fileId);
    }

    public FileVersion getVersion(String tenantCode, Long fileId, Integer versionNumber) {
        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        return fileVersionRepository.findByTenantIdAndFileIdAndVersionNumber(tenantId, fileId, versionNumber)
                .orElseThrow(() -> new RuntimeException("版本不存在"));
    }

    @Transactional
    public FileInfo rollbackToVersion(String tenantCode, Long fileId, Integer versionNumber,
                                       String operator) {
        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        FileVersion targetVersion = fileVersionRepository
                .findByTenantIdAndFileIdAndVersionNumber(tenantId, fileId, versionNumber)
                .orElseThrow(() -> new RuntimeException("版本不存在"));

        FileInfo currentFile = fileInfoRepository.findById(fileId)
                .orElseThrow(() -> new RuntimeException("文件不存在"));

        saveVersion(tenantCode, currentFile, operator, "回滚前自动备份");

        String bucketName = minioStorageService.getBucketName(tenantCode);
        try (InputStream inputStream = minioStorageService.downloadFile(bucketName, targetVersion.getFilePath())) {
            minioStorageService.uploadFile(bucketName, currentFile.getFilePath(), inputStream,
                    targetVersion.getFileSize(), "application/octet-stream");
        } catch (Exception e) {
            log.error("回滚文件版本失败: fileId={}, version={}", fileId, versionNumber, e);
            throw new RuntimeException("回滚文件版本失败", e);
        }

        currentFile.setFileMd5(targetVersion.getFileMd5());
        currentFile.setFileName(targetVersion.getFileName());
        currentFile.setFileSize(targetVersion.getFileSize());
        currentFile.setFileExtension(targetVersion.getFileExtension());
        currentFile = fileInfoRepository.save(currentFile);

        String cacheKey = FILE_CACHE_PREFIX + tenantCode + ":" + fileId;
        redisUtil.delete(cacheKey);

        log.info("文件回滚成功: fileId={}, 回滚到版本={}, 操作人={}", fileId, versionNumber, operator);
        return currentFile;
    }

    @Transactional
    public void deleteAllVersions(String tenantCode, Long fileId) {
        List<FileVersion> versions = fileVersionRepository.findByFileIdOrderByVersionNumberDesc(fileId);
        String bucketName = minioStorageService.getBucketName(tenantCode);

        for (FileVersion version : versions) {
            try {
                minioStorageService.deleteFile(bucketName, version.getFilePath());
            } catch (Exception e) {
                log.warn("删除版本文件失败: versionId={}", version.getId(), e);
            }
        }

        fileVersionRepository.deleteByFileId(fileId);
    }

    public InputStream downloadVersion(String tenantCode, Long fileId, Integer versionNumber) {
        FileVersion version = getVersion(tenantCode, fileId, versionNumber);
        String bucketName = minioStorageService.getBucketName(tenantCode);
        return minioStorageService.downloadFile(bucketName, version.getFilePath());
    }

    public String getVersionDownloadUrl(String tenantCode, Long fileId, Integer versionNumber,
                                        int expiresInSeconds) {
        FileVersion version = getVersion(tenantCode, fileId, versionNumber);
        String bucketName = minioStorageService.getBucketName(tenantCode);
        return minioStorageService.getPresignedUrl(bucketName, version.getFilePath(), expiresInSeconds);
    }
}
