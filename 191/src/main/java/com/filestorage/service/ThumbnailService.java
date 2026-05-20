package com.filestorage.service;

import com.filestorage.config.FileStorageConfig;
import com.filestorage.entity.FileInfo;
import com.filestorage.repository.FileInfoRepository;
import com.filestorage.util.FileUtil;
import lombok.extern.slf4j.Slf4j;
import net.coobird.thumbnailator.Thumbnails;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import jakarta.annotation.Resource;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;

@Slf4j
@Service
public class ThumbnailService {

    @Resource
    private MinioStorageService minioStorageService;

    @Resource
    private FileInfoRepository fileInfoRepository;

    @Resource
    private FileStorageConfig fileStorageConfig;

    @Transactional
    public void generateThumbnail(String tenantCode, FileInfo fileInfo) {
        if (!fileStorageConfig.getThumbnail().getImage().isEnabled()) {
            return;
        }

        String extension = fileInfo.getFileExtension();
        if (!FileUtil.isImageFile(extension)) {
            return;
        }

        try {
            String bucketName = minioStorageService.getBucketName(tenantCode);
            InputStream inputStream = minioStorageService.downloadFile(bucketName, fileInfo.getFilePath());

            ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
            FileStorageConfig.Thumbnail.Image imageConfig = fileStorageConfig.getThumbnail().getImage();

            Thumbnails.of(inputStream)
                    .size(imageConfig.getWidth(), imageConfig.getHeight())
                    .keepAspectRatio(true)
                    .outputFormat("jpg")
                    .outputQuality(imageConfig.getQuality())
                    .toOutputStream(outputStream);

            byte[] thumbnailBytes = outputStream.toByteArray();
            String thumbnailPath = FileUtil.generateThumbnailPath(tenantCode, fileInfo.getFileMd5());

            minioStorageService.uploadFile(
                    bucketName,
                    thumbnailPath,
                    new ByteArrayInputStream(thumbnailBytes),
                    thumbnailBytes.length,
                    "image/jpeg"
            );

            fileInfo.setHasThumbnail(1);
            fileInfo.setThumbnailPath(thumbnailPath);
            fileInfoRepository.save(fileInfo);

            log.info("缩略图生成成功: {}/{}", bucketName, thumbnailPath);
        } catch (Exception e) {
            log.error("缩略图生成失败: {}", fileInfo.getFilePath(), e);
        }
    }

    public InputStream getThumbnail(String tenantCode, String fileMd5) {
        String bucketName = minioStorageService.getBucketName(tenantCode);
        String thumbnailPath = FileUtil.generateThumbnailPath(tenantCode, fileMd5);
        return minioStorageService.downloadFile(bucketName, thumbnailPath);
    }

    public boolean hasThumbnail(String tenantCode, String fileMd5) {
        String bucketName = minioStorageService.getBucketName(tenantCode);
        String thumbnailPath = FileUtil.generateThumbnailPath(tenantCode, fileMd5);
        return minioStorageService.fileExists(bucketName, thumbnailPath);
    }
}
