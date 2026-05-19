package com.payment.reconciliation.service.impl;

import com.alibaba.excel.EasyExcel;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.payment.reconciliation.dto.ReportQueryDTO;
import com.payment.reconciliation.entity.Discrepancy;
import com.payment.reconciliation.entity.ReconciliationResult;
import com.payment.reconciliation.mapper.DiscrepancyMapper;
import com.payment.reconciliation.mapper.ReconciliationResultMapper;
import com.payment.reconciliation.service.ReportService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class ReportServiceImpl implements ReportService {

    @Autowired
    private ReconciliationResultMapper reconciliationResultMapper;

    @Autowired
    private DiscrepancyMapper discrepancyMapper;

    @Override
    public List<ReconciliationResult> queryReconciliationResults(ReportQueryDTO dto) {
        LambdaQueryWrapper<ReconciliationResult> wrapper = new LambdaQueryWrapper<>();
        if (dto.getChannelCode() != null) {
            wrapper.eq(ReconciliationResult::getChannelCode, dto.getChannelCode());
        }
        if (dto.getStartDate() != null) {
            wrapper.ge(ReconciliationResult::getReconciliationDate, dto.getStartDate());
        }
        if (dto.getEndDate() != null) {
            wrapper.le(ReconciliationResult::getReconciliationDate, dto.getEndDate());
        }
        if (dto.getStatus() != null) {
            wrapper.eq(ReconciliationResult::getStatus, dto.getStatus());
        }
        wrapper.orderByDesc(ReconciliationResult::getReconciliationDate);
        return reconciliationResultMapper.selectList(wrapper);
    }

    @Override
    public ReconciliationResult getReconciliationResultById(Long id) {
        return reconciliationResultMapper.selectById(id);
    }

    @Override
    public void exportReconciliationReport(Long resultId, HttpServletResponse response) throws IOException {
        log.info("导出对账报表, resultId: {}", resultId);

        ReconciliationResult result = reconciliationResultMapper.selectById(resultId);
        if (result == null) {
            throw new RuntimeException("对账结果不存在");
        }

        LambdaQueryWrapper<Discrepancy> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Discrepancy::getResultId, resultId);
        List<Discrepancy> discrepancies = discrepancyMapper.selectList(wrapper);

        List<Map<String, Object>> summaryData = new ArrayList<>();
        Map<String, Object> summary = new HashMap<>();
        summary.put("item", "系统交易总数");
        summary.put("count", result.getSysTotalCount());
        summary.put("amount", result.getSysTotalAmount());
        summaryData.add(summary);

        summary = new HashMap<>();
        summary.put("item", "渠道交易总数");
        summary.put("count", result.getChannelTotalCount());
        summary.put("amount", result.getChannelTotalAmount());
        summaryData.add(summary);

        summary = new HashMap<>();
        summary.put("item", "匹配成功");
        summary.put("count", result.getMatchedCount());
        summary.put("amount", result.getMatchedAmount());
        summaryData.add(summary);

        summary = new HashMap<>();
        summary.put("item", "长款");
        summary.put("count", result.getLongCount());
        summary.put("amount", result.getLongAmount());
        summaryData.add(summary);

        summary = new HashMap<>();
        summary.put("item", "短款");
        summary.put("count", result.getShortCount());
        summary.put("amount", result.getShortAmount());
        summaryData.add(summary);

        String fileName = "对账报表_" + result.getChannelCode() + "_" + result.getReconciliationDate();
        response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        response.setCharacterEncoding("utf-8");
        response.setHeader("Content-disposition", "attachment;filename*=utf-8''" + URLEncoder.encode(fileName, "UTF-8") + ".xlsx");

        EasyExcel.write(response.getOutputStream())
                .sheet("汇总信息")
                .doWrite(summaryData);

        log.info("对账报表导出完成, resultId: {}", resultId);
    }
}
