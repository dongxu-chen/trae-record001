package com.pushplatform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.pushplatform.entity.PushRecord;
import com.pushplatform.mapper.PushRecordMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class PushRecordService extends ServiceImpl<PushRecordMapper, PushRecord> {

    public List<PushRecord> listByTaskId(Long taskId) {
        return list(new LambdaQueryWrapper<PushRecord>().eq(PushRecord::getTaskId, taskId));
    }

    public List<PushRecord> listByTaskNo(String taskNo) {
        return list(new LambdaQueryWrapper<PushRecord>().eq(PushRecord::getTaskNo, taskNo));
    }

    public boolean updateStatus(Long id, Integer status, String errorMsg, String messageId) {
        PushRecord record = new PushRecord();
        record.setId(id);
        record.setStatus(status);
        record.setErrorMsg(errorMsg);
        record.setMessageId(messageId);
        record.setUpdateTime(LocalDateTime.now());
        return updateById(record);
    }

    public boolean updateCallback(Long id, String callbackResult) {
        PushRecord record = new PushRecord();
        record.setId(id);
        record.setCallbackTime(LocalDateTime.now());
        record.setCallbackResult(callbackResult);
        record.setUpdateTime(LocalDateTime.now());
        return updateById(record);
    }

    public List<PushRecord> listPendingRecords(String channel, int limit) {
        LambdaQueryWrapper<PushRecord> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(PushRecord::getStatus, 0);
        if (channel != null) {
            wrapper.eq(PushRecord::getChannel, channel);
        }
        wrapper.orderByAsc(PushRecord::getCreateTime);
        wrapper.last("LIMIT " + limit);
        return list(wrapper);
    }
}
