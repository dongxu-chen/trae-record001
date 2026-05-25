package com.property.repair.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import javax.imageio.IIOImage;
import javax.imageio.ImageIO;
import javax.imageio.ImageWriteParam;
import javax.imageio.ImageWriter;
import javax.imageio.stream.ImageOutputStream;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.*;

@Service
public class ImageService {

    @Value("${image.upload.path:./uploads}")
    private String uploadPath;

    @Value("${image.compression.quality:0.6f}")
    private float compressionQuality;

    @Value("${image.compression.max-width:1280}")
    private int maxWidth;

    @Value("${image.compression.max-height:1280}")
    private int maxHeight;

    private static final Set<String> ALLOWED_TYPES = new HashSet<>(
        Arrays.asList("image/jpeg", "image/jpg", "image/png", "image/gif", "image/bmp")
    );

    public Map<String, String> uploadImage(MultipartFile file) throws IOException {
        validateFile(file);

        String datePath = new SimpleDateFormat("yyyy/MM/dd").format(new Date());
        String originalDir = uploadPath + "/original/" + datePath;
        String compressedDir = uploadPath + "/compressed/" + datePath;

        Files.createDirectories(Paths.get(originalDir));
        Files.createDirectories(Paths.get(compressedDir));

        String fileName = generateFileName(file.getOriginalFilename());
        String originalPath = originalDir + "/" + fileName;
        String compressedPath = compressedDir + "/" + fileName;

        File originalFile = new File(originalPath);
        file.transferTo(originalFile);

        BufferedImage originalImage = ImageIO.read(originalFile);
        BufferedImage compressedImage = compressImage(originalImage);

        File compressedFile = new File(compressedPath);
        writeCompressedImage(compressedImage, compressedFile, getFileExtension(fileName));

        Map<String, String> result = new HashMap<>();
        result.put("originalUrl", "/uploads/original/" + datePath + "/" + fileName);
        result.put("compressedUrl", "/uploads/compressed/" + datePath + "/" + fileName);
        result.put("fileName", fileName);
        result.put("originalSize", String.valueOf(file.getSize()));
        result.put("compressedSize", String.valueOf(compressedFile.length()));
        result.put("compressionRatio", String.format("%.2f%%", 
            (1 - (double) compressedFile.length() / file.getSize()) * 100));

        return result;
    }

    public List<Map<String, String>> uploadImages(MultipartFile[] files) throws IOException {
        List<Map<String, String>> results = new ArrayList<>();
        for (MultipartFile file : files) {
            if (!file.isEmpty()) {
                results.add(uploadImage(file));
            }
        }
        return results;
    }

    private void validateFile(MultipartFile file) {
        if (file.isEmpty()) {
            throw new IllegalArgumentException("文件不能为空");
        }

        String contentType = file.getContentType();
        if (!ALLOWED_TYPES.contains(contentType)) {
            throw new IllegalArgumentException("不支持的文件类型，仅支持图片格式");
        }

        if (file.getSize() > 10 * 1024 * 1024) {
            throw new IllegalArgumentException("文件大小不能超过10MB");
        }
    }

    private String generateFileName(String originalFileName) {
        String extension = getFileExtension(originalFileName);
        return UUID.randomUUID().toString().replace("-", "") + "." + extension;
    }

    private String getFileExtension(String fileName) {
        int dotIndex = fileName.lastIndexOf(".");
        if (dotIndex > 0) {
            return fileName.substring(dotIndex + 1).toLowerCase();
        }
        return "jpg";
    }

    private BufferedImage compressImage(BufferedImage originalImage) {
        int originalWidth = originalImage.getWidth();
        int originalHeight = originalImage.getHeight();

        double scaleRatio = Math.min(
            (double) maxWidth / originalWidth,
            (double) maxHeight / originalHeight
        );

        if (scaleRatio >= 1) {
            scaleRatio = 1;
        }

        int newWidth = (int) (originalWidth * scaleRatio);
        int newHeight = (int) (originalHeight * scaleRatio);

        BufferedImage resizedImage = new BufferedImage(newWidth, newHeight, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = resizedImage.createGraphics();
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
        g.drawImage(originalImage, 0, 0, newWidth, newHeight, null);
        g.dispose();

        return resizedImage;
    }

    private void writeCompressedImage(BufferedImage image, File outputFile, String format) throws IOException {
        if ("png".equalsIgnoreCase(format)) {
            format = "png";
        } else {
            format = "jpg";
        }

        if ("jpg".equalsIgnoreCase(format) || "jpeg".equalsIgnoreCase(format)) {
            Iterator<ImageWriter> writers = ImageIO.getImageWritersByFormatName("jpg");
            ImageWriter writer = writers.next();

            ImageWriteParam param = writer.getDefaultWriteParam();
            param.setCompressionMode(ImageWriteParam.MODE_EXPLICIT);
            param.setCompressionQuality(compressionQuality);

            try (FileOutputStream fos = new FileOutputStream(outputFile);
                 ImageOutputStream ios = ImageIO.createImageOutputStream(fos)) {
                writer.setOutput(ios);
                writer.write(null, new IIOImage(image, null, null), param);
            } finally {
                writer.dispose();
            }
        } else {
            ImageIO.write(image, format, outputFile);
        }
    }

    public boolean deleteImage(String imageUrl) {
        try {
            if (imageUrl.startsWith("/uploads/")) {
                String filePath = uploadPath + imageUrl.substring("/uploads".length());
                Path path = Paths.get(filePath);
                return Files.deleteIfExists(path);
            }
            return false;
        } catch (IOException e) {
            return false;
        }
    }
}
