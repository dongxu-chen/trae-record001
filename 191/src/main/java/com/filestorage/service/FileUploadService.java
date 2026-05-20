package com.filestorage.service;

import com.filestorage.config.FileStorageConfig;
import com.filestorage.dto.FileUploadDTO;
import com.filestorage.entity.FileChunk;
import com.filestorage.entity.FileInfo;
import com.filestorage.repository.FileChunkRepository;
import com.filestorage.repository.FileInfoRepository;
import com.filestorage.util.FileUtil;
import com.filestorage.util.RedisLock;
import com.filestorage.util.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import jakarta.annotation.Resource;
import java.io.IOException;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class FileUploadService {

    private static final String CHUNK_UPLOADED_PREFIX = "upload:chunks:";
    private static final String FAST_CHECK_PREFIX = "fastcheck:";
    private static final String LOCK_PREFIX = "upload:lock:";

    @Resource
    private FileChunkRepository fileChunkRepository;

    @Resource
    private FileInfoRepository fileInfoRepository;

    @Resource
    private MinioStorageService minioStorageService;

    @Resource
    private TenantService tenantService;

    @Resource
    private FileStorageConfig fileStorageConfig;

    @Resource
    private RedisUtil redisUtil;

    @Resource
    private RedisLock redisLock;

    @Resource
    private ThumbnailService thumbnailService;

    public Map<String, Object> checkFileByMd5(String tenantCode, String fileMd5, String fileName) {
        Map<String, Object> result = new HashMap<>();
        result.put("exist", false);
        result.put("skipUpload", false);

        String fastCheckKey = FAST_CHECK_PREFIX + tenantCode + ":" + fileMd5;
        Object cached = redisUtil.get(fastCheckKey);
        if (cached != null) {
            result.put("exist", true);
            result.put("skipUpload", true);
            result.put("fileId", cached);
            return result;
        }

        List<FileInfo> existingFiles = fileInfoRepository
                .findByTenantIdAndFileMd5AndIsDeleted(tenantService.getTenantByCode(tenantCode).getId(), fileMd5, 0);

        if (!existingFiles.isEmpty()) {
            FileInfo fileInfo = existingFiles.get(0);
            boolean fileExists = minioStorageService.fileExists(
                    minioStorageService.getBucketName(tenantCode),
                    fileInfo.getFilePath()
            );

            if (fileExists) {
                redisUtil.set(fastCheckKey, fileInfo.getId(), 1, TimeUnit.DAYS);
                result.put("exist", true);
                result.put("skipUpload", true);
                result.put("fileId", fileInfo.getId());
                return result;
            }
        }

        result.put("uploadedChunks", getUploadedChunks(tenantCode, fileMd5));
        return result;
    }

    public String initUpload(FileUploadDTO dto) {
        String tenantCode = dto.getTenantCode();
        String fileMd5 = dto.getFileMd5();

        if (!tenantService.checkStorageQuota(tenantCode, dto.getFileSize())) {
            throw new RuntimeException("存储空间不足");
        }

        String uploadId = FileUtil.generateUploadId();
        String cacheKey = CHUNK_UPLOADED_PREFIX + uploadId;

        Map<String, Object> uploadInfo = new HashMap<>();
        uploadInfo.put("fileMd5", fileMd5);
        uploadInfo.put("fileName", dto.getFileName());
        uploadInfo.put("fileSize", dto.getFileSize());
        uploadInfo.put("totalChunks", dto.getTotalChunks());
        uploadInfo.put("uploadUser", dto.getUploadUser());
        uploadInfo.put("tenantCode", tenantCode);

        redisUtil.hSet(cacheKey, "info", uploadInfo);
        redisUtil.expire(cacheKey, fileStorageConfig.getUpload().getTimeoutHours(), TimeUnit.HOURS);

        return uploadId;
    }

    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> uploadChunk(String tenantCode, String uploadId, MultipartFile file,
                                           int chunkNumber, int totalChunks, long chunkSize,
                                           String fileMd5, String fileName, String uploadUser) throws IOException {
        Map<String, Object> result = new HashMap<>();
        String bucketName = minioStorageService.getBucketName(tenantCode);
        boolean chunkUploaded = false;
        Long savedChunkId = null;

        try {
            byte[] bytes = file.getBytes();
            String contentType = file.getContentType();
            minioStorageService.uploadChunk(bucketName, uploadId, chunkNumber, bytes, contentType);
            chunkUploaded = true;

            Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
            FileChunk fileChunk = new FileChunk();
            fileChunk.setTenantId(tenantId);
            fileChunk.setUploadId(uploadId);
            fileChunk.setFileMd5(fileMd5);
            fileChunk.setChunkNumber(chunkNumber);
            fileChunk.setChunkSize(chunkSize);
            fileChunk.setTotalChunks(totalChunks);
            fileChunk.setTotalSize(chunkSize * totalChunks);
            fileChunk.setFileName(fileName);
            fileChunk.setUploadUser(uploadUser);
            fileChunk.setStatus(1);
            fileChunk.setExpiredAt(LocalDateTime.now().plusHours(fileStorageConfig.getUpload().getTimeoutHours()));
            fileChunk = fileChunkRepository.save(fileChunk);
            savedChunkId = fileChunk.getId();

            String cacheKey = CHUNK_UPLOADED_PREFIX + uploadId;
            redisUtil.sAdd(cacheKey + ":chunks", chunkNumber);
            redisUtil.expire(cacheKey, fileStorageConfig.getUpload().getTimeoutHours(), TimeUnit.HOURS);

            Set<Object> uploadedChunks = redisUtil.sMembers(cacheKey + ":chunks");
            result.put("uploadedChunks", uploadedChunks);
            result.put("allUploaded", uploadedChunks.size() >= totalChunks);

            if (uploadedChunks.size() >= totalChunks) {
                FileInfo fileInfo = mergeChunks(tenantCode, uploadId, fileMd5, fileName, uploadUser);
                result.put("merged", true);
                result.put("fileId", fileInfo.getId());
            }

            return result;
        } catch (Exception e) {
            log.error("上传分片失败，开始回滚: uploadId={}, chunkNumber={}", uploadId, chunkNumber, e);

            if (chunkUploaded) {
                try {
                    minioStorageService.deleteChunk(bucketName, uploadId, chunkNumber);
                } catch (Exception ex) {
                    log.error("回滚MinIO分片失败", ex);
                }
            }

            if (savedChunkId != null) {
                try {
                    fileChunkRepository.deleteById(savedChunkId);
                } catch (Exception ex) {
                    log.error("回滚数据库分片记录失败", ex);
                }
            }

            String cacheKey = CHUNK_UPLOADED_PREFIX + uploadId;
            try {
                redisUtil.sRemove(cacheKey + ":chunks", chunkNumber);
            } catch (Exception ex) {
                log.error("回滚Redis分片记录失败", ex);
            }

            throw new RuntimeException("上传分片失败: " + e.getMessage(), e);
        }
    }

    private Set<Integer> getUploadedChunks(String tenantCode, String fileMd5) {
        Set<Integer> uploadedChunks = new HashSet<>();
        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        List<FileChunk> chunks = fileChunkRepository.findByTenantIdAndFileMd5AndStatus(tenantId, fileMd5, 1);
        for (FileChunk chunk : chunks) {
            uploadedChunks.add(chunk.getChunkNumber());
        }
        return uploadedChunks;
    }

    @Transactional(rollbackFor = Exception.class)
    public FileInfo mergeChunks(String tenantCode, String uploadId, String fileMd5,
                                String fileName, String uploadUser) {
        String lockKey = LOCK_PREFIX + uploadId;
        String lockValue = UUID.randomUUID().toString();
        String bucketName = minioStorageService.getBucketName(tenantCode);
        String objectPath = null;
        FileInfo savedFileInfo = null;

        if (!redisLock.tryLock(lockKey, lockValue, 5000, 30000, TimeUnit.MILLISECONDS)) {
            throw new RuntimeException("合并中，请稍后重试");
        }

        try {
            String cacheKey = CHUNK_UPLOADED_PREFIX + uploadId;
            Map<Object, Object> infoMap = redisUtil.hGetAll(cacheKey);
            if (infoMap == null || infoMap.isEmpty()) {
                throw new RuntimeException("上传信息不存在或已过期");
            }

            Map<String, Object> info = (Map<String, Object>) infoMap.get("info");
            int totalChunks = (Integer) info.get("totalChunks");
            long fileSize = (Long) info.get("fileSize");

            if (!tenantService.checkStorageQuota(tenantCode, fileSize)) {
                throw new RuntimeException("存储空间不足");
            }

            objectPath = FileUtil.generateObjectPath(tenantCode, fileMd5, fileName);

            if (minioStorageService.fileExists(bucketName, objectPath)) {
                FileInfo fileInfo = createFileInfo(tenantCode, fileMd5, fileName, objectPath, fileSize, uploadUser);
                cleanupUploadData(uploadId, tenantCode, fileMd5);
                return fileInfo;
            }

            minioStorageService.mergeChunks(bucketName, uploadId, objectPath, totalChunks, "application/octet-stream");

            savedFileInfo = createFileInfo(tenantCode, fileMd5, fileName, objectPath, fileSize, uploadUser);

            tenantService.increaseUsedStorage(tenantCode, fileSize);

            asyncProcessAfterUpload(savedFileInfo, tenantCode, fileMd5);

            cleanupUploadData(uploadId, tenantCode, fileMd5);

            return savedFileInfo;
        } catch (Exception e) {
            log.error("合并分片失败，开始回滚: uploadId={}", uploadId, e);

            if (objectPath != null && minioStorageService.fileExists(bucketName, objectPath)) {
                try {
                    minioStorageService.deleteFile(bucketName, objectPath);
                } catch (Exception ex) {
                    log.error("回滚合并后的文件失败", ex);
                }
            }

            if (savedFileInfo != null && savedFileInfo.getId() != null) {
                try {
                    fileInfoRepository.deleteById(savedFileInfo.getId());
                } catch (Exception ex) {
                    log.error("回滚文件信息记录失败", ex);
                }
            }

            String cacheKey = CHUNK_UPLOADED_PREFIX + uploadId;
            try {
                Map<Object, Object> infoMap = redisUtil.hGetAll(cacheKey);
                if (infoMap != null && !infoMap.isEmpty()) {
                    Map<String, Object> info = (Map<String, Object>) infoMap.get("info");
                    int totalChunks = (Integer) info.get("totalChunks");
                    minioStorageService.deleteAllChunks(bucketName, uploadId, totalChunks);
                }
            } catch (Exception ex) {
                log.error("回滚所有分片失败", ex);
            }

            throw new RuntimeException("合并分片失败: " + e.getMessage(), e);
        } finally {
            redisLock.unlock(lockKey, lockValue);
        }
    }

    private FileInfo createFileInfo(String tenantCode, String fileMd5, String fileName,
                                    String objectPath, long fileSize, String uploadUser) {
        FileInfo fileInfo = new FileInfo();
        fileInfo.setTenantId(tenantService.getTenantByCode(tenantCode).getId());
        fileInfo.setFileMd5(fileMd5);
        fileInfo.setFileName(fileName);
        fileInfo.setFilePath(objectPath);
        fileInfo.setFileSize(fileSize);
        fileInfo.setFileExtension(FileUtil.getFileExtension(fileName));
        fileInfo.setUploadUser(uploadUser);
        fileInfo.setIsDeleted(0);
        fileInfo.setHasThumbnail(0);
        return fileInfoRepository.save(fileInfo);
    }

    @Async
    public void asyncProcessAfterUpload(FileInfo fileInfo, String tenantCode, String fileMd5) {
        try {
            thumbnailService.generateThumbnail(tenantCode, fileInfo);
            String fastCheckKey = FAST_CHECK_PREFIX + tenantCode + ":" + fileMd5;
            redisUtil.set(fastCheckKey, fileInfo.getId(), 1, TimeUnit.DAYS);
        } catch (Exception e) {
            log.error("异步处理文件失败", e);
        }
    }

    private void cleanupUploadData(String uploadId, String tenantCode, String fileMd5) {
        String cacheKey = CHUNK_UPLOADED_PREFIX + uploadId;
        redisUtil.delete(cacheKey);
        redisUtil.delete(cacheKey + ":chunks");

        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        fileChunkRepository.deleteByTenantIdAndUploadId(tenantId, uploadId);
    }

    @Async
    public void cleanupExpiredChunks() {
        log.info("开始清理过期的分片数据");
        int deleted = fileChunkRepository.deleteExpiredChunks(LocalDateTime.now());
        log.info("清理完成，删除过期分片记录: {}", deleted);
    }
}
