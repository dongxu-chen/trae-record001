package com.filetransfer.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Slf4j
@Service
public class WatermarkService {
    private static final float DEFAULT_OPACITY = 0.3f;
    private static final int DEFAULT_FONT_SIZE = 24;
    private static final int INTERVAL = 150;

    public byte[] addTextWatermark(InputStream inputStream, String watermarkText,
                                    String visitorInfo, String ipAddress) {
        try {
            BufferedImage image = ImageIO.read(inputStream);
            if (image == null) {
                log.warn("无法读取图片");
                return null;
            }

            int width = image.getWidth();
            int height = image.getHeight();

            BufferedImage watermarkedImage = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
            Graphics2D g2d = (Graphics2D) watermarkedImage.getGraphics();
            g2d.drawImage(image, 0, 0, null);

            AlphaComposite alphaComposite = AlphaComposite.getInstance(AlphaComposite.SRC_OVER, DEFAULT_OPACITY);
            g2d.setComposite(alphaComposite);
            g2d.setColor(Color.RED);
            g2d.setFont(new Font("微软雅黑", Font.BOLD, DEFAULT_FONT_SIZE));
            g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

            String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
            String fullWatermark = String.format("%s | %s | %s | %s",
                    watermarkText != null ? watermarkText : "机密文件",
                    visitorInfo != null ? visitorInfo : "访客",
                    ipAddress != null ? ipAddress : "未知IP",
                    timestamp);

            FontMetrics metrics = g2d.getFontMetrics();
            int textWidth = metrics.stringWidth(fullWatermark);
            int textHeight = metrics.getHeight();

            double radians = Math.toRadians(-30);
            double diagonal = Math.sqrt(width * width + height * height);
            int steps = (int) (diagonal / (textWidth + INTERVAL));

            for (int i = -steps; i <= steps; i++) {
                for (int j = -steps; j <= steps; j++) {
                    int x = i * (textWidth + INTERVAL);
                    int y = j * (INTERVAL + textHeight);

                    g2d.translate(x + width / 2, y + height / 2);
                    g2d.rotate(radians);
                    g2d.drawString(fullWatermark, -textWidth / 2, textHeight / 2);
                    g2d.rotate(-radians);
                    g2d.translate(-(x + width / 2), -(y + height / 2));
                }
            }

            g2d.dispose();

            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            ImageIO.write(watermarkedImage, "png", baos);
            return baos.toByteArray();

        } catch (Exception e) {
            log.error("添加水印失败", e);
            return null;
        }
    }

    public byte[] addSimpleWatermark(InputStream inputStream, String watermarkText) {
        try {
            BufferedImage image = ImageIO.read(inputStream);
            if (image == null) {
                return null;
            }

            int width = image.getWidth();
            int height = image.getHeight();

            BufferedImage watermarkedImage = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
            Graphics2D g2d = (Graphics2D) watermarkedImage.getGraphics();
            g2d.drawImage(image, 0, 0, null);

            AlphaComposite alphaComposite = AlphaComposite.getInstance(AlphaComposite.SRC_OVER, DEFAULT_OPACITY);
            g2d.setComposite(alphaComposite);
            g2d.setColor(Color.RED);
            g2d.setFont(new Font("微软雅黑", Font.BOLD, 36));
            g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

            String text = watermarkText != null ? watermarkText : "内部文件";
            FontMetrics metrics = g2d.getFontMetrics();
            int textWidth = metrics.stringWidth(text);

            g2d.drawString(text, (width - textWidth) / 2, height / 2);
            g2d.dispose();

            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            ImageIO.write(watermarkedImage, "png", baos);
            return baos.toByteArray();

        } catch (Exception e) {
            log.error("添加简单水印失败", e);
            return null;
        }
    }

    public boolean isImageFile(String fileName) {
        if (fileName == null) return false;
        String lower = fileName.toLowerCase();
        return lower.endsWith(".jpg") || lower.endsWith(".jpeg")
                || lower.endsWith(".png") || lower.endsWith(".gif")
                || lower.endsWith(".bmp") || lower.endsWith(".webp");
    }
}
