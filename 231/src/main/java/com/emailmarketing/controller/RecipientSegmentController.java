package com.emailmarketing.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.emailmarketing.common.Result;
import com.emailmarketing.entity.RecipientSegment;
import com.emailmarketing.entity.RecipientSegmentMember;
import com.emailmarketing.service.RecipientSegmentService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/segments")
public class RecipientSegmentController {

    @Autowired
    private RecipientSegmentService segmentService;

    @GetMapping
    public Result<Page<RecipientSegment>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) Integer type) {
        return Result.success(segmentService.listSegments(page, size, name, type));
    }

    @GetMapping("/{id}")
    public Result<RecipientSegment> getById(@PathVariable Long id) {
        return Result.success(segmentService.getById(id));
    }

    @PostMapping
    public Result<Void> create(@RequestBody RecipientSegment segment) {
        boolean success = segmentService.createSegment(segment);
        return success ? Result.success() : Result.error("创建失败");
    }

    @PostMapping("/{id}/refresh")
    public Result<Void> refresh(@PathVariable Long id) {
        segmentService.refreshSegment(id);
        return Result.success();
    }

    @GetMapping("/{id}/members")
    public Result<List<RecipientSegmentMember>> getMembers(
            @PathVariable Long id,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        return Result.success(segmentService.getSegmentMembers(id, page, size));
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        boolean success = segmentService.removeById(id);
        return success ? Result.success() : Result.error("删除失败");
    }

    @GetMapping("/recommend/{recipientId}")
    public Result<Map<String, Object>> getRecommendations(
            @PathVariable Long recipientId,
            @RequestParam String email) {
        return Result.success(segmentService.getRecommendedForRecipient(recipientId, email));
    }
}
