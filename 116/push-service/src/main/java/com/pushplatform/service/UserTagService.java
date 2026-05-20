package com.pushplatform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.pushplatform.entity.UserTag;
import com.pushplatform.mapper.UserTagMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class UserTagService extends ServiceImpl<UserTagMapper, UserTag> {

    private static final Logger logger = LoggerFactory.getLogger(UserTagService.class);

    public void addUserTag(String userId, String tagCode, String tagName, String tagValue) {
        try {
            LambdaQueryWrapper<UserTag> wrapper = new LambdaQueryWrapper<>();
            wrapper.eq(UserTag::getUserId, userId)
                    .eq(UserTag::getTagCode, tagCode);
            UserTag existing = getOne(wrapper);

            if (existing != null) {
                existing.setTagName(tagName);
                existing.setTagValue(tagValue);
                existing.setUpdateTime(LocalDateTime.now());
                updateById(existing);
                logger.info("Updated user tag, userId: {}, tagCode: {}", userId, tagCode);
            } else {
                UserTag userTag = new UserTag();
                userTag.setUserId(userId);
                userTag.setTagCode(tagCode);
                userTag.setTagName(tagName);
                userTag.setTagValue(tagValue);
                userTag.setCreateTime(LocalDateTime.now());
                userTag.setUpdateTime(LocalDateTime.now());
                save(userTag);
                logger.info("Added user tag, userId: {}, tagCode: {}", userId, tagCode);
            }
        } catch (Exception e) {
            logger.error("Add user tag error, userId: {}, tagCode: {}", userId, tagCode, e);
        }
    }

    @Transactional
    public void batchAddUserTags(String userId, Map<String, String> tags) {
        tags.forEach((tagCode, tagValue) -> {
            addUserTag(userId, tagCode, tagCode, tagValue);
        });
    }

    public List<UserTag> getUserTags(String userId) {
        LambdaQueryWrapper<UserTag> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserTag::getUserId, userId);
        return list(wrapper);
    }

    public void removeUserTag(String userId, String tagCode) {
        LambdaQueryWrapper<UserTag> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserTag::getUserId, userId)
                .eq(UserTag::getTagCode, tagCode);
        remove(wrapper);
        logger.info("Removed user tag, userId: {}, tagCode: {}", userId, tagCode);
    }

    public List<String> getUserIdsByTag(String tagCode) {
        return baseMapper.selectUserIdsByTagCode(tagCode);
    }

    public List<String> getUserIdsByTags(List<String> tagCodes, boolean allMatch) {
        if (tagCodes == null || tagCodes.isEmpty()) {
            return new ArrayList<>();
        }

        Map<String, List<String>> tagUserMap = tagCodes.stream()
                .collect(Collectors.toMap(tag -> tag, this::getUserIdsByTag));

        if (allMatch) {
            return tagUserMap.values().stream()
                    .reduce((a, b) -> {
                        List<String> result = new ArrayList<>(a);
                        result.retainAll(b);
                        return result;
                    })
                    .orElse(new ArrayList<>());
        } else {
            return tagUserMap.values().stream()
                    .flatMap(List::stream)
                    .distinct()
                    .collect(Collectors.toList());
        }
    }

    public Map<String, Long> getTagStats() {
        List<UserTag> allTags = list();
        return allTags.stream()
                .collect(Collectors.groupingBy(UserTag::getTagCode, Collectors.counting()));
    }
}
