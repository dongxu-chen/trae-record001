package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.entity.AbTestVariant;
import com.emailmarketing.mapper.AbTestVariantMapper;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class AbTestVariantService extends ServiceImpl<AbTestVariantMapper, AbTestVariant> {

    public List<AbTestVariant> getVariantsByTestId(Long testId) {
        LambdaQueryWrapper<AbTestVariant> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(AbTestVariant::getTestId, testId);
        wrapper.orderByAsc(AbTestVariant::getId);
        return list(wrapper);
    }
}
