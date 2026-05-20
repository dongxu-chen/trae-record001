package com.econtract.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.econtract.common.Result;
import com.econtract.dto.TemplateDTO;
import com.econtract.entity.ContractTemplate;
import com.econtract.service.ContractTemplateService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.io.IOException;

@RestController
@RequestMapping("/template")
public class ContractTemplateController {

    @Resource
    private ContractTemplateService templateService;

    @GetMapping("/page")
    public Result<Page<ContractTemplate>> getTemplatePage(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(required = false) String templateName,
            @RequestParam(required = false) String templateType) {
        return Result.success(templateService.getTemplatePage(pageNum, pageSize, templateName, templateType));
    }

    @GetMapping("/{id}")
    public Result<ContractTemplate> getTemplateById(@PathVariable Long id) {
        return Result.success(templateService.getTemplateById(id));
    }

    @PostMapping
    public Result<ContractTemplate> createTemplate(
            @RequestPart("template") @Validated TemplateDTO templateDTO,
            @RequestPart("file") MultipartFile file) throws IOException {
        return Result.success(templateService.createTemplate(templateDTO, file));
    }

    @PutMapping("/{id}")
    public Result<Void> updateTemplate(
            @PathVariable Long id,
            @RequestPart("template") @Validated TemplateDTO templateDTO,
            @RequestPart(value = "file", required = false) MultipartFile file) throws IOException {
        templateService.updateTemplate(id, templateDTO, file);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteTemplate(@PathVariable Long id) {
        templateService.deleteTemplate(id);
        return Result.success();
    }
}
