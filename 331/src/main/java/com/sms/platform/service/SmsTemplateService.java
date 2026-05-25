package com.sms.platform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.sms.platform.common.exception.BusinessException;
import com.sms.platform.entity.SmsTemplate;
import com.sms.platform.mapper.SmsTemplateMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.util.List;

@Slf4j
@Service
public class SmsTemplateService {

    @Resource
    private SmsTemplateMapper templateMapper;

    public void addTemplate(SmsTemplate template) {
        SmsTemplate exists = templateMapper.selectOne(
                new LambdaQueryWrapper<SmsTemplate>()
                        .eq(SmsTemplate::getTemplateCode, template.getTemplateCode())
                        .eq(SmsTemplate::getChannelCode, template.getChannelCode())
                        .eq(SmsTemplate::getDeleted, 0)
        );
        if (exists != null) {
            throw new BusinessException("该模板编码在该通道下已存在");
        }
        templateMapper.insert(template);
        log.info("添加模板成功: {}", template.getTemplateName());
    }

    public void updateTemplate(SmsTemplate template) {
        SmsTemplate exists = templateMapper.selectById(template.getId());
        if (exists == null || exists.getDeleted() == 1) {
            throw new BusinessException("模板不存在");
        }
        templateMapper.updateById(template);
        log.info("更新模板成功: id={}", template.getId());
    }

    public void deleteTemplate(Long id) {
        SmsTemplate template = templateMapper.selectById(id);
        if (template == null || template.getDeleted() == 1) {
            throw new BusinessException("模板不存在");
        }
        template.setDeleted(1);
        templateMapper.updateById(template);
        log.info("删除模板成功: id={}", id);
    }

    public SmsTemplate getTemplate(Long id) {
        SmsTemplate template = templateMapper.selectById(id);
        if (template == null || template.getDeleted() == 1) {
            throw new BusinessException("模板不存在");
        }
        return template;
    }

    public Page<SmsTemplate> listTemplates(Integer pageNum, Integer pageSize, Integer smsType, Integer channelCode, Integer status, String templateCode) {
        Page<SmsTemplate> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<SmsTemplate> wrapper = new LambdaQueryWrapper<SmsTemplate>()
                .eq(SmsTemplate::getDeleted, 0)
                .orderByDesc(SmsTemplate::getCreateTime);

        if (smsType != null) {
            wrapper.eq(SmsTemplate::getSmsType, smsType);
        }
        if (channelCode != null) {
            wrapper.eq(SmsTemplate::getChannelCode, channelCode);
        }
        if (status != null) {
            wrapper.eq(SmsTemplate::getStatus, status);
        }
        if (templateCode != null && !templateCode.isEmpty()) {
            wrapper.like(SmsTemplate::getTemplateCode, templateCode);
        }

        return templateMapper.selectPage(page, wrapper);
    }

    public List<SmsTemplate> listAllTemplates() {
        return templateMapper.selectList(
                new LambdaQueryWrapper<SmsTemplate>()
                        .eq(SmsTemplate::getStatus, 1)
                        .eq(SmsTemplate::getDeleted, 0)
                        .orderByDesc(SmsTemplate::getCreateTime)
        );
    }
}
