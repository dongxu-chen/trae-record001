package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.entity.Recipient;
import com.emailmarketing.mapper.RecipientMapper;
import com.opencsv.CSVReader;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;

@Service
public class RecipientService extends ServiceImpl<RecipientMapper, Recipient> {

    @Autowired
    private RecipientGroupService groupService;

    public Page<Recipient> listRecipients(int page, int size, Long groupId, String email, Integer status) {
        Page<Recipient> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<Recipient> wrapper = new LambdaQueryWrapper<>();
        if (groupId != null) {
            wrapper.eq(Recipient::getGroupId, groupId);
        }
        if (StringUtils.hasText(email)) {
            wrapper.like(Recipient::getEmail, email);
        }
        if (status != null) {
            wrapper.eq(Recipient::getStatus, status);
        }
        wrapper.orderByDesc(Recipient::getCreatedAt);
        return page(pageParam, wrapper);
    }

    public Recipient getRecipientById(Long id) {
        return getById(id);
    }

    public boolean createRecipient(Recipient recipient) {
        recipient.setStatus(1);
        recipient.setUnsubscribed(0);
        boolean result = save(recipient);
        if (result) {
            updateGroupCount(recipient.getGroupId());
        }
        return result;
    }

    public boolean updateRecipient(Recipient recipient) {
        return updateById(recipient);
    }

    public boolean deleteRecipient(Long id) {
        Recipient recipient = getById(id);
        if (recipient == null) {
            return false;
        }
        boolean result = removeById(id);
        if (result) {
            updateGroupCount(recipient.getGroupId());
        }
        return result;
    }

    @Transactional(rollbackFor = Exception.class)
    public int importFromCsv(Long groupId, MultipartFile file) throws Exception {
        List<Recipient> recipients = new ArrayList<>();
        
        try (CSVReader reader = new CSVReader(new InputStreamReader(file.getInputStream()))) {
            String[] line;
            boolean isFirstLine = true;
            
            while ((line = reader.readNext()) != null) {
                if (isFirstLine) {
                    isFirstLine = false;
                    continue;
                }
                if (line.length < 1 || !StringUtils.hasText(line[0])) {
                    continue;
                }
                
                Recipient recipient = new Recipient();
                recipient.setGroupId(groupId);
                recipient.setEmail(line[0].trim());
                recipient.setName(line.length > 1 ? line[1].trim() : null);
                recipient.setPhone(line.length > 2 ? line[2].trim() : null);
                recipient.setStatus(1);
                recipient.setUnsubscribed(0);
                recipients.add(recipient);
            }
        }
        
        if (!recipients.isEmpty()) {
            saveBatch(recipients);
            updateGroupCount(groupId);
        }
        
        return recipients.size();
    }

    public List<Recipient> getActiveRecipientsByGroup(Long groupId) {
        LambdaQueryWrapper<Recipient> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Recipient::getGroupId, groupId);
        wrapper.eq(Recipient::getStatus, 1);
        wrapper.eq(Recipient::getUnsubscribed, 0);
        return list(wrapper);
    }

    private void updateGroupCount(Long groupId) {
        LambdaQueryWrapper<Recipient> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Recipient::getGroupId, groupId);
        int count = (int) count(wrapper);
        groupService.updateRecipientCount(groupId, count);
    }
}
