package com.payment.reconciliation.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.payment.reconciliation.dto.DiscrepancyHandleDTO;
import com.payment.reconciliation.entity.Discrepancy;
import com.payment.reconciliation.mapper.DiscrepancyMapper;
import com.payment.reconciliation.service.DiscrepancyService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
public class DiscrepancyServiceImpl implements DiscrepancyService {

    @Autowired
    private DiscrepancyMapper discrepancyMapper;

    @Override
    public List<Discrepancy> listDiscrepancies(String channelCode, Integer type, Integer status) {
        LambdaQueryWrapper<Discrepancy> wrapper = new LambdaQueryWrapper<>();
        if (channelCode != null) {
            wrapper.eq(Discrepancy::getChannelCode, channelCode);
        }
        if (type != null) {
            wrapper.eq(Discrepancy::getType, type);
        }
        if (status != null) {
            wrapper.eq(Discrepancy::getStatus, status);
        }
        wrapper.orderByDesc(Discrepancy::getCreateTime);
        return discrepancyMapper.selectList(wrapper);
    }

    @Override
    public Discrepancy getDiscrepancyById(Long id) {
        return discrepancyMapper.selectById(id);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void handleDiscrepancy(DiscrepancyHandleDTO dto) {
        log.info("处理差错记录, discrepancyId: {}, status: {}", dto.getDiscrepancyId(), dto.getStatus());

        Discrepancy discrepancy = discrepancyMapper.selectById(dto.getDiscrepancyId());
        if (discrepancy == null) {
            throw new RuntimeException("差错记录不存在");
        }

        discrepancy.setStatus(dto.getStatus());
        discrepancy.setHandleRemark(dto.getHandleRemark());
        discrepancy.setHandleTime(LocalDateTime.now());
        discrepancy.setHandler(dto.getHandler());
        discrepancy.setUpdateTime(LocalDateTime.now());

        discrepancyMapper.updateById(discrepancy);

        log.info("差错记录处理完成, discrepancyId: {}", dto.getDiscrepancyId());
    }
}
