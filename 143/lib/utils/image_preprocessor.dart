import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;

class ImagePreprocessor {
  static Future<Uint8List> preprocessForOCR(
    Uint8List imageData, {
    int targetWidth = 2000,
    bool applyBinarization = true,
    bool applyDenoising = true,
    bool applyContrast = true,
    bool applySharpening = true,
  }) async {
    img.Image? image = img.decodeImage(imageData);
    if (image == null) {
      throw Exception('Failed to decode image');
    }

    image = await _resizeImage(image, targetWidth);
    
    if (applyContrast) {
      image = _adjustContrast(image, 1.5);
    }
    
    if (applyBinarization) {
      image = _otsuBinarization(image);
    }
    
    if (applyDenoising) {
      image = _adaptiveMedianDenoise(image);
    }
    
    if (applySharpening) {
      image = _unsharpMask(image);
    }

    return Uint8List.fromList(img.encodePng(image));
  }

  static Future<img.Image> _resizeImage(img.Image image, int targetWidth) async {
    final ratio = targetWidth / image.width;
    final targetHeight = (image.height * ratio).round();
    return img.copyResize(image, width: targetWidth, height: targetHeight);
  }

  static img.Image _adjustContrast(img.Image image, double factor) {
    final result = img.Image(width: image.width, height: image.height);
    
    for (int y = 0; y < image.height; y++) {
      for (int x = 0; x < image.width; x++) {
        final pixel = image.getPixel(x, y);
        final r = ((pixel.r - 128) * factor + 128).clamp(0, 255).toInt();
        final g = ((pixel.g - 128) * factor + 128).clamp(0, 255).toInt();
        final b = ((pixel.b - 128) * factor + 128).clamp(0, 255).toInt();
        result.setPixel(x, y, img.ColorRgba8(r, g, b, pixel.a.toInt()));
      }
    }
    
    return result;
  }

  static img.Image _otsuBinarization(img.Image image) {
    final grayscale = img.grayscale(image);
    final histogram = List<int>.filled(256, 0);
    
    for (int y = 0; y < grayscale.height; y++) {
      for (int x = 0; x < grayscale.width; x++) {
        final pixel = grayscale.getPixel(x, y);
        final intensity = pixel.r.toInt();
        histogram[intensity]++;
      }
    }

    final total = grayscale.width * grayscale.height;
    double sum = 0;
    for (int i = 0; i < 256; i++) {
      sum += i * histogram[i];
    }

    double sumB = 0;
    int wB = 0;
    int wF = 0;
    double varMax = 0;
    int threshold = 0;

    for (int t = 0; t < 256; t++) {
      wB += histogram[t];
      if (wB == 0) continue;

      wF = total - wB;
      if (wF == 0) break;

      sumB += t * histogram[t];
      final mB = sumB / wB;
      final mF = (sum - sumB) / wF;
      final varBetween = wB * wF * (mB - mF) * (mB - mF);

      if (varBetween > varMax) {
        varMax = varBetween;
        threshold = t;
      }
    }

    final result = img.Image(width: image.width, height: image.height);
    
    for (int y = 0; y < grayscale.height; y++) {
      for (int x = 0; x < grayscale.width; x++) {
        final pixel = grayscale.getPixel(x, y);
        final value = pixel.r.toInt() > threshold ? 255 : 0;
        result.setPixel(x, y, img.ColorRgba8(value, value, value, 255));
      }
    }

    return result;
  }

  static img.Image _adaptiveMedianDenoise(img.Image image, {int maxWindowSize = 7}) {
    final result = img.Image(width: image.width, height: image.height);
    final halfWindow = maxWindowSize ~/ 2;

    for (int y = 0; y < image.height; y++) {
      for (int x = 0; x < image.width; x++) {
        int windowSize = 3;
        int? newValue;

        while (windowSize <= maxWindowSize && newValue == null) {
          final half = windowSize ~/ 2;
          final window = <int>[];

          for (int dy = -half; dy <= half; dy++) {
            for (int dx = -half; dx <= half; dx++) {
              final nx = x + dx;
              final ny = y + dy;
              if (nx >= 0 && nx < image.width && ny >= 0 && ny < image.height) {
                final pixel = image.getPixel(nx, ny);
                window.add(pixel.r.toInt());
              }
            }
          }

          window.sort();
          final median = window[window.length ~/ 2];
          final min = window.first;
          final max = window.last;
          final current = image.getPixel(x, y).r.toInt();

          if (median > min && median < max) {
            if (current > min && current < max) {
              newValue = current;
            } else {
              newValue = median;
            }
          } else {
            windowSize += 2;
          }
        }

        final v = newValue ?? image.getPixel(x, y).r.toInt();
        result.setPixel(x, y, img.ColorRgba8(v, v, v, 255));
      }
    }

    return result;
  }

