package com.filestorage.util;

import cn.hutool.core.io.FileTypeUtil;
import cn.hutool.core.util.IdUtil;
import cn.hutool.crypto.digest.DigestUtil;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;

public class FileUtil {

    public static String generateUploadId() {
        return IdUtil.fastSimpleUUID();
    }

    public static String generateShareCode() {
        return IdUtil.fastSimpleUUID();
    }

    public static String generateExtractCode() {
        return cn.hutool.core.util.RandomUtil.randomString(6);
    }

    public static String getFileExtension(String fileName) {
        if (fileName == null || fileName.isEmpty()) {
            return "";
        }
        int lastDotIndex = fileName.lastIndexOf('.');
        if (lastDotIndex == -1 || lastDotIndex == fileName.length() - 1) {
            return "";
        }
        return fileName.substring(lastDotIndex + 1).toLowerCase();
    }

    public static String getFileMd5(InputStream inputStream) throws IOException {
        return DigestUtil.md5Hex(inputStream);
    }

    public static String getFileType(MultipartFile file) throws IOException {
        return FileTypeUtil.getType(file.getInputStream());
    }

    public static boolean isImageFile(String extension) {
        String[] imageExtensions = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"};
        for (String ext : imageExtensions) {
            if (ext.equalsIgnoreCase(extension)) {
                return true;
            }
        }
        return false;
    }

    public static boolean isVideoFile(String extension) {
        String[] videoExtensions = {"mp4", "avi", "mov", "wmv", "flv", "mkv", "webm"};
        for (String ext : videoExtensions) {
            if (ext.equalsIgnoreCase(extension)) {
                return true;
            }
        }
        return false;
    }

    public static String generateObjectPath(String tenantCode, String fileMd5, String fileName) {
        String extension = getFileExtension(fileName);
        return "files/" + tenantCode + "/" + fileMd5.substring(0, 2) + "/" + fileMd5.substring(2, 4) + "/" +
                fileMd5 + (extension.isEmpty() ? "" : "." + extension);
    }

    public static String generateThumbnailPath(String tenantCode, String fileMd5) {
        return "thumbnails/" + tenantCode + "/" + fileMd5.substring(0, 2) + "/" +
                fileMd5.substring(2, 4) + "/" + fileMd5 + ".jpg";
    }

    public static String formatFileSize(long size) {
        if (size < 1024) {
            return size + " B";
        } else if (size < 1024 * 1024) {
            return String.format("%.2f KB", size / 1024.0);
        } else if (size < 1024 * 1024 * 1024) {
            return String.format("%.2f MB", size / (1024.0 * 1024));
        } else {
            return String.format("%.2f GB", size / (1024.0 * 1024 * 1024));
        }
    }
}
