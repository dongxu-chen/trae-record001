package com.econtract.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.econtract.common.BusinessException;
import com.econtract.common.ResultCode;
import com.econtract.entity.ContractSigner;
import com.econtract.mapper.ContractSignerMapper;
import com.econtract.security.UserContext;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;

@Slf4j
@Service
public class SignRemindService {

    @Value("${sign.remind-interval-hours:6}")
    private Integer remindIntervalHours;

    @Value("${sign.max-remind-count:3}")
    private Integer maxRemindCount;

    @Resource
    private ContractSignerMapper signerMapper;

    @Resource
    private SmsService smsService;

    @Resource
    private SignLogService signLogService;

    @Transactional(rollbackFor = Exception.class)
    public void remindSigner(Long contractId) {
        Long currentUserId = UserContext.getCurrentUserId();

        QueryWrapper<ContractSigner> wrapper = new QueryWrapper<>();
        wrapper.eq("contract_id", contractId);
        wrapper.orderByAsc("sign_order");
        wrapper.last("limit 1");
        ContractSigner currentSigner = signerMapper.selectOne(wrapper);

        if (currentSigner == null) {
            throw new BusinessException(ResultCode.CONTRACT_NOT_FOUND);
        }

        if (!"SIGNING".equals(currentSigner.getSignStatus())) {
            throw new BusinessException("当前没有待签署的签署人");
        }

        if (currentSigner.getRemindCount() != null
                && currentSigner.getRemindCount() >= maxRemindCount) {
            throw new BusinessException("催办次数已达上限，请稍后再试");
        }

        if (currentSigner.getLastRemindTime() != null) {
            long hoursSinceLast = ChronoUnit.HOURS.between(
                    currentSigner.getLastRemindTime(), LocalDateTime.now());
            if (hoursSinceLast < remindIntervalHours) {
                throw new BusinessException("催办过于频繁，请" + (remindIntervalHours - hoursSinceLast)
                        + "小时后再试");
            }
        }

        try {
            smsService.sendSms(currentSigner.getSignerPhone(), "SIGN_REMIND");
        } catch (Exception e) {
            log.warn("发送催办短信失败: {}", e.getMessage());
        }

        currentSigner.setRemindCount((currentSigner.getRemindCount() == null
                ? 0 : currentSigner.getRemindCount()) + 1);
        currentSigner.setLastRemindTime(LocalDateTime.now());
        signerMapper.updateById(currentSigner);

        signLogService.addLog(contractId, currentUserId, "REMIND_MANUAL",
                "手动催办签署人: " + currentSigner.getSignerName());

        log.info("手动催办成功, contractId: {}, signerId: {}", contractId, currentSigner.getId());
    }

    public int getRemainRemindCount(Long contractId) {
        QueryWrapper<ContractSigner> wrapper = new QueryWrapper<>();
        wrapper.eq("contract_id", contractId);
        wrapper.eq("sign_status", "SIGNING");
        ContractSigner currentSigner = signerMapper.selectOne(wrapper);
        if (currentSigner == null) {
            return 0;
        }
        int used = currentSigner.getRemindCount() == null ? 0 : currentSigner.getRemindCount();
        return Math.max(0, maxRemindCount - used);
    }
}
