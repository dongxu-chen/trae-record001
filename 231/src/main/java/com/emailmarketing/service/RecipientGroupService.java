package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.entity.RecipientGroup;
import com.emailmarketing.mapper.RecipientGroupMapper;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class RecipientGroupService extends ServiceImpl<RecipientGroupMapper, RecipientGroup> {

    public Page<RecipientGroup> listGroups(int page, int size, String name) {
        Page<RecipientGroup> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<RecipientGroup> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(name)) {
            wrapper.like(RecipientGroup::getName, name);
        }
        wrapper.orderByDesc(RecipientGroup::getCreatedAt);
        return page(pageParam, wrapper);
    }

    public RecipientGroup getGroupById(Long id) {
        return getById(id);
    }

    public boolean createGroup(RecipientGroup group) {
        group.setRecipientCount(0);
        return save(group);
    }

    public boolean updateGroup(RecipientGroup group) {
        return updateById(group);
    }

    public boolean deleteGroup(Long id) {
        return removeById(id);
    }

    public void updateRecipientCount(Long groupId, int count) {
        RecipientGroup group = new RecipientGroup();
        group.setId(groupId);
        group.setRecipientCount(count);
        updateById(group);
    }
}
