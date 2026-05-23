package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.config.RabbitMQConfig;
import com.emailmarketing.dto.EmailSendMessage;
import com.emailmarketing.entity.*;
import com.emailmarketing.mapper.AbTestMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
public class AbTestService extends ServiceImpl<AbTestMapper, AbTest> {

    @Autowired
    private AbTestVariantService variantService;

    @Autowired
    private RecipientService recipientService;

    @Autowired
    private EmailSendLogService sendLogService;

    @Autowired
    private EmailTrackingService trackingService;

    @Autowired
    private RabbitTemplate rabbitTemplate;

    public Page<AbTest> listTests(int page, int size, String name, Integer status) {
        Page<AbTest> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<AbTest> wrapper = new LambdaQueryWrapper<>();
        if (name != null && !name.isEmpty()) {
            wrapper.like(AbTest::getName, name);
        }
        if (status != null) {
            wrapper.eq(AbTest::getStatus, status);
        }
        wrapper.orderByDesc(AbTest::getCreatedAt);
        return page(pageParam, wrapper);
    }

    @Transactional(rollbackFor = Exception.class)
    public boolean createTest(AbTest test, List<AbTestVariant> variants) {
        test.setStatus(0);
        test.setWinnerId(null);
        boolean saved = save(test);
        if (!saved) {
            return false;
        }

        for (AbTestVariant variant : variants) {
            variant.setTestId(test.getId());
            variant.setIsWinner(0);
            variant.setSentCount(0);
            variant.setOpenCount(0);
            variant.setClickCount(0);
            variant.setConversionCount(0);
            variantService.save(variant);
        }
        return true;
    }

    @Transactional(rollbackFor = Exception.class)
    public boolean startTest(Long testId) {
        AbTest test = getById(testId);
        if (test == null || test.getStatus() != 0) {
            return false;
        }

        List<AbTestVariant> variants = variantService.getVariantsByTestId(testId);
        if (variants.size() < 2) {
            throw new RuntimeException("A/B测试至少需要2个变体");
        }

        List<Recipient> recipients = recipientService.getActiveRecipientsByGroup(test.getGroupId());
        if (recipients.isEmpty()) {
            throw new RuntimeException("收件人分组为空");
        }

        int sampleSize = test.getSampleSize() > 0 ? test.getSampleSize() : Math.min(100, recipients.size() / variants.size());
        Collections.shuffle(recipients);

        int variantIndex = 0;
        int sentCount = 0;

        for (int i = 0; i < Math.min(sampleSize * variants.size(), recipients.size()); i++) {
            Recipient recipient = recipients.get(i);
            AbTestVariant variant = variants.get(variantIndex % variants.size());

            EmailSendLog sendLog = new EmailSendLog();
            sendLog.setTaskId(testId);
            sendLog.setRecipientId(recipient.getId());
            sendLog.setEmail(recipient.getEmail());
            sendLog.setSendStatus(0);
            sendLog.setOpened(0);
            sendLog.setClicked(0);
            sendLog.setUnsubscribed(0);
            sendLog.setCreatedAt(LocalDateTime.now());
            sendLogService.save(sendLog);

            String subject = variant.getSubject();
            String content = trackingService.injectTracking(variant.getContent(), testId, sendLog.getId(), recipient.getEmail());

            EmailSendMessage message = new EmailSendMessage(
                    testId,
                    sendLog.getId(),
                    recipient.getId(),
                    recipient.getEmail(),
                    subject,
                    content
            );

            rabbitTemplate.convertAndSend(RabbitMQConfig.EMAIL_EXCHANGE, RabbitMQConfig.EMAIL_ROUTING_KEY, message);

            variantIndex++;
            sentCount++;
        }

        test.setStatus(1);
        test.setStartTime(LocalDateTime.now());
        test.setTotalSize(sentCount);
        updateById(test);

        for (AbTestVariant variant : variants) {
            variant.setSentCount(sentCount / variants.size());
            variantService.updateById(variant);
        }

        return true;
    }

    public void recordOpen(Long testId, Long logId) {
        updateVariantStats(testId, logId, "open");
    }

    public void recordClick(Long testId, Long logId) {
        updateVariantStats(testId, logId, "click");
    }

    private void updateVariantStats(Long testId, Long logId, String type) {
        EmailSendLog sendLog = sendLogService.getById(logId);
        if (sendLog == null) return;

        List<AbTestVariant> variants = variantService.getVariantsByTestId(testId);
        if (variants.isEmpty()) return;

        int recipientIndex = getRecipientIndex(sendLog.getRecipientId(), testId);
        AbTestVariant variant = variants.get(recipientIndex % variants.size());

        if ("open".equals(type) && sendLog.getOpened() == 1) {
            LambdaUpdateWrapper<AbTestVariant> wrapper = new LambdaUpdateWrapper<>();
            wrapper.eq(AbTestVariant::getId, variant.getId());
            wrapper.setSql("open_count = open_count + 1");
            variantService.update(wrapper);
        }

        if ("click".equals(type) && sendLog.getClicked() == 1) {
            LambdaUpdateWrapper<AbTestVariant> wrapper = new LambdaUpdateWrapper<>();
            wrapper.eq(AbTestVariant::getId, variant.getId());
            wrapper.setSql("click_count = click_count + 1");
            variantService.update(wrapper);
        }

        updateVariantRates(variant.getId());
    }

