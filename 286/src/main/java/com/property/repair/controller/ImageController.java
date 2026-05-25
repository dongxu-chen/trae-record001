package com.property.repair.controller;

import com.property.repair.common.Result;
import com.property.repair.service.ImageService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/image")
@CrossOrigin
public class ImageController {

    @Autowired
    private ImageService imageService;

    @PostMapping("/upload")
    public Result<Map<String, String>> upload(@RequestParam("file") MultipartFile file) {
        try {
            Map<String, String> result = imageService.uploadImage(file);
            return Result.success(result);
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IOException e) {
            return Result.error("文件上传失败：" + e.getMessage());
        }
    }

    @PostMapping("/batch")
    public Result<List<Map<String, String>>> batchUpload(@RequestParam("files") MultipartFile[] files) {
        try {
            List<Map<String, String>> results = imageService.uploadImages(files);
            return Result.success(results);
        } catch (IOException e) {
            return Result.error("文件上传失败：" + e.getMessage());
        }
    }

    @DeleteMapping("/delete")
    public Result<Void> delete(@RequestParam("url") String url) {
        boolean deleted = imageService.deleteImage(url);
        if (deleted) {
            return Result.success();
        } else {
            return Result.error("删除失败");
        }
    }
}
