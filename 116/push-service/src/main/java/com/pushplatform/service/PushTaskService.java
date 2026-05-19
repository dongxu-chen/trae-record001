package com.pushplatform.service;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.pushplatform.common.enums.PushStatusEnum;
import com.pushplatform.dto.PushTaskDTO;
import com.pushplatform.entity.PushRecord;
import com.pushplatform.entity.PushTask;
import com.pushplatform.mapper.PushTaskMapper;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Service
public class PushTaskService extends ServiceImpl<PushTaskMapper, PushTask> {

    @Autowired
    private PushRecordService pushRecordService;

    public List<PushTask> list(String channel, Integer status) {
        LambdaQueryWrapper<PushTask> wrapper = new LambdaQueryWrapper<>();
        if (channel != null) {
            wrapper.eq(PushTask::getChannel, channel);
        }
        if (status != null) {
            wrapper.eq(PushTask::getStatus, status);
        }
        wrapper.orderByDesc(PushTask::getCreateTime);
        return list(wrapper);
    }

    public PushTask getByTaskNo(String taskNo) {
        return getOne(new LambdaQueryWrapper<PushTask>().eq(PushTask::getTaskNo, taskNo));
    }

    @Transactional(rollbackFor = Exception.class)
    public String create(PushTaskDTO dto) {
        String taskNo = "TASK" + System.currentTimeMillis() + UUID.randomUUID().toString().substring(0, 8);
        
        PushTask task = new PushTask();
        BeanUtils.copyProperties(dto, task);
        task.setTaskNo(taskNo);
        task.setTargets(dto.getTargets() != null ? JSON.toJSONString(dto.getTargets()) : null);
        task.setStatus(PushStatusEnum.PENDING.getCode());
        task.setTotalCount(dto.getTargets() != null ? dto.getTargets().size() : 0);
        task.setSuccessCount(0);
        task.setFailCount(0);
        task.setCreateTime(LocalDateTime.now());
        task.setUpdateTime(LocalDateTime.now());
        save(task);

        if (dto.getTargets() != null && !dto.getTargets().isEmpty()) {
            for (String target : dto.getTargets()) {
                PushRecord record = new PushRecord();
                record.setTaskId(task.getId());
                record.setTaskNo(taskNo);
                record.setChannel(dto.getChannel());
                record.setTarget(target);
                record.setTitle(dto.getTitle());
                record.setContent(dto.getContent());
                record.setStatus(PushStatusEnum.PENDING.getCode());
                record.setCreateTime(LocalDateTime.now());
                record.setUpdateTime(LocalDateTime.now());
                pushRecordService.save(record);
            }
        }

        return taskNo;
    }

    public boolean updateStatus(Long id, Integer status) {
        PushTask task = new PushTask();
        task.setId(id);
        task.setStatus(status);
        task.setUpdateTime(LocalDateTime.now());
        return updateById(task);
    }
}
