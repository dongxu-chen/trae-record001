package com.econtract.task;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.econtract.entity.Contract;
import com.econtract.entity.ContractSigner;
import com.econtract.mapper.ContractMapper;
import com.econtract.mapper.ContractSignerMapper;
import com.econtract.service.SignLogService;
import com.econtract.service.SmsService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.Comparator;
import java.util.List;

@Slf4j
@Component
public class SignTimeoutTask {

    @Value("${sign.timeout-hours:24}")
    private Integer timeoutHours;

    @Value("${sign.remind-interval-hours:6}")
    private Integer remindIntervalHours;

    @Value("${sign.max-remind-count:3}")
    private Integer maxRemindCount;

    @Value("${sign.auto-skip-timeout:true}")
    private Boolean autoSkipTimeout;

    @Resource
    private ContractSignerMapper signerMapper;

    @Resource
    private ContractMapper contractMapper;

    @Resource
    private SmsService smsService;

    @Resource
    private SignLogService signLogService;

    @Scheduled(fixedRate = 60000)
    @Transactional(rollbackFor = Exception.class)
    public void checkTimeoutAndRemind() {
        log.info("开始检查签署超时和催办...");

        QueryWrapper<ContractSigner> wrapper = new QueryWrapper<>();
        wrapper.in("sign_status", "SIGNING", "PENDING");
        List<ContractSigner> signers = signerMapper.selectList(wrapper);

        for (ContractSigner signer : signers) {
            try {
                processSigner(signer);
            } catch (Exception e) {
                log.error("处理签署人超时失败, signerId: {}", signer.getId(), e);
            }
        }

        log.info("签署超时和催办检查完成");
    }

    private void processSigner(ContractSigner signer) {
        if (!"SIGNING".equals(signer.getSignStatus())) {
            return;
        }

        LocalDateTime now = LocalDateTime.now();
        LocalDateTime deadline = signer.getSignDeadline();
        if (deadline == null) {
            deadline = signer.getCreateTime().plusHours(timeoutHours);
            signer.setSignDeadline(deadline);
            signerMapper.updateById(signer);
        }

        boolean isTimeout = now.isAfter(deadline);
        if (isTimeout && signer.getIsTimeout() == 0) {
            signer.setIsTimeout(1);
            signerMapper.updateById(signer);
            log.warn("签署人已超时, signerId: {}, contractId: {}", signer.getId(), signer.getContractId());

            sendSmsNotify(signer, "超时提醒",
                    "您的合同签署已超时，请尽快处理。如超时次数过多，系统将自动跳过您的签署流程。");

            signLogService.addLog(signer.getContractId(), signer.getSignerId(),
                    "TIMEOUT", "签署超时提醒");

            if (autoSkipTimeout) {
                skipTimeoutSigner(signer);
            }
            return;
        }

        if (!isTimeout) {
            long hoursLeft = ChronoUnit.HOURS.between(now, deadline);
            if (hoursLeft <= 6 && hoursLeft > 0) {
                checkAndRemind(signer, "即将超时提醒",
                        "您有一份合同即将在" + hoursLeft + "小时后截止签署，请尽快完成签署。");
            }
        }

        checkAndRemind(signer, "签署催办",
                "您有待签署的合同，请尽快登录平台完成签署。");
    }

    private void checkAndRemind(ContractSigner signer, String title, String content) {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime lastRemind = signer.getLastRemindTime();
        int remindCount = signer.getRemindCount() == null ? 0 : signer.getRemindCount();

        if (remindCount >= maxRemindCount) {
            return;
        }

        if (lastRemind == null) {
            if (remindCount == 0) {
                sendRemind(signer, title, content);
            }
        } else {
            long hoursSinceLastRemind = ChronoUnit.HOURS.between(lastRemind, now);
            if (hoursSinceLastRemind >= remindIntervalHours) {
                sendRemind(signer, title, content);
            }
        }
    }

    private void sendRemind(ContractSigner signer, String title, String content) {
        try {
            sendSmsNotify(signer, title, content);
        } catch (Exception e) {
            log.warn("发送催办短信失败: {}", e.getMessage());
        }

        signer.setRemindCount((signer.getRemindCount() == null ? 0 : signer.getRemindCount()) + 1);
        signer.setLastRemindTime(LocalDateTime.now());
        signerMapper.updateById(signer);

        signLogService.addLog(signer.getContractId(), signer.getSignerId(),
                "REMIND", title + ": " + content);

        log.info("已发送催办提醒, signerId: {}, 次数: {}", signer.getId(), signer.getRemindCount());
    }

    private void sendSmsNotify(ContractSigner signer, String title, String content) {
        try {
            smsService.sendSms(signer.getSignerPhone(), "SIGN_REMIND");
        } catch (Exception e) {
            log.warn("发送短信失败, phone: {}, error: {}", signer.getSignerPhone(), e.getMessage());
        }
    }

    private void skipTimeoutSigner(ContractSigner signer) {
        log.info("自动跳过超时签署人, signerId: {}, contractId: {}", signer.getId(), signer.getContractId());

        Contract contract = contractMapper.selectById(signer.getContractId());
        if (contract == null) {
            return;
        }

        QueryWrapper<ContractSigner> wrapper = new QueryWrapper<>();
        wrapper.eq("contract_id", signer.getContractId());
        wrapper.orderByAsc("sign_order");
        List<ContractSigner> allSigners = signerMapper.selectList(wrapper);

        int currentMaxCompletedOrder = allSigners.stream()
                .filter(s -> "COMPLETED".equals(s.getSignStatus()))
                .map(ContractSigner::getSignOrder)
                .max(Comparator.naturalOrder())
                .orElse(0);

        if (signer.getSignOrder() == currentMaxCompletedOrder + 1) {
            for (ContractSigner nextSigner : allSigners) {
                if (nextSigner.getSignOrder() > signer.getSignOrder()
                        && "PENDING".equals(nextSigner.getSignStatus())) {
                    nextSigner.setSignStatus("SIGNING");
                    nextSigner.setSignDeadline(LocalDateTime.now().plusHours(timeoutHours));
                    signerMapper.updateById(nextSigner);

                    try {
                        smsService.sendSms(nextSigner.getSignerPhone(), "SIGN_NOTIFY");
                    } catch (Exception e) {
                        log.warn("发送通知短信失败: {}", e.getMessage());
                    }

                    signLogService.addLog(contract.getId(), nextSigner.getSignerId(),
                            "NOTIFY", "上一方签署超时，自动流转到您签署");

                    log.info("已自动通知下一方, signerId: {}", nextSigner.getId());
                    break;
                }
            }

            boolean allDone = allSigners.stream()
                    .allMatch(s -> "COMPLETED".equals(s.getSignStatus())
                            || (s.getId().equals(signer.getId())));

            if (allDone) {
                contract.setStatus("COMPLETED");
                contractMapper.updateById(contract);
                log.info("合同已完成（跳过超时方）, contractId: {}", contract.getId());
            }
        }

        signer.setSignStatus("COMPLETED");
        signer.setSignNote("系统自动跳过（超时未签署）");
        signer.setSignTime(LocalDateTime.now());
        signerMapper.updateById(signer);

        signLogService.addLog(contract.getId(), signer.getSignerId(),
                "SKIP_TIMEOUT", "签署超时，系统自动跳过");
    }
}
