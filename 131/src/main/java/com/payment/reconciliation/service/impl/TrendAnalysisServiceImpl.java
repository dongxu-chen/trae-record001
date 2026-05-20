package com.payment.reconciliation.service.impl;

import cn.hutool.core.util.IdUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.payment.reconciliation.dto.TrendAnalysisDTO;
import com.payment.reconciliation.entity.Discrepancy;
import com.payment.reconciliation.entity.DiscrepancyTrend;
import com.payment.reconciliation.enums.DiscrepancyTypeEnum;
import com.payment.reconciliation.mapper.DiscrepancyMapper;
import com.payment.reconciliation.mapper.DiscrepancyTrendMapper;
import com.payment.reconciliation.service.TrendAnalysisService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class TrendAnalysisServiceImpl implements TrendAnalysisService {

    @Autowired
    private DiscrepancyTrendMapper discrepancyTrendMapper;

    @Autowired
    private DiscrepancyMapper discrepancyMapper;

    @Override
    @Scheduled(cron = "0 0 2 * * ?")
    @Transactional(rollbackFor = Exception.class)
    public void generateDailyTrendStatistics() {
        log.info("开始生成每日对账差异趋势统计");

        LocalDate statisticsDate = LocalDate.now().minusDays(1);

        LambdaQueryWrapper<Discrepancy> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Discrepancy::getReconciliationDate, statisticsDate);
        List<Discrepancy> discrepancies = discrepancyMapper.selectList(wrapper);

        Map<String, List<Discrepancy>> channelMap = new HashMap<>();
        for (Discrepancy d : discrepancies) {
            channelMap.computeIfAbsent(d.getChannelCode(), k -> new ArrayList<>()).add(d);
        }

        for (Map.Entry<String, List<Discrepancy>> entry : channelMap.entrySet()) {
            saveChannelTrend(statisticsDate, entry.getKey(), entry.getValue());
        }

        log.info("每日对账差异趋势统计生成完成，共处理{}个渠道", channelMap.size());
    }

    private void saveChannelTrend(LocalDate statisticsDate, String channelCode, List<Discrepancy> discrepancies) {
        log.debug("生成渠道趋势统计，channelCode: {}, date: {}", channelCode, statisticsDate);

        DiscrepancyTrend existing = discrepancyTrendMapper.selectByDateAndChannel(statisticsDate, channelCode);
        if (existing != null) {
            log.debug("该渠道当日统计已存在，跳过，channelCode: {}", channelCode);
            return;
        }

        int totalCount = discrepancies.size();
        BigDecimal totalAmount = discrepancies.stream()
                .map(Discrepancy::getDifferenceAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        long longCount = discrepancies.stream()
                .filter(d -> DiscrepancyTypeEnum.LONG.getCode().equals(d.getType()))
                .count();
        BigDecimal longAmount = discrepancies.stream()
                .filter(d -> DiscrepancyTypeEnum.LONG.getCode().equals(d.getType()))
                .map(Discrepancy::getDifferenceAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        long shortCount = discrepancies.stream()
                .filter(d -> DiscrepancyTypeEnum.SHORT.getCode().equals(d.getType()))
                .count();
        BigDecimal shortAmount = discrepancies.stream()
                .filter(d -> DiscrepancyTypeEnum.SHORT.getCode().equals(d.getType()))
                .map(Discrepancy::getDifferenceAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        long amountMismatchCount = discrepancies.stream()
                .filter(d -> DiscrepancyTypeEnum.AMOUNT_MISMATCH.getCode().equals(d.getType()))
                .count();
        BigDecimal amountMismatchAmount = discrepancies.stream()
                .filter(d -> DiscrepancyTypeEnum.AMOUNT_MISMATCH.getCode().equals(d.getType()))
                .map(Discrepancy::getDifferenceAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        long resolvedCount = discrepancies.stream()
                .filter(d -> d.getStatus() == 2)
                .count();
        BigDecimal resolvedAmount = discrepancies.stream()
                .filter(d -> d.getStatus() == 2)
                .map(Discrepancy::getDifferenceAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        DiscrepancyTrend trend = new DiscrepancyTrend();
        trend.setTrendNo(IdUtil.simpleUUID());
        trend.setChannelCode(channelCode);
        trend.setStatisticsDate(statisticsDate);
        trend.setTotalCount(totalCount);
        trend.setTotalAmount(totalAmount);
        trend.setLongCount((int) longCount);
        trend.setLongAmount(longAmount);
        trend.setShortCount((int) shortCount);
        trend.setShortAmount(shortAmount);
        trend.setAmountMismatchCount((int) amountMismatchCount);
        trend.setAmountMismatchAmount(amountMismatchAmount);
        trend.setResolvedCount((int) resolvedCount);
        trend.setResolvedAmount(resolvedAmount);
        trend.setCreateTime(LocalDateTime.now());

        discrepancyTrendMapper.insert(trend);
        log.debug("渠道趋势统计保存成功，channelCode: {}, totalCount: {}", channelCode, totalCount);
    }

    @Override
    public List<DiscrepancyTrend> getTrendData(TrendAnalysisDTO dto) {
        return discrepancyTrendMapper.selectByDateRange(
                dto.getChannelCode(),
                dto.getStartDate(),
                dto.getEndDate()
        );
    }

    @Override
    public Map<String, Object> getTrendChartData(TrendAnalysisDTO dto) {
        log.info("获取趋势图表数据，channelCode: {}, startDate: {}, endDate: {}",
                dto.getChannelCode(), dto.getStartDate(), dto.getEndDate());

        List<DiscrepancyTrend> trends = getTrendData(dto);

        List<String> dates = new ArrayList<>();
        List<Integer> totalCounts = new ArrayList<>();
        List<BigDecimal> totalAmounts = new ArrayList<>();
        List<Integer> longCounts = new ArrayList<>();
        List<Integer> shortCounts = new ArrayList<>();
        List<Integer> amountMismatchCounts = new ArrayList<>();

        for (DiscrepancyTrend trend : trends) {
            dates.add(trend.getStatisticsDate().toString());
            totalCounts.add(trend.getTotalCount());
            totalAmounts.add(trend.getTotalAmount());
            longCounts.add(trend.getLongCount());
            shortCounts.add(trend.getShortCount());
            amountMismatchCounts.add(trend.getAmountMismatchCount());
        }

        Map<String, Object> result = new HashMap<>();
        result.put("dates", dates);
        result.put("totalCounts", totalCounts);
        result.put("totalAmounts", totalAmounts);
        result.put("longCounts", longCounts);
        result.put("shortCounts", shortCounts);
        result.put("amountMismatchCounts", amountMismatchCounts);

        return result;
    }

    @Override
    public Map<String, Object> getDiscrepancyTypeDistribution(TrendAnalysisDTO dto) {
        log.info("获取差异类型分布数据，channelCode: {}, startDate: {}, endDate: {}",
                dto.getChannelCode(), dto.getStartDate(), dto.getEndDate());

        List<DiscrepancyTrend> trends = getTrendData(dto);

        int totalLongCount = 0;
        BigDecimal totalLongAmount = BigDecimal.ZERO;
        int totalShortCount = 0;
        BigDecimal totalShortAmount = BigDecimal.ZERO;
        int totalMismatchCount = 0;
        BigDecimal totalMismatchAmount = BigDecimal.ZERO;

        for (DiscrepancyTrend trend : trends) {
            totalLongCount += trend.getLongCount();
            totalLongAmount = totalLongAmount.add(trend.getLongAmount());
            totalShortCount += trend.getShortCount();
            totalShortAmount = totalShortAmount.add(trend.getShortAmount());
            totalMismatchCount += trend.getAmountMismatchCount();
            totalMismatchAmount = totalMismatchAmount.add(trend.getAmountMismatchAmount());
        }

        List<Map<String, Object>> typeDistribution = new ArrayList<>();

        Map<String, Object> longType = new HashMap<>();
        longType.put("type", "长款");
        longType.put("count", totalLongCount);
        longType.put("amount", totalLongAmount);
        typeDistribution.add(longType);

        Map<String, Object> shortType = new HashMap<>();
        shortType.put("type", "短款");
        shortType.put("count", totalShortCount);
        shortType.put("amount", totalShortAmount);
        typeDistribution.add(shortType);

        Map<String, Object> mismatchType = new HashMap<>();
        mismatchType.put("type", "金额不符");
        mismatchType.put("count", totalMismatchCount);
        mismatchType.put("amount", totalMismatchAmount);
        typeDistribution.add(mismatchType);

        int totalCount = totalLongCount + totalShortCount + totalMismatchCount;
        BigDecimal totalAmount = totalLongAmount.add(totalShortAmount).add(totalMismatchAmount);

        Map<String, Object> result = new HashMap<>();
        result.put("distribution", typeDistribution);
        result.put("totalCount", totalCount);
        result.put("totalAmount", totalAmount);

        return result;
    }
}
