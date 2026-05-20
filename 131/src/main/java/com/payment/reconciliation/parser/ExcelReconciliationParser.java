package com.payment.reconciliation.parser;

import cn.hutool.core.date.DateUtil;
import com.alibaba.excel.EasyExcel;
import com.alibaba.excel.context.AnalysisContext;
import com.alibaba.excel.read.listener.ReadListener;
import com.payment.reconciliation.entity.ChannelTransaction;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class ExcelReconciliationParser implements ReconciliationParser {

    @Override
    public List<ChannelTransaction> parse(InputStream inputStream, String channelCode) throws Exception {
        List<ChannelTransaction> resultList = new ArrayList<>();

        EasyExcel.read(inputStream, new ReadListener<Map<Integer, String>>() {
            @Override
            public void invoke(Map<Integer, String> data, AnalysisContext context) {
                if (context.readRowHolder().getRowIndex() == 0) {
                    return;
                }
                try {
                    ChannelTransaction transaction = mapToTransaction(data, channelCode);
                    if (transaction != null) {
                        resultList.add(transaction);
                    }
                } catch (Exception e) {
                    log.error("解析Excel行失败, 行号: {}, 数据: {}", context.readRowHolder().getRowIndex(), data, e);
                }
            }

            @Override
            public void doAfterAllAnalysed(AnalysisContext context) {
                log.info("Excel解析完成, 共解析 {} 条记录", resultList.size());
            }
        }).sheet().doRead();

        return resultList;
    }

    private ChannelTransaction mapToTransaction(Map<Integer, String> data, String channelCode) {
        ChannelTransaction transaction = new ChannelTransaction();
        transaction.setChannelCode(channelCode);
        transaction.setChannelTransNo(data.get(0));
        transaction.setMerchantNo(data.get(1));
        transaction.setOrderNo(data.get(2));
        transaction.setAmount(new BigDecimal(data.get(3)));
        transaction.setFee(new BigDecimal(data.get(4)));
        transaction.setStatus(Integer.parseInt(data.get(5)));
        transaction.setTransTime(LocalDateTime.ofInstant(
                DateUtil.parse(data.get(6)).toInstant(),
                ZoneId.systemDefault()
        ));
        transaction.setMatched(0);
        return transaction;
    }

    @Override
    public boolean support(String fileType) {
        return "xlsx".equalsIgnoreCase(fileType) || "xls".equalsIgnoreCase(fileType);
    }
}
