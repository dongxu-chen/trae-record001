package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.entity.CategoryPreference;
import com.emailmarketing.entity.ProductCategory;
import com.emailmarketing.entity.UserBehavior;
import com.emailmarketing.mapper.UserBehaviorMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
public class UserBehaviorService extends ServiceImpl<UserBehaviorMapper, UserBehavior> {

    @Autowired
    private CategoryPreferenceService preferenceService;

    @Autowired
    private ProductCategoryService categoryService;

    public void recordBehavior(Long recipientId, String email, Long taskId, Integer behaviorType,
                               String itemCategory, String itemId, Integer stayDuration) {
        UserBehavior behavior = new UserBehavior();
        behavior.setRecipientId(recipientId);
        behavior.setEmail(email);
        behavior.setTaskId(taskId);
        behavior.setBehaviorType(behaviorType);
        behavior.setItemCategory(itemCategory);
        behavior.setItemId(itemId);
        behavior.setBehaviorTime(LocalDateTime.now());
        behavior.setStayDuration(stayDuration != null ? stayDuration : 0);
        behavior.setClickCount(1);
        behavior.setCreatedAt(LocalDateTime.now());
        save(behavior);

        if (itemCategory != null && !itemCategory.isEmpty()) {
            updateCategoryPreference(recipientId, email, itemCategory, behaviorType);
        }
    }

    private void updateCategoryPreference(Long recipientId, String email, String categoryCode, Integer behaviorType) {
        BigDecimal scoreIncrement = switch (behaviorType) {
            case 2 -> BigDecimal.ONE;
            case 3 -> new BigDecimal("3");
            case 5 -> new BigDecimal("10");
            default -> BigDecimal.ZERO;
        };

        if (scoreIncrement.compareTo(BigDecimal.ZERO) > 0) {
            preferenceService.updatePreference(recipientId, email, categoryCode, behaviorType, scoreIncrement);
        }
    }

    public List<ProductCategory> getRecommendedCategories(Long recipientId, String email, int limit) {
        List<CategoryPreference> preferences = preferenceService.getTopPreferences(recipientId, email, limit);
        
        if (preferences.isEmpty()) {
            return getPopularCategories(limit);
        }

        List<String> categoryCodes = preferences.stream()
                .map(CategoryPreference::getCategoryCode)
                .toList();

        return categoryService.getCategoriesByCodes(categoryCodes);
    }

    public String getRecommendedCategoriesAsKeywords(Long recipientId, String email, int limit) {
        List<ProductCategory> categories = getRecommendedCategories(recipientId, email, limit);
        Set<String> keywords = new LinkedHashSet<>();
        
        for (ProductCategory category : categories) {
            if (category.getKeywords() != null && !category.getKeywords().isEmpty()) {
                String[] parts = category.getKeywords().split(",");
                for (String part : parts) {
                    keywords.add(part.trim());
                }
            }
            keywords.add(category.getCategoryName());
        }

        return String.join(",", keywords);
    }

    private List<ProductCategory> getPopularCategories(int limit) {
        LambdaQueryWrapper<ProductCategory> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ProductCategory::getStatus, 1);
        wrapper.orderByAsc(ProductCategory::getId);
        wrapper.last("LIMIT " + limit);
        return categoryService.list(wrapper);
    }

    public Map<String, Object> getUserBehaviorSummary(Long recipientId, String email, int days) {
        Map<String, Object> summary = new HashMap<>();
        LocalDateTime startTime = LocalDateTime.now().minusDays(days);

        LambdaQueryWrapper<UserBehavior> wrapper = new LambdaQueryWrapper<>();
        wrapper.and(w -> w.eq(UserBehavior::getRecipientId, recipientId).or().eq(UserBehavior::getEmail, email));
        wrapper.ge(UserBehavior::getBehaviorTime, startTime);
        List<UserBehavior> behaviors = list(wrapper);

        int openCount = 0, clickCount = 0, conversionCount = 0;
        Map<String, Integer> categoryCounts = new HashMap<>();

        for (UserBehavior behavior : behaviors) {
            switch (behavior.getBehaviorType()) {
                case 2 -> openCount++;
                case 3 -> clickCount++;
                case 5 -> conversionCount++;
            }
            if (behavior.getItemCategory() != null) {
                categoryCounts.merge(behavior.getItemCategory(), 1, Integer::sum);
            }
        }

        summary.put("openCount", openCount);
        summary.put("clickCount", clickCount);
        summary.put("conversionCount", conversionCount);
        summary.put("categoryCounts", categoryCounts);
        summary.put("totalBehaviors", behaviors.size());

        return summary;
    }
}
