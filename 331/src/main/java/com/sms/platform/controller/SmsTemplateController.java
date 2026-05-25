package com.sms.platform.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.sms.platform.common.Result;
import com.sms.platform.entity.SmsTemplate;
import com.sms.platform.service.SmsTemplateService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/v1/template")
public class SmsTemplateController {

    @Resource
    private SmsTemplateService templateService;

    @PostMapping
    public Result<Void> addTemplate(@RequestBody SmsTemplate template) {
        log.info("添加模板: {}", template.getTemplateName());
        templateService.addTemplate(template);
        return Result.success();
    }

    @PutMapping
    public Result<Void> updateTemplate(@RequestBody SmsTemplate template) {
        log.info("更新模板: id={}", template.getId());
        templateService.updateTemplate(template);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteTemplate(@PathVariable Long id) {
        log.info("删除模板: id={}", id);
        templateService.deleteTemplate(id);
        return Result.success();
    }

    @GetMapping("/{id}")
    public Result<SmsTemplate> getTemplate(@PathVariable Long id) {
        return Result.success(templateService.getTemplate(id));
    }

    @GetMapping("/page")
    public Result<Page<SmsTemplate>> listTemplates(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(required = false) Integer smsType,
            @RequestParam(required = false) Integer channelCode,
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) String templateCode) {
        return Result.success(templateService.listTemplates(pageNum, pageSize, smsType, channelCode, status, templateCode));
    }

    @GetMapping("/list")
    public Result<List<SmsTemplate>> listAllTemplates() {
        return Result.success(templateService.listAllTemplates());
    }
}
