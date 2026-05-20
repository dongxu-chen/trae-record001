package com.pushplatform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.pushplatform.entity.AbTest;
import com.pushplatform.entity.PushRecord;
import com.pushplatform.mapper.AbTestMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Random;

@Service
public class AbTestService extends ServiceImpl<AbTestMapper, AbTest> {

    private static final Logger logger = LoggerFactory.getLogger(AbTestService.class);

    @Autowired
    private PushRecordService pushRecordService;

    private final Random random = new Random();

    public AbTest createTest(String testCode, String testName, String channel, 
                             Long templateAId, Long templateBId, 
                             Integer splitRatio, String remark) {
        AbTest test = new AbTest();
        test.setTestCode(testCode);
        test.setTestName(testName);
        test.setChannel(channel);
        test.setTemplateAId(templateAId);
        test.setTemplateBId(templateBId);
        test.setSplitRatio(splitRatio != null ? splitRatio : 50);
        test.setStatus(0);
        test.setRemark(remark);
        test.setCreateTime(LocalDateTime.now());
        test.setUpdateTime(LocalDateTime.now());
        save(test);
        logger.info("Created A/B test: {}", testCode);
        return test;
    }

    public boolean startTest(Long testId) {
        AbTest test = getById(testId);
        if (test == null) {
            return false;
        }
        test.setStatus(1);
        test.setStartTime(LocalDateTime.now());
        test.setUpdateTime(LocalDateTime.now());
        updateById(test);
        logger.info("Started A/B test: {}", test.getTestCode());
        return true;
    }

    public boolean endTest(Long testId) {
        AbTest test = getById(testId);
        if (test == null) {
            return false;
        }
        test.setStatus(2);
        test.setEndTime(LocalDateTime.now());
        test.setUpdateTime(LocalDateTime.now());
        updateById(test);
        logger.info("Ended A/B test: {}", test.getTestCode());
        return true;
    }

    public String assignGroup(Long testId) {
        AbTest test = getById(testId);
        if (test == null || test.getStatus() != 1) {
            return "A";
        }
        int randomValue = random.nextInt(100) + 1;
        return randomValue <= test.getSplitRatio() ? "A" : "B";
    }

    public Long getTemplateForUser(Long testId, String userId) {
        AbTest test = getById(testId);
        if (test == null || test.getStatus() != 1) {
            return test != null ? test.getTemplateAId() : null;
        }

        int hash = Math.abs(userId.hashCode()) % 100 + 1;
        String group = hash <= test.getSplitRatio() ? "A" : "B";

        return "A".equals(group) ? test.getTemplateAId() : test.getTemplateBId();
    }

    public void recordClick(Long recordId) {
        PushRecord record = pushRecordService.getById(recordId);
        if (record == null || record.getAbTestId() == null) {
            return;
        }

        AbTest test = getById(record.getAbTestId());
        if (test == null) {
            return;
        }

        if ("A".equals(record.getAbGroup())) {
            test.setAClicks(test.getAClicks() + 1);
        } else if ("B".equals(record.getAbGroup())) {
            test.setBClicks(test.getBClicks() + 1);
        }

        calculateClickRates(test);
        test.setUpdateTime(LocalDateTime.now());
        updateById(test);
        logger.info("Recorded click for A/B test: {}, group: {}", test.getTestCode(), record.getAbGroup());
    }

    @Scheduled(fixedDelay = 300000)
    public void updateTestStats() {
        LambdaQueryWrapper<AbTest> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(AbTest::getStatus, 1);
        List<AbTest> tests = list(wrapper);

        for (AbTest test : tests) {
            updateTestStats(test);
        }
    }

    private void updateTestStats(AbTest test) {
        LambdaQueryWrapper<PushRecord> wrapperA = new LambdaQueryWrapper<>();
        wrapperA.eq(PushRecord::getAbTestId, test.getId())
                .eq(PushRecord::getAbGroup, "A")
                .eq(PushRecord::getStatus, 1);
        long sentA = pushRecordService.count(wrapperA);

        LambdaQueryWrapper<PushRecord> wrapperB = new LambdaQueryWrapper<>();
        wrapperB.eq(PushRecord::getAbTestId, test.getId())
                .eq(PushRecord::getAbGroup, "B")
                .eq(PushRecord::getStatus, 1);
        long sentB = pushRecordService.count(wrapperB);

        test.setATargets(sentA);
        test.setBTargets(sentB);
        test.setTotalTargets(sentA + sentB);

        calculateClickRates(test);
        test.setUpdateTime(LocalDateTime.now());
        updateById(test);
    }

    private void calculateClickRates(AbTest test) {
        if (test.getATargets() != null && test.getATargets() > 0) {
            BigDecimal rate = BigDecimal.valueOf(test.getAClicks())
                    .multiply(BigDecimal.valueOf(100))
                    .divide(BigDecimal.valueOf(test.getATargets()), 2, RoundingMode.HALF_UP);
            test.setAClickRate(rate);
        } else {
            test.setAClickRate(BigDecimal.ZERO);
        }

        if (test.getBTargets() != null && test.getBTargets() > 0) {
            BigDecimal rate = BigDecimal.valueOf(test.getBClicks())
                    .multiply(BigDecimal.valueOf(100))
                    .divide(BigDecimal.valueOf(test.getBTargets()), 2, RoundingMode.HALF_UP);
            test.setBClickRate(rate);
        } else {
            test.setBClickRate(BigDecimal.ZERO);
        }
    }

    public String getWinningGroup(Long testId) {
        AbTest test = getById(testId);
        if (test == null) {
            return null;
        }

        if (test.getAClickRate() == null || test.getBClickRate() == null) {
            return null;
        }

        int comparison = test.getAClickRate().compareTo(test.getBClickRate());
        if (comparison > 0) {
            return "A";
        } else if (comparison < 0) {
            return "B";
        } else {
            return "DRAW";
        }
    }

    public List<AbTest> listActiveTests() {
        LambdaQueryWrapper<AbTest> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(AbTest::getStatus, 1);
        return list(wrapper);
    }
}