  static img.Image _unsharpMask(img.Image image, {double sigma = 1.0, double amount = 0.5}) {
    final blurred = img.gaussianBlur(image, radius: sigma.toInt());
    final result = img.Image(width: image.width, height: image.height);

    for (int y = 0; y < image.height; y++) {
      for (int x = 0; x < image.width; x++) {
        final original = image.getPixel(x, y);
        final blurPixel = blurred.getPixel(x, y);

        final r = (original.r + (original.r - blurPixel.r) * amount).clamp(0, 255).toInt();
        final g = (original.g + (original.g - blurPixel.g) * amount).clamp(0, 255).toInt();
        final b = (original.b + (original.b - blurPixel.b) * amount).clamp(0, 255).toInt();

        result.setPixel(x, y, img.ColorRgba8(r, g, b, original.a.toInt()));
      }
    }

    return result;
  }

  static Future<Uint8List> cropToContent(Uint8List imageData) async {
    img.Image? image = img.decodeImage(imageData);
    if (image == null) {
      throw Exception('Failed to decode image');
    }

    final grayscale = img.grayscale(image);
    
    int minX = grayscale.width;
    int maxX = 0;
    int minY = grayscale.height;
    int maxY = 0;
    const threshold = 240;

    for (int y = 0; y < grayscale.height; y++) {
      for (int x = 0; x < grayscale.width; x++) {
        final pixel = grayscale.getPixel(x, y);
        if (pixel.r.toInt() < threshold) {
          if (x < minX) minX = x;
          if (x > maxX) maxX = x;
          if (y < minY) minY = y;
          if (y > maxY) maxY = y;
        }
      }
    }

    const padding = 20;
    minX = max(0, minX - padding);
    maxX = min(grayscale.width - 1, maxX + padding);
    minY = max(0, minY - padding);
    maxY = min(grayscale.height - 1, maxY + padding);

    if (minX >= maxX || minY >= maxY) {
      return imageData;
    }

    final cropped = img.copyCrop(
      image,
      x: minX,
      y: minY,
      width: maxX - minX + 1,
      height: maxY - minY + 1,
    );

    return Uint8List.fromList(img.encodePng(cropped));
  }

  static Future<Uint8List> deskewImage(Uint8List imageData) async {
    img.Image? image = img.decodeImage(imageData);
    if (image == null) {
      throw Exception('Failed to decode image');
    }

    final grayscale = img.grayscale(image);
    final edges = _detectEdges(grayscale);
    final angle = _calculateSkewAngle(edges);

    if (angle.abs() > 0.5) {
      final rotated = img.copyRotate(image, angle: angle);
      return Uint8List.fromList(img.encodePng(rotated));
    }

    return imageData;
  }

  static img.Image _detectEdges(img.Image image) {
    final result = img.Image(width: image.width, height: image.height);
    
    const List<int> sobelX = [-1, 0, 1, -2, 0, 2, -1, 0, 1];
    const List<int> sobelY = [-1, -2, -1, 0, 0, 0, 1, 2, 1];

    for (int y = 1; y < image.height - 1; y++) {
      for (int x = 1; x < image.width - 1; x++) {
        int gx = 0, gy = 0;
        int idx = 0;

        for (int dy = -1; dy <= 1; dy++) {
          for (int dx = -1; dx <= 1; dx++) {
            final pixel = image.getPixel(x + dx, y + dy);
            gx += pixel.r.toInt() * sobelX[idx];
            gy += pixel.r.toInt() * sobelY[idx];
            idx++;
          }
        }

        final magnitude = sqrt(gx * gx + gy * gy).toInt().clamp(0, 255);
        result.setPixel(x, y, img.ColorRgba8(magnitude, magnitude, magnitude, 255));
      }
    }

    return result;
  }

  static double _calculateSkewAngle(img.Image edges) {
    final hough = <double, int>{};
    final centerX = edges.width / 2;
    final centerY = edges.height / 2;
    final maxRadius = sqrt(centerX * centerX + centerY * centerY);

    for (int y = 0; y < edges.height; y++) {
      for (int x = 0; x < edges.width; x++) {
        final pixel = edges.getPixel(x, y);
        if (pixel.r.toInt() > 128) {
          for (int angle = -45; angle <= 45; angle++) {
            final rad = angle * pi / 180;
            final rho = (x - centerX) * cos(rad) + (y - centerY) * sin(rad);
            final quantizedRho = (rho * 2).round() / 2;
            hough[quantizedRho] = (hough[quantizedRho] ?? 0) + 1;
          }
        }
      }
    }

    if (hough.isEmpty) return 0.0;

    final maxEntry = hough.entries.reduce((a, b) => a.value > b.value ? a : b);
    return maxEntry.key;
  }
}

class OCRPreprocessingPipeline {
  static Future<Uint8List> processImage(Uint8List imageData) async {
    Uint8List result = imageData;
    
    result = await ImagePreprocessor.deskewImage(result);
    
    result = await ImagePreprocessor.cropToContent(result);
    
    result = await ImagePreprocessor.preprocessForOCR(
      result,
      applyBinarization: true,
      applyDenoising: true,
      applyContrast: true,
      applySharpening: true,
    );

    return result;
  }
}