    private void updateVariantRates(Long variantId) {
        AbTestVariant variant = variantService.getById(variantId);
        if (variant == null || variant.getSentCount() == 0) return;

        variant.setOpenRate(calculateRate(variant.getOpenCount(), variant.getSentCount()));
        variant.setClickRate(calculateRate(variant.getClickCount(), variant.getSentCount()));
        variant.setConversionRate(calculateRate(variant.getConversionCount(), variant.getSentCount()));
        variantService.updateById(variant);
    }

    private BigDecimal calculateRate(int count, int total) {
        if (total == 0) return BigDecimal.ZERO;
        return BigDecimal.valueOf(count)
                .multiply(BigDecimal.valueOf(100))
                .divide(BigDecimal.valueOf(total), 2, RoundingMode.HALF_UP);
    }

    private int getRecipientIndex(Long recipientId, Long testId) {
        return Math.abs((recipientId + ":" + testId).hashCode()) % 1000;
    }

    @Scheduled(fixedDelay = 300000)
    public void checkTestResults() {
        LambdaQueryWrapper<AbTest> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(AbTest::getStatus, 1);
        List<AbTest> tests = list(wrapper);

        for (AbTest test : tests) {
            if (shouldDetermineWinner(test)) {
                determineWinner(test.getId());
            }
        }
    }

    private boolean shouldDetermineWinner(AbTest test) {
        if (test.getStartTime() == null) return false;
        return LocalDateTime.now().isAfter(test.getStartTime().plusHours(4));
    }

    @Transactional(rollbackFor = Exception.class)
    public AbTestVariant determineWinner(Long testId) {
        AbTest test = getById(testId);
        if (test == null || test.getStatus() != 1) return null;

        List<AbTestVariant> variants = variantService.getVariantsByTestId(testId);
        if (variants.isEmpty()) return null;

        AbTestVariant winner = null;
        BigDecimal bestMetric = BigDecimal.ZERO;

        for (AbTestVariant variant : variants) {
            updateVariantRates(variant.getId());
            variant = variantService.getById(variant.getId());

            BigDecimal metric = switch (test.getMetricType()) {
                case 2 -> variant.getClickRate();
                case 3 -> variant.getConversionRate();
                default -> variant.getOpenRate();
            };

            if (metric.compareTo(bestMetric) > 0) {
                bestMetric = metric;
                winner = variant;
            }
        }

        if (winner != null) {
            winner.setIsWinner(1);
            variantService.updateById(winner);

            test.setWinnerId(winner.getId());
            test.setStatus(2);
            test.setEndTime(LocalDateTime.now());
            updateById(test);
        }

        return winner;
    }

    @Transactional(rollbackFor = Exception.class)
    public boolean launchWinner(Long testId) {
        AbTest test = getById(testId);
        if (test == null || test.getStatus() != 2 || test.getWinnerId() == null) {
            return false;
        }

        AbTestVariant winner = variantService.getById(test.getWinnerId());
        if (winner == null) return false;

        List<Recipient> recipients = recipientService.getActiveRecipientsByGroup(test.getGroupId());
        int sampleSize = test.getSampleSize() > 0 ? test.getSampleSize() * 2 : 200;

        int sentCount = 0;
        for (int i = sampleSize; i < recipients.size(); i++) {
            Recipient recipient = recipients.get(i);

            EmailSendLog sendLog = new EmailSendLog();
            sendLog.setTaskId(testId);
            sendLog.setRecipientId(recipient.getId());
            sendLog.setEmail(recipient.getEmail());
            sendLog.setSendStatus(0);
            sendLog.setOpened(0);
            sendLog.setClicked(0);
            sendLog.setUnsubscribed(0);
            sendLog.setCreatedAt(LocalDateTime.now());
            sendLogService.save(sendLog);

            String content = trackingService.injectTracking(winner.getContent(), testId, sendLog.getId(), recipient.getEmail());

            EmailSendMessage message = new EmailSendMessage(
                    testId,
                    sendLog.getId(),
                    recipient.getId(),
                    recipient.getEmail(),
                    winner.getSubject(),
                    content
            );

            rabbitTemplate.convertAndSend(RabbitMQConfig.EMAIL_EXCHANGE, RabbitMQConfig.EMAIL_ROUTING_KEY, message);
            sentCount++;
        }

        test.setTotalSize(test.getTotalSize() + sentCount);
        updateById(test);

        return true;
    }

    public Map<String, Object> getTestResults(Long testId) {
        Map<String, Object> result = new HashMap<>();
        AbTest test = getById(testId);
        if (test == null) return result;

        result.put("test", test);
        List<AbTestVariant> variants = variantService.getVariantsByTestId(testId);
        for (AbTestVariant variant : variants) {
            updateVariantRates(variant.getId());
        }
        variants = variantService.getVariantsByTestId(testId);
        result.put("variants", variants);

        if (test.getWinnerId() != null) {
            AbTestVariant winner = variants.stream()
                    .filter(v -> v.getId().equals(test.getWinnerId()))
                    .findFirst()
                    .orElse(null);
            result.put("winner", winner);
        }

        return result;
    }
}
