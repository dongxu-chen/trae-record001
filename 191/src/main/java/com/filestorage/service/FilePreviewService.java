package com.filestorage.service;

import com.filestorage.entity.FileInfo;
import com.filestorage.util.FileUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import jakarta.annotation.Resource;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
public class FilePreviewService {

    @Resource
    private FileService fileService;

    @Resource
    private MinioStorageService minioStorageService;

    @Resource
    private WatermarkService watermarkService;

    @Resource
    private FileVersionService fileVersionService;

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    public Map<String, Object> getPreviewInfo(String tenantCode, Long fileId, String username, String ip) {
        FileInfo fileInfo = fileService.getFileById(tenantCode, fileId);
        Map<String, Object> result = new HashMap<>();

        String extension = fileInfo.getFileExtension();
        result.put("fileId", fileId);
        result.put("fileName", fileInfo.getFileName());
        result.put("fileSize", fileInfo.getFileSize());
        result.put("fileExtension", extension);
        result.put("contentType", getContentType(extension));
        result.put("canPreview", canPreview(extension));
        result.put("previewType", getPreviewType(extension));

        if (canPreview(extension)) {
            result.put("previewUrl", "/api/preview/" + fileId + "?tenantCode=" + tenantCode +
                    "&username=" + (username != null ? username : "") +
                    "&ip=" + (ip != null ? ip : ""));
        }

        return result;
    }

    public InputStream previewFile(String tenantCode, Long fileId, String username, String ip) throws Exception {
        FileInfo fileInfo = fileService.getFileById(tenantCode, fileId);
        String extension = fileInfo.getFileExtension();
        String bucketName = minioStorageService.getBucketName(tenantCode);

        if (FileUtil.isImageFile(extension)) {
            return previewImage(bucketName, fileInfo.getFilePath(), username, ip);
        } else if ("pdf".equalsIgnoreCase(extension)) {
            return previewPdf(bucketName, fileInfo.getFilePath());
        } else {
            throw new RuntimeException("不支持的预览格式: " + extension);
        }
    }

    public InputStream previewVersion(String tenantCode, Long fileId, Integer versionNumber,
                                       String username, String ip) throws Exception {
        String bucketName = minioStorageService.getBucketName(tenantCode);
        String versionPath = fileVersionService.getVersion(tenantCode, fileId, versionNumber).getFilePath();
        com.filestorage.entity.FileVersion version = fileVersionService.getVersion(tenantCode, fileId, versionNumber);
        String extension = version.getFileExtension();

        if (FileUtil.isImageFile(extension)) {
            return previewImage(bucketName, versionPath, username, ip);
        } else if ("pdf".equalsIgnoreCase(extension)) {
            return previewPdf(bucketName, versionPath);
        } else {
            throw new RuntimeException("不支持的预览格式: " + extension);
        }
    }

    private InputStream previewImage(String bucketName, String filePath, String username, String ip) throws Exception {
        InputStream inputStream = minioStorageService.downloadFile(bucketName, filePath);
        String timestamp = LocalDateTime.now().format(DATE_FORMATTER);
        String watermarkText = watermarkService.generateWatermarkText(username, ip, timestamp);
        byte[] watermarkedBytes = watermarkService.addImageWatermark(inputStream, watermarkText);
        return new ByteArrayInputStream(watermarkedBytes);
    }

    private InputStream previewPdf(String bucketName, String filePath) {
        return minioStorageService.downloadFile(bucketName, filePath);
    }

    public String getOfficePreviewUrl(String tenantCode, Long fileId) {
        FileInfo fileInfo = fileService.getFileById(tenantCode, fileId);
        String downloadUrl = fileService.getDownloadUrl(tenantCode, fileId, 3600 * 24);
        return downloadUrl;
    }

    private boolean canPreview(String extension) {
        if (FileUtil.isImageFile(extension)) {
            return true;
        }
        return "pdf".equalsIgnoreCase(extension);
    }

    private String getPreviewType(String extension) {
        if (FileUtil.isImageFile(extension)) {
            return "image";
        } else if ("pdf".equalsIgnoreCase(extension)) {
            return "pdf";
        } else if (isOfficeDocument(extension)) {
            return "office";
        } else {
            return "none";
        }
    }

    private boolean isOfficeDocument(String extension) {
        String[] officeExtensions = {"doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "md", "rtf"};
        for (String ext : officeExtensions) {
            if (ext.equalsIgnoreCase(extension)) {
                return true;
            }
        }
        return false;
    }

    private String getContentType(String extension) {
        Map<String, String> contentTypes = new HashMap<>();
        contentTypes.put("pdf", "application/pdf");
        contentTypes.put("jpg", "image/jpeg");
        contentTypes.put("jpeg", "image/jpeg");
        contentTypes.put("png", "image/png");
        contentTypes.put("gif", "image/gif");
        contentTypes.put("bmp", "image/bmp");
        contentTypes.put("webp", "image/webp");
        contentTypes.put("doc", "application/msword");
        contentTypes.put("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        contentTypes.put("xls", "application/vnd.ms-excel");
        contentTypes.put("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        contentTypes.put("ppt", "application/vnd.ms-powerpoint");
        contentTypes.put("pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation");
        contentTypes.put("txt", "text/plain");

        String contentType = contentTypes.get(extension.toLowerCase());
        return contentType != null ? contentType : "application/octet-stream";
    }
}
