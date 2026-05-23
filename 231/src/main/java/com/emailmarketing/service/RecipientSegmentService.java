package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.entity.*;
import com.emailmarketing.mapper.RecipientSegmentMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
public class RecipientSegmentService extends ServiceImpl<RecipientSegmentMapper, RecipientSegment> {

    @Autowired
    private RecipientSegmentMemberService memberService;

    @Autowired
    private UserBehaviorService behaviorService;

    @Autowired
    private CategoryPreferenceService preferenceService;

    @Autowired
    private RecipientService recipientService;

    public Page<RecipientSegment> listSegments(int page, int size, String name, Integer type) {
        Page<RecipientSegment> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<RecipientSegment> wrapper = new LambdaQueryWrapper<>();
        if (name != null && !name.isEmpty()) {
            wrapper.like(RecipientSegment::getSegmentName, name);
        }
        if (type != null) {
            wrapper.eq(RecipientSegment::getSegmentType, type);
        }
        wrapper.orderByDesc(RecipientSegment::getCreatedAt);
        return page(pageParam, wrapper);
    }

    @Transactional(rollbackFor = Exception.class)
    public boolean createSegment(RecipientSegment segment) {
        segment.setRecipientCount(0);
        segment.setStatus(1);
        segment.setAutoRefresh(1);
        boolean saved = save(segment);
        if (saved) {
            refreshSegment(segment.getId());
        }
        return saved;
    }

    @Transactional(rollbackFor = Exception.class)
    public void refreshSegment(Long segmentId) {
        RecipientSegment segment = getById(segmentId);
        if (segment == null) return;

        memberService.remove(new LambdaQueryWrapper<RecipientSegmentMember>()
                .eq(RecipientSegmentMember::getSegmentId, segmentId));

        List<Recipient> recipients = switch (segment.getSegmentType()) {
            case 1 -> generateBehaviorSegment(segment);
            case 3 -> generateRecommendationSegment(segment);
            default -> new ArrayList<>();
        };

        List<RecipientSegmentMember> members = new ArrayList<>();
        for (Recipient recipient : recipients) {
            RecipientSegmentMember member = new RecipientSegmentMember();
            member.setSegmentId(segmentId);
            member.setRecipientId(recipient.getId());
            member.setEmail(recipient.getEmail());
            member.setScore(calculateMatchScore(recipient, segment));
            member.setCreatedAt(LocalDateTime.now());
            members.add(member);
        }

        if (!members.isEmpty()) {
            memberService.saveBatch(members);
        }

        segment.setRecipientCount(members.size());
        segment.setLastRefreshTime(LocalDateTime.now());
        updateById(segment);
    }

    private List<Recipient> generateBehaviorSegment(RecipientSegment segment) {
        List<Recipient> result = new ArrayList<>();
        List<Recipient> allRecipients = recipientService.list();

        for (Recipient recipient : allRecipients) {
            Map<String, Object> summary = behaviorService.getUserBehaviorSummary(
                    recipient.getId(), recipient.getEmail(), 30);
            
            int totalBehaviors = (int) summary.getOrDefault("totalBehaviors", 0);
            if (totalBehaviors >= 1) {
                result.add(recipient);
            }
        }
        return result;
    }

    private List<Recipient> generateRecommendationSegment(RecipientSegment segment) {
        List<Recipient> result = new ArrayList<>();
        List<Recipient> allRecipients = recipientService.list();

        for (Recipient recipient : allRecipients) {
            List<CategoryPreference> preferences = preferenceService.getTopPreferences(
                    recipient.getId(), recipient.getEmail(), 3);
            
            if (!preferences.isEmpty()) {
                BigDecimal totalScore = preferences.stream()
                        .map(CategoryPreference::getPreferenceScore)
                        .reduce(BigDecimal.ZERO, BigDecimal::add);
                
                if (totalScore.compareTo(new BigDecimal("5")) >= 0) {
                    result.add(recipient);
                }
            }
        }
        return result;
    }

    private BigDecimal calculateMatchScore(Recipient recipient, RecipientSegment segment) {
        List<CategoryPreference> preferences = preferenceService.getTopPreferences(
                recipient.getId(), recipient.getEmail(), 3);
        
        if (preferences.isEmpty()) {
            return BigDecimal.ZERO;
        }
        
        return preferences.stream()
                .map(CategoryPreference::getPreferenceScore)
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .min(new BigDecimal("100"));
    }

    @Scheduled(cron = "0 0 2 * * ?")
    public void autoRefreshSegments() {
        LambdaQueryWrapper<RecipientSegment> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(RecipientSegment::getStatus, 1);
        wrapper.eq(RecipientSegment::getAutoRefresh, 1);
        
        List<RecipientSegment> segments = list(wrapper);
        for (RecipientSegment segment : segments) {
            try {
                refreshSegment(segment.getId());
                log.info("Auto refreshed segment: {}", segment.getSegmentName());
            } catch (Exception e) {
                log.error("Failed to refresh segment: {}", segment.getSegmentName(), e);
            }
        }
    }

    public List<RecipientSegmentMember> getSegmentMembers(Long segmentId, int page, int size) {
        LambdaQueryWrapper<RecipientSegmentMember> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(RecipientSegmentMember::getSegmentId, segmentId);
        wrapper.orderByDesc(RecipientSegmentMember::getScore);
        wrapper.last("LIMIT " + (page - 1) * size + ", " + size);
        return memberService.list(wrapper);
    }

    public Map<String, Object> getRecommendedForRecipient(Long recipientId, String email) {
        Map<String, Object> result = new HashMap<>();
        
        List<ProductCategory> categories = behaviorService.getRecommendedCategories(recipientId, email, 5);
        result.put("categories", categories);
        
        String keywords = behaviorService.getRecommendedCategoriesAsKeywords(recipientId, email, 5);
        result.put("keywords", keywords);
        
        List<CategoryPreference> preferences = preferenceService.getTopPreferences(recipientId, email, 10);
        result.put("preferences", preferences);
        
        return result;
    }
}
