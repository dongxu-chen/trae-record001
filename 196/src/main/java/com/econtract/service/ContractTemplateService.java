package com.econtract.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.econtract.common.BusinessException;
import com.econtract.common.ResultCode;
import com.econtract.dto.TemplateDTO;
import com.econtract.entity.ContractTemplate;
import com.econtract.mapper.ContractTemplateMapper;
import com.econtract.security.UserContext;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.io.File;
import java.io.IOException;
import java.util.UUID;

@Slf4j
@Service
public class ContractTemplateService {

    @Value("${file.template-path}")
    private String templatePath;

    @Resource
    private ContractTemplateMapper templateMapper;

    public Page<ContractTemplate> getTemplatePage(int pageNum, int pageSize, String templateName, String templateType) {
        Page<ContractTemplate> page = new Page<>(pageNum, pageSize);
        QueryWrapper<ContractTemplate> wrapper = new QueryWrapper<>();
        if (templateName != null && !templateName.isEmpty()) {
            wrapper.like("template_name", templateName);
        }
        if (templateType != null && !templateType.isEmpty()) {
            wrapper.eq("template_type", templateType);
        }
        wrapper.eq("status", 1);
        wrapper.orderByDesc("create_time");
        return templateMapper.selectPage(page, wrapper);
    }

    public ContractTemplate getTemplateById(Long id) {
        ContractTemplate template = templateMapper.selectById(id);
        if (template == null) {
            throw new BusinessException(ResultCode.TEMPLATE_NOT_FOUND);
        }
        return template;
    }

    @Transactional(rollbackFor = Exception.class)
    public ContractTemplate createTemplate(TemplateDTO templateDTO, MultipartFile file) throws IOException {
        QueryWrapper<ContractTemplate> wrapper = new QueryWrapper<>();
        wrapper.eq("template_code", templateDTO.getTemplateCode());
        if (templateMapper.selectCount(wrapper) > 0) {
            throw new BusinessException(ResultCode.TEMPLATE_CODE_EXISTS);
        }
        String fileName = saveFile(file);
        ContractTemplate template = new ContractTemplate();
        template.setTemplateName(templateDTO.getTemplateName());
        template.setTemplateType(templateDTO.getTemplateType());
        template.setTemplateCode(templateDTO.getTemplateCode());
        template.setFilePath(templatePath + fileName);
        template.setFileName(file.getOriginalFilename());
        template.setFileSize(file.getSize());
        template.setFields(templateDTO.getFields());
        template.setSignPositions(templateDTO.getSignPositions());
        template.setStatus(1);
        template.setCreatorId(UserContext.getCurrentUserId());
        templateMapper.insert(template);
        return template;
    }

    @Transactional(rollbackFor = Exception.class)
    public void updateTemplate(Long id, TemplateDTO templateDTO, MultipartFile file) throws IOException {
        ContractTemplate template = getTemplateById(id);
        if (!template.getTemplateCode().equals(templateDTO.getTemplateCode())) {
            QueryWrapper<ContractTemplate> wrapper = new QueryWrapper<>();
            wrapper.eq("template_code", templateDTO.getTemplateCode());
            if (templateMapper.selectCount(wrapper) > 0) {
                throw new BusinessException(ResultCode.TEMPLATE_CODE_EXISTS);
            }
        }
        if (file != null && !file.isEmpty()) {
            deleteFile(template.getFilePath());
            String fileName = saveFile(file);
            template.setFilePath(templatePath + fileName);
            template.setFileName(file.getOriginalFilename());
            template.setFileSize(file.getSize());
        }
        template.setTemplateName(templateDTO.getTemplateName());
        template.setTemplateType(templateDTO.getTemplateType());
        template.setTemplateCode(templateDTO.getTemplateCode());
        template.setFields(templateDTO.getFields());
        template.setSignPositions(templateDTO.getSignPositions());
        templateMapper.updateById(template);
    }

    @Transactional(rollbackFor = Exception.class)
    public void deleteTemplate(Long id) {
        ContractTemplate template = getTemplateById(id);
        deleteFile(template.getFilePath());
        templateMapper.deleteById(id);
    }

    private String saveFile(MultipartFile file) throws IOException {
        File dir = new File(templatePath);
        if (!dir.exists()) {
            dir.mkdirs();
        }
        String originalName = file.getOriginalFilename();
        String extension = originalName.substring(originalName.lastIndexOf("."));
        String fileName = UUID.randomUUID().toString().replace("-", "") + extension;
        File dest = new File(templatePath + fileName);
        file.transferTo(dest);
        return fileName;
    }

    private void deleteFile(String filePath) {
        try {
            File file = new File(filePath);
            if (file.exists()) {
                file.delete();
            }
        } catch (Exception e) {
            log.warn("删除模板文件失败: {}", e.getMessage());
        }
    }
}
