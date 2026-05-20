package com.payment.reconciliation.parser;

import com.alibaba.excel.EasyExcel;
import com.alibaba.excel.context.AnalysisContext;
import com.alibaba.excel.read.listener.ReadListener;
import com.payment.reconciliation.entity.ChannelTransaction;
import com.payment.reconciliation.mapper.ChannelTransactionMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.io.InputStream;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Component
public class StreamingExcelParser implements ReconciliationParser {

    @Autowired
    private ChannelTransactionMapper channelTransactionMapper;

    @Value("${reconciliation.batch-size:1000}")
    private int batchSize;

    private static final int BATCH_SIZE = 1000;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public List<ChannelTransaction> parse(InputStream inputStream, String channelCode) throws Exception {
        return parseWithCallback(inputStream, channelCode, null, null);
    }

    public void parseStreaming(InputStream inputStream, String channelCode,
                               Long reconciliationId, ParseCallback callback) throws Exception {
        AtomicInteger totalCount = new AtomicInteger(0);
        AtomicInteger successCount = new AtomicInteger(0);
        List<ChannelTransaction> batchList = new ArrayList<>(batchSize);

        EasyExcel.read(inputStream, new ReadListener<Map<Integer, String>>() {
            @Override
            public void invoke(Map<Integer, String> data, AnalysisContext context) {
                if (context.readRowHolder().getRowIndex() == 0) {
                    return;
                }

                try {
                    ChannelTransaction transaction = mapToTransaction(data, channelCode, reconciliationId);
                    if (transaction != null) {
                        batchList.add(transaction);
                        totalCount.incrementAndGet();

                        if (batchList.size() >= batchSize) {
                            flushBatch(batchList, successCount, callback);
                        }
                    }
                } catch (Exception e) {
                    log.error("解析Excel行失败, 行号: {}, 数据: {}", context.readRowHolder().getRowIndex(), data, e);
                    if (callback != null) {
                        callback.onError(context.readRowHolder().getRowIndex(), data, e);
                    }
                }
            }

            @Override
            public void doAfterAllAnalysed(AnalysisContext context) {
                if (!batchList.isEmpty()) {
                    flushBatch(batchList, successCount, callback);
                }
                log.info("Excel流式解析完成, 总条数: {}, 成功: {}", totalCount.get(), successCount.get());
                if (callback != null) {
                    callback.onComplete(totalCount.get(), successCount.get());
                }
            }
        }).sheet().doRead();
    }

    private void flushBatch(List<ChannelTransaction> batchList, AtomicInteger successCount, ParseCallback callback) {
        try {
            channelTransactionMapper.batchInsert(batchList);
            successCount.addAndGet(batchList.size());
            log.debug("批量入库成功, size: {}, 累计: {}", batchList.size(), successCount.get());

            if (callback != null) {
                callback.onBatchComplete(batchList.size(), successCount.get());
            }
        } catch (Exception e) {
            log.error("批量入库失败, size: {}", batchList.size(), e);
            throw new RuntimeException("批量入库失败", e);
        } finally {
            batchList.clear();
        }
    }

    private ChannelTransaction mapToTransaction(Map<Integer, String> data, String channelCode, Long reconciliationId) {
        if (data.size() < 7) {
            return null;
        }
        ChannelTransaction transaction = new ChannelTransaction();
        transaction.setReconciliationId(reconciliationId);
        transaction.setChannelCode(channelCode);
        transaction.setChannelTransNo(data.get(0));
        transaction.setMerchantNo(data.get(1));
        transaction.setOrderNo(data.get(2));
        transaction.setAmount(new BigDecimal(data.get(3)));
        transaction.setFee(new BigDecimal(data.get(4)));
        transaction.setStatus(Integer.parseInt(data.get(5)));
        transaction.setTransTime(LocalDateTime.now());
        transaction.setMatched(0);
        transaction.setCreateTime(LocalDateTime.now());
        return transaction;
    }

    private List<ChannelTransaction> parseWithCallback(InputStream inputStream, String channelCode,
                                                        Long reconciliationId, ParseCallback callback) {
        List<ChannelTransaction> resultList = new ArrayList<>();
        AtomicInteger totalCount = new AtomicInteger(0);

        EasyExcel.read(inputStream, new ReadListener<Map<Integer, String>>() {
            @Override
            public void invoke(Map<Integer, String> data, AnalysisContext context) {
                if (context.readRowHolder().getRowIndex() == 0) {
                    return;
                }
                try {
                    ChannelTransaction transaction = mapToTransaction(data, channelCode, reconciliationId);
                    if (transaction != null) {
                        resultList.add(transaction);
                        totalCount.incrementAndGet();
                    }
                } catch (Exception e) {
                    log.error("解析Excel行失败, 行号: {}, 数据: {}", context.readRowHolder().getRowIndex(), data, e);
                }
            }

            @Override
            public void doAfterAllAnalysed(AnalysisContext context) {
                log.info("Excel解析完成, 共解析 {} 条记录", totalCount.get());
            }
        }).sheet().doRead();

        return resultList;
    }

    @Override
    public boolean support(String fileType) {
        return "xlsx".equalsIgnoreCase(fileType) || "xls".equalsIgnoreCase(fileType);
    }

    public interface ParseCallback {
        void onBatchComplete(int batchSize, int totalSuccess);
        void onError(long rowIndex, Object rowData, Exception e);
        void onComplete(int totalCount, int successCount);
    }
}
