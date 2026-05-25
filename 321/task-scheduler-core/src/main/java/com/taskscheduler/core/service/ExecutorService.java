package com.taskscheduler.core.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taskscheduler.common.dto.PageResult;
import com.taskscheduler.common.entity.ExecutorInfo;
import com.taskscheduler.common.enums.ExecutorStatusEnum;
import com.taskscheduler.core.mapper.ExecutorInfoMapper;
import com.taskscheduler.core.registry.ExecutorRegistry;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class ExecutorService {

    @Autowired
    private ExecutorInfoMapper executorInfoMapper;

    @Autowired
    private ExecutorRegistry executorRegistry;

    public PageResult<ExecutorInfo> queryExecutors(Integer pageNum, Integer pageSize, String appName, Integer status) {
        Page<ExecutorInfo> page = new Page<>(pageNum, pageSize);
        QueryWrapper<ExecutorInfo> wrapper = new QueryWrapper<>();
        if (appName != null && !appName.isEmpty()) {
            wrapper.eq("app_name", appName);
        }
        if (status != null) {
            wrapper.eq("status", status);
        }
        wrapper.orderByDesc("create_time");
        Page<ExecutorInfo> result = executorInfoMapper.selectPage(page, wrapper);
        return new PageResult<>(result.getTotal(), pageNum, pageSize, result.getRecords());
    }

    public ExecutorInfo getExecutorById(Long id) {
        return executorInfoMapper.selectById(id);
    }

    public List<ExecutorInfo> getAvailableExecutors() {
        return executorRegistry.getAvailableExecutors();
    }

    public List<ExecutorInfo> getAllExecutors() {
        return executorRegistry.getAllExecutors();
    }

    public void addExecutor(ExecutorInfo executorInfo) {
        executorInfo.setStatus(ExecutorStatusEnum.OFFLINE.getCode());
        executorInfo.setCreateTime(LocalDateTime.now());
        executorInfo.setUpdateTime(LocalDateTime.now());
        executorInfoMapper.insert(executorInfo);
    }

    public void updateExecutor(ExecutorInfo executorInfo) {
        executorInfo.setUpdateTime(LocalDateTime.now());
        executorInfoMapper.updateById(executorInfo);
    }

    public void deleteExecutor(Long id) {
        executorInfoMapper.deleteById(id);
    }

    public void refreshExecutorStatus() {
        executorRegistry.refreshExecutorStatus();
    }

    public int getOnlineExecutorCount() {
        return getAvailableExecutors().size();
    }

    public int getTotalExecutorCount() {
        return Math.toIntExact(executorInfoMapper.selectCount(null));
    }
}
