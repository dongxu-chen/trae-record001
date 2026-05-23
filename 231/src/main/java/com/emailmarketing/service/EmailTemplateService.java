package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.entity.EmailTemplate;
import com.emailmarketing.mapper.EmailTemplateMapper;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class EmailTemplateService extends ServiceImpl<EmailTemplateMapper, EmailTemplate> {

    public Page<EmailTemplate> listTemplates(int page, int size, String name, Integer status) {
        Page<EmailTemplate> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<EmailTemplate> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(name)) {
            wrapper.like(EmailTemplate::getName, name);
        }
        if (status != null) {
            wrapper.eq(EmailTemplate::getStatus, status);
        }
        wrapper.orderByDesc(EmailTemplate::getCreatedAt);
        return page(pageParam, wrapper);
    }

    public EmailTemplate getTemplateById(Long id) {
        return getById(id);
    }

    public boolean createTemplate(EmailTemplate template) {
        template.setStatus(1);
        return save(template);
    }

    public boolean updateTemplate(EmailTemplate template) {
        return updateById(template);
    }

    public boolean deleteTemplate(Long id) {
        return removeById(id);
    }

    public boolean updateStatus(Long id, Integer status) {
        EmailTemplate template = new EmailTemplate();
        template.setId(id);
        template.setStatus(status);
        return updateById(template);
    }
}
