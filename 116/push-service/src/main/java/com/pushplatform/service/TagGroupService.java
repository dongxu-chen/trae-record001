package com.pushplatform.service;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.pushplatform.dto.TagCondition;
import com.pushplatform.entity.TagGroup;
import com.pushplatform.mapper.TagGroupMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class TagGroupService extends ServiceImpl<TagGroupMapper, TagGroup> {

    private static final Logger logger = LoggerFactory.getLogger(TagGroupService.class);

    @Autowired
    private UserTagService userTagService;

    public TagGroup createGroup(String groupCode, String groupName, List<TagCondition> conditions, String remark) {
        TagGroup group = new TagGroup();
        group.setGroupCode(groupCode);
        group.setGroupName(groupName);
        group.setTagConditions(JSON.toJSONString(conditions));
        group.setStatus(1);
        group.setRemark(remark);
        group.setCreateTime(LocalDateTime.now());
        group.setUpdateTime(LocalDateTime.now());
        save(group);

        calculateGroupUserCount(group.getId());
        logger.info("Created tag group: {}", groupCode);
        return group;
    }

    public void calculateGroupUserCount(Long groupId) {
        TagGroup group = getById(groupId);
        if (group == null) {
            return;
        }

        try {
            List<TagCondition> conditions = JSON.parseArray(group.getTagConditions(), TagCondition.class);
            if (conditions == null || conditions.isEmpty()) {
                group.setUserCount(0);
                updateById(group);
                return;
            }

            Map<String, List<String>> tagUserMap = conditions.stream()
                    .collect(Collectors.toMap(
                            TagCondition::getTagCode,
                            c -> userTagService.getUserIdsByTag(c.getTagCode())
                    ));

            List<String> resultUsers = null;
            for (TagCondition condition : conditions) {
                List<String> users = tagUserMap.get(condition.getTagCode());
                if (users == null) {
                    users = new ArrayList<>();
                }

                List<String> filteredUsers = filterByCondition(users, condition);

                if (resultUsers == null) {
                    resultUsers = filteredUsers;
                } else {
                    if ("AND".equalsIgnoreCase(condition.getLogic())) {
                        resultUsers.retainAll(filteredUsers);
                    } else {
                        resultUsers.addAll(filteredUsers);
                        resultUsers = resultUsers.stream().distinct().collect(Collectors.toList());
                    }
                }
            }

            group.setUserCount(resultUsers != null ? resultUsers.size() : 0);
            group.setUpdateTime(LocalDateTime.now());
            updateById(group);

            logger.info("Calculated group user count, group: {}, count: {}", group.getGroupCode(), group.getUserCount());
        } catch (Exception e) {
            logger.error("Calculate group user count error, groupId: {}", groupId, e);
        }
    }

    private List<String> filterByCondition(List<String> users, TagCondition condition) {
        if (condition.getOperator() == null || condition.getTagValue() == null) {
            return users;
        }
        return users;
    }

    public List<String> getGroupUserIds(Long groupId) {
        TagGroup group = getById(groupId);
        if (group == null) {
            return new ArrayList<>();
        }

        try {
            List<TagCondition> conditions = JSON.parseArray(group.getTagConditions(), TagCondition.class);
            if (conditions == null || conditions.isEmpty()) {
                return new ArrayList<>();
            }

            List<String> resultUsers = null;
            for (TagCondition condition : conditions) {
                List<String> users = userTagService.getUserIdsByTag(condition.getTagCode());

                if (resultUsers == null) {
                    resultUsers = new ArrayList<>(users);
                } else {
                    if ("AND".equalsIgnoreCase(condition.getLogic())) {
                        resultUsers.retainAll(users);
                    } else {
                        resultUsers.addAll(users);
                        resultUsers = resultUsers.stream().distinct().collect(Collectors.toList());
                    }
                }
            }

            return resultUsers != null ? resultUsers : new ArrayList<>();
        } catch (Exception e) {
            logger.error("Get group user ids error, groupId: {}", groupId, e);
            return new ArrayList<>();
        }
    }

    public List<TagGroup> listActiveGroups() {
        LambdaQueryWrapper<TagGroup> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(TagGroup::getStatus, 1);
        return list(wrapper);
    }

    public boolean updateGroupStatus(Long groupId, Integer status) {
        TagGroup group = getById(groupId);
        if (group == null) {
            return false;
        }
        group.setStatus(status);
        group.setUpdateTime(LocalDateTime.now());
        return updateById(group);
    }
}
