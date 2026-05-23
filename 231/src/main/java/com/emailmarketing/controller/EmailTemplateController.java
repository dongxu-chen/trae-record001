package com.emailmarketing.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.emailmarketing.common.Result;
import com.emailmarketing.entity.EmailTemplate;
import com.emailmarketing.service.EmailTemplateService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/templates")
public class EmailTemplateController {

    @Autowired
    private EmailTemplateService templateService;

    @GetMapping
    public Result<Page<EmailTemplate>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) Integer status) {
        return Result.success(templateService.listTemplates(page, size, name, status));
    }

    @GetMapping("/{id}")
    public Result<EmailTemplate> getById(@PathVariable Long id) {
        return Result.success(templateService.getTemplateById(id));
    }

    @PostMapping
    public Result<Void> create(@RequestBody EmailTemplate template) {
        boolean success = templateService.createTemplate(template);
        return success ? Result.success() : Result.error("创建失败");
    }

    @PutMapping
    public Result<Void> update(@RequestBody EmailTemplate template) {
        boolean success = templateService.updateTemplate(template);
        return success ? Result.success() : Result.error("更新失败");
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        boolean success = templateService.deleteTemplate(id);
        return success ? Result.success() : Result.error("删除失败");
    }

    @PutMapping("/{id}/status")
    public Result<Void> updateStatus(@PathVariable Long id, @RequestParam Integer status) {
        boolean success = templateService.updateStatus(id, status);
        return success ? Result.success() : Result.error("状态更新失败");
    }
}
