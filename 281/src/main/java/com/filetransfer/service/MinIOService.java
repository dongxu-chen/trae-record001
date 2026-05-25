package com.filetransfer.service;

import com.filetransfer.config.MinIOConfig;
import io.minio.*;
import io.minio.http.Method;
import io.minio.messages.ComposeSource;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class MinIOService {
    private final MinioClient minioClient;
    private final MinIOConfig minIOConfig;

    public void createBucketIfNotExists() {
        try {
            boolean exists = minioClient.bucketExists(BucketExistsArgs.builder()
                    .bucket(minIOConfig.getBucketName())
                    .build());
            if (!exists) {
                minioClient.makeBucket(MakeBucketArgs.builder()
                        .bucket(minIOConfig.getBucketName())
                        .build());
                log.info("Bucket {} 创建成功", minIOConfig.getBucketName());
            }
        } catch (Exception e) {
            log.error("创建Bucket失败", e);
            throw new RuntimeException("创建Bucket失败", e);
        }
    }

    public void uploadChunk(String objectName, InputStream inputStream, long size, String contentType) {
        try {
            minioClient.putObject(PutObjectArgs.builder()
                    .bucket(minIOConfig.getBucketName())
                    .object(objectName)
                    .stream(inputStream, size, -1)
                    .contentType(contentType)
                    .build());
        } catch (Exception e) {
            log.error("上传分片失败: {}", objectName, e);
            throw new RuntimeException("上传分片失败", e);
        }
    }

    public InputStream getObject(String objectName) {
        try {
            return minioClient.getObject(GetObjectArgs.builder()
                    .bucket(minIOConfig.getBucketName())
                    .object(objectName)
                    .build());
        } catch (Exception e) {
            log.error("获取对象失败: {}", objectName, e);
            throw new RuntimeException("获取对象失败", e);
        }
    }

    public InputStream getObjectRange(String objectName, long offset, long length) {
        try {
            return minioClient.getObject(GetObjectArgs.builder()
                    .bucket(minIOConfig.getBucketName())
                    .object(objectName)
                    .offset(offset)
                    .length(length)
                    .build());
        } catch (Exception e) {
            log.error("获取对象范围失败: {}", objectName, e);
            throw new RuntimeException("获取对象范围失败", e);
        }
    }

    public void composeObject(String targetObjectName, Iterable<ComposeSource> sources) {
        try {
            minioClient.composeObject(ComposeObjectArgs.builder()
                    .bucket(minIOConfig.getBucketName())
                    .object(targetObjectName)
                    .sources(sources)
                    .build());
        } catch (Exception e) {
            log.error("合并对象失败: {}", targetObjectName, e);
            throw new RuntimeException("合并对象失败", e);
        }
    }

    public void deleteObject(String objectName) {
        try {
            minioClient.removeObject(RemoveObjectArgs.builder()
                    .bucket(minIOConfig.getBucketName())
                    .object(objectName)
                    .build());
        } catch (Exception e) {
            log.error("删除对象失败: {}", objectName, e);
        }
    }

    public String getPresignedUrl(String objectName, int expiry, TimeUnit timeUnit) {
        try {
            return minioClient.getPresignedObjectUrl(GetPresignedObjectUrlArgs.builder()
                    .method(Method.GET)
                    .bucket(minIOConfig.getBucketName())
                    .object(objectName)
                    .expiry(expiry, timeUnit)
                    .build());
        } catch (Exception e) {
            log.error("获取预签名URL失败: {}", objectName, e);
            throw new RuntimeException("获取预签名URL失败", e);
        }
    }

    public StatObjectResponse getObjectInfo(String objectName) {
        try {
            return minioClient.statObject(StatObjectArgs.builder()
                    .bucket(minIOConfig.getBucketName())
                    .object(objectName)
                    .build());
        } catch (Exception e) {
            log.error("获取对象信息失败: {}", objectName, e);
            return null;
        }
    }

    public boolean objectExists(String objectName) {
        return getObjectInfo(objectName) != null;
    }
}
