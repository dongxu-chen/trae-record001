package com.filestorage.service;

import com.filestorage.config.MinIOConfig;
import io.minio.*;
import io.minio.errors.*;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import jakarta.annotation.Resource;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;

@Slf4j
@Service
public class MinioStorageService {

    @Resource
    private MinioClient minioClient;

    @Resource
    private MinIOConfig minIOConfig;

    public String getBucketName(String tenantCode) {
        return minIOConfig.getBucketPrefix() + tenantCode;
    }

    public void createBucketIfNotExists(String bucketName) {
        try {
            if (!minioClient.bucketExists(BucketExistsArgs.builder().bucket(bucketName).build())) {
                minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucketName).build());
            }
        } catch (Exception e) {
            log.error("创建Bucket失败: {}", bucketName, e);
            throw new RuntimeException("创建Bucket失败", e);
        }
    }

    public void uploadFile(String bucketName, String objectName, InputStream inputStream,
                           long size, String contentType) {
        createBucketIfNotExists(bucketName);
        try {
            minioClient.putObject(
                    PutObjectArgs.builder()
                            .bucket(bucketName)
                            .object(objectName)
                            .stream(inputStream, size, -1)
                            .contentType(contentType)
                            .build()
            );
        } catch (Exception e) {
            log.error("上传文件失败: {}/{}", bucketName, objectName, e);
            throw new RuntimeException("上传文件失败", e);
        }
    }

    public void uploadChunk(String bucketName, String uploadId, int chunkNumber,
                            byte[] chunkData, String contentType) {
        String objectName = "chunks/" + uploadId + "/" + chunkNumber;
        uploadFile(bucketName, objectName, new ByteArrayInputStream(chunkData), chunkData.length, contentType);
    }

    public void deleteChunk(String bucketName, String uploadId, int chunkNumber) {
        String objectName = "chunks/" + uploadId + "/" + chunkNumber;
        deleteFile(bucketName, objectName);
    }

    public void deleteAllChunks(String bucketName, String uploadId, int totalChunks) {
        for (int i = 1; i <= totalChunks; i++) {
            try {
                deleteChunk(bucketName, uploadId, i);
            } catch (Exception e) {
                log.warn("删除分片失败: {}/chunks/{}/{}", bucketName, uploadId, i, e);
            }
        }
    }

    public void mergeChunks(String bucketName, String uploadId, String targetObjectName,
                            int totalChunks, String contentType) {
        createBucketIfNotExists(bucketName);
        try {
            minioClient.composeObject(
                    ComposeObjectArgs.builder()
                            .bucket(bucketName)
                            .object(targetObjectName)
                            .sources(buildComposeSources(bucketName, uploadId, totalChunks))
                            .build()
            );
            deleteChunks(bucketName, uploadId, totalChunks);
        } catch (Exception e) {
            log.error("合并分片失败: {}/{}", bucketName, targetObjectName, e);
            throw new RuntimeException("合并分片失败", e);
        }
    }

    private ComposeSource buildComposeSource(String bucketName, String uploadId, int chunkNumber) {
        return ComposeSource.builder()
                .bucket(bucketName)
                .object("chunks/" + uploadId + "/" + chunkNumber)
                .build();
    }

    private java.util.List<ComposeSource> buildComposeSources(String bucketName, String uploadId, int totalChunks) {
        java.util.List<ComposeSource> sources = new java.util.ArrayList<>();
        for (int i = 1; i <= totalChunks; i++) {
            sources.add(buildComposeSource(bucketName, uploadId, i));
        }
        return sources;
    }

    private void deleteChunks(String bucketName, String uploadId, int totalChunks) {
        for (int i = 1; i <= totalChunks; i++) {
            try {
                minioClient.removeObject(
                        RemoveObjectArgs.builder()
                                .bucket(bucketName)
                                .object("chunks/" + uploadId + "/" + i)
                                .build()
                );
            } catch (Exception e) {
                log.warn("删除分片失败: {}/chunks/{}/{}", bucketName, uploadId, i, e);
            }
        }
    }

    public InputStream downloadFile(String bucketName, String objectName) {
        try {
            return minioClient.getObject(
                    GetObjectArgs.builder()
                            .bucket(bucketName)
                            .object(objectName)
                            .build()
            );
        } catch (Exception e) {
            log.error("下载文件失败: {}/{}", bucketName, objectName, e);
            throw new RuntimeException("下载文件失败", e);
        }
    }

    public void deleteFile(String bucketName, String objectName) {
        try {
            minioClient.removeObject(
                    RemoveObjectArgs.builder()
                            .bucket(bucketName)
                            .object(objectName)
                            .build()
            );
        } catch (Exception e) {
            log.error("删除文件失败: {}/{}", bucketName, objectName, e);
            throw new RuntimeException("删除文件失败", e);
        }
    }

    public boolean fileExists(String bucketName, String objectName) {
        try {
            minioClient.statObject(
                    StatObjectArgs.builder()
                            .bucket(bucketName)
                            .object(objectName)
                            .build()
            );
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public String getPresignedUrl(String bucketName, String objectName, int expiresInSeconds) {
        try {
            return minioClient.getPresignedObjectUrl(
                    GetPresignedObjectUrlArgs.builder()
                            .method(Method.GET)
                            .bucket(bucketName)
                            .object(objectName)
                            .expiry(expiresInSeconds)
                            .build()
            );
        } catch (Exception e) {
            log.error("获取预签名URL失败: {}/{}", bucketName, objectName, e);
            throw new RuntimeException("获取预签名URL失败", e);
        }
    }
}
