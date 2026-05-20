package com.filestorage.service;

import com.filestorage.config.WatermarkConfig;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import jakarta.annotation.Resource;
import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.geom.AffineTransform;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;

@Slf4j
@Service
public class WatermarkService {

    @Resource
    private WatermarkConfig watermarkConfig;

    public byte[] addImageWatermark(InputStream imageStream, String watermarkText) throws Exception {
        BufferedImage image = ImageIO.read(imageStream);
        if (image == null) {
            throw new RuntimeException("无法读取图片");
        }

        int width = image.getWidth();
        int height = image.getHeight();

        BufferedImage watermarkedImage = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
        Graphics2D g2d = watermarkedImage.createGraphics();

        g2d.drawImage(image, 0, 0, null);

        if (watermarkConfig.isEnabled() && watermarkText != null && !watermarkText.isEmpty()) {
            applyWatermark(g2d, watermarkText, width, height);
        }

        g2d.dispose();

        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        ImageIO.write(watermarkedImage, "jpg", outputStream);
        return outputStream.toByteArray();
    }

    private void applyWatermark(Graphics2D g2d, String watermarkText, int width, int height) {
        Font font = new Font("微软雅黑", Font.PLAIN, watermarkConfig.getFontSize());
        g2d.setFont(font);

        AlphaComposite alphaComposite = AlphaComposite.getInstance(
                AlphaComposite.SRC_OVER, watermarkConfig.getOpacity());
        g2d.setComposite(alphaComposite);

        Color color = Color.decode(watermarkConfig.getColor());
        g2d.setColor(color);

        FontMetrics metrics = g2d.getFontMetrics(font);
        int textWidth = metrics.stringWidth(watermarkText);
        int textHeight = metrics.getHeight();

        double radians = Math.toRadians(watermarkConfig.getRotation());

        int intervalX = watermarkConfig.getIntervalX();
        int intervalY = watermarkConfig.getIntervalY();

        for (int y = -height; y < height * 2; y += intervalY) {
            for (int x = -width; x < width * 2; x += intervalX) {
                AffineTransform originalTransform = g2d.getTransform();
                g2d.rotate(radians, x, y);
                g2d.drawString(watermarkText, x, y);
                g2d.setTransform(originalTransform);
            }
        }
    }

    public String generateWatermarkText(String username, String ip, String timestamp) {
        StringBuilder sb = new StringBuilder();
        if (username != null && !username.isEmpty()) {
            sb.append(username);
        }
        if (ip != null && !ip.isEmpty()) {
            if (sb.length() > 0) sb.append(" | ");
            sb.append(ip);
        }
        if (timestamp != null && !timestamp.isEmpty()) {
            if (sb.length() > 0) sb.append(" | ");
            sb.append(timestamp);
        }
        return sb.toString();
    }
}
