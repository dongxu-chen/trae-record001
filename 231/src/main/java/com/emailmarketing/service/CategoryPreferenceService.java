package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.entity.CategoryPreference;
import com.emailmarketing.mapper.CategoryPreferenceMapper;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Service
public class CategoryPreferenceService extends ServiceImpl<CategoryPreferenceMapper, CategoryPreference> {

    public void updatePreference(Long recipientId, String email, String categoryCode,
                                 Integer behaviorType, BigDecimal scoreIncrement) {
        LambdaQueryWrapper<CategoryPreference> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(CategoryPreference::getRecipientId, recipientId);
        wrapper.eq(CategoryPreference::getCategoryCode, categoryCode);
        CategoryPreference preference = getOne(wrapper);

        if (preference == null) {
            preference = new CategoryPreference();
            preference.setRecipientId(recipientId);
            preference.setEmail(email);
            preference.setCategoryCode(categoryCode);
            preference.setPreferenceScore(scoreIncrement);
            preference.setViewCount(0);
            preference.setClickCount(0);
            preference.setConversionCount(0);
            preference.setCreatedAt(LocalDateTime.now());
            preference.setUpdatedAt(LocalDateTime.now());

            switch (behaviorType) {
                case 2 -> preference.setViewCount(1);
                case 3 -> preference.setClickCount(1);
                case 5 -> preference.setConversionCount(1);
            }
            save(preference);
        } else {
            LambdaUpdateWrapper<CategoryPreference> updateWrapper = new LambdaUpdateWrapper<>();
            updateWrapper.eq(CategoryPreference::getId, preference.getId());
            updateWrapper.setSql("preference_score = preference_score + " + scoreIncrement);
            updateWrapper.setSql("last_behavior_time = NOW()");

            switch (behaviorType) {
                case 2 -> updateWrapper.setSql("view_count = view_count + 1");
                case 3 -> updateWrapper.setSql("click_count = click_count + 1");
                case 5 -> updateWrapper.setSql("conversion_count = conversion_count + 1");
            }

            update(updateWrapper);
        }
    }

    public List<CategoryPreference> getTopPreferences(Long recipientId, String email, int limit) {
        LambdaQueryWrapper<CategoryPreference> wrapper = new LambdaQueryWrapper<>();
        wrapper.and(w -> w.eq(CategoryPreference::getRecipientId, recipientId)
                .or().eq(CategoryPreference::getEmail, email));
        wrapper.orderByDesc(CategoryPreference::getPreferenceScore);
        wrapper.last("LIMIT " + limit);
        return list(wrapper);
    }
}
