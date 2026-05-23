package com.emailmarketing.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.emailmarketing.common.Result;
import com.emailmarketing.entity.Recipient;
import com.emailmarketing.entity.RecipientGroup;
import com.emailmarketing.service.RecipientGroupService;
import com.emailmarketing.service.RecipientService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/recipients")
public class RecipientController {

    @Autowired
    private RecipientGroupService groupService;

    @Autowired
    private RecipientService recipientService;

    @GetMapping("/groups")
    public Result<Page<RecipientGroup>> listGroups(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String name) {
        return Result.success(groupService.listGroups(page, size, name));
    }

    @GetMapping("/groups/{id}")
    public Result<RecipientGroup> getGroupById(@PathVariable Long id) {
        return Result.success(groupService.getGroupById(id));
    }

    @PostMapping("/groups")
    public Result<Void> createGroup(@RequestBody RecipientGroup group) {
        boolean success = groupService.createGroup(group);
        return success ? Result.success() : Result.error("创建失败");
    }

    @PutMapping("/groups")
    public Result<Void> updateGroup(@RequestBody RecipientGroup group) {
        boolean success = groupService.updateGroup(group);
        return success ? Result.success() : Result.error("更新失败");
    }

    @DeleteMapping("/groups/{id}")
    public Result<Void> deleteGroup(@PathVariable Long id) {
        boolean success = groupService.deleteGroup(id);
        return success ? Result.success() : Result.error("删除失败");
    }

    @GetMapping
    public Result<Page<Recipient>> listRecipients(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) Long groupId,
            @RequestParam(required = false) String email,
            @RequestParam(required = false) Integer status) {
        return Result.success(recipientService.listRecipients(page, size, groupId, email, status));
    }

    @GetMapping("/{id}")
    public Result<Recipient> getRecipientById(@PathVariable Long id) {
        return Result.success(recipientService.getRecipientById(id));
    }

    @PostMapping
    public Result<Void> createRecipient(@RequestBody Recipient recipient) {
        boolean success = recipientService.createRecipient(recipient);
        return success ? Result.success() : Result.error("创建失败");
    }

    @PutMapping
    public Result<Void> updateRecipient(@RequestBody Recipient recipient) {
        boolean success = recipientService.updateRecipient(recipient);
        return success ? Result.success() : Result.error("更新失败");
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteRecipient(@PathVariable Long id) {
        boolean success = recipientService.deleteRecipient(id);
        return success ? Result.success() : Result.error("删除失败");
    }

    @PostMapping("/import")
    public Result<Map<String, Integer>> importFromCsv(
            @RequestParam Long groupId,
            @RequestParam("file") MultipartFile file) {
        try {
            int count = recipientService.importFromCsv(groupId, file);
            Map<String, Integer> result = new HashMap<>();
            result.put("importCount", count);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("导入失败: " + e.getMessage());
        }
    }
}
