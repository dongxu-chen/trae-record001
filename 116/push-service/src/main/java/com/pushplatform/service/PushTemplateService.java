package com.pushplatform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.pushplatform.dto.PushTemplateDTO;
import com.pushplatform.entity.PushTemplate;
import com.pushplatform.mapper.PushTemplateMapper;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class PushTemplateService extends ServiceImpl<PushTemplateMapper, PushTemplate> {

    public List<PushTemplate> list(String channel, Integer status) {
        LambdaQueryWrapper<PushTemplate> wrapper = new LambdaQueryWrapper<>();
        if (channel != null) {
            wrapper.eq(PushTemplate::getChannel, channel);
        }
        if (status != null) {
            wrapper.eq(PushTemplate::getStatus, status);
        }
        wrapper.orderByDesc(PushTemplate::getCreateTime);
        return list(wrapper);
    }

    public PushTemplate getByCode(String templateCode) {
        return getOne(new LambdaQueryWrapper<PushTemplate>().eq(PushTemplate::getTemplateCode, templateCode));
    }

    public boolean create(PushTemplateDTO dto) {
        PushTemplate template = new PushTemplate();
        BeanUtils.copyProperties(dto, template);
        template.setCreateTime(LocalDateTime.now());
        template.setUpdateTime(LocalDateTime.now());
        template.setStatus(dto.getStatus() == null ? 1 : dto.getStatus());
        return save(template);
    }

    public boolean update(PushTemplateDTO dto) {
        PushTemplate template = new PushTemplate();
        BeanUtils.copyProperties(dto, template);
        template.setUpdateTime(LocalDateTime.now());
        return updateById(template);
    }

    public boolean delete(Long id) {
        return removeById(id);
    }
}
