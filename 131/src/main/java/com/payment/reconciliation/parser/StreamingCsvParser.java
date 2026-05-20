package com.payment.reconciliation.parser;

import cn.hutool.core.util.StrUtil;
import com.payment.reconciliation.entity.ChannelTransaction;
import com.payment.reconciliation.mapper.ChannelTransactionMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Component
public class StreamingCsvParser implements ReconciliationParser {

    @Autowired
    private ChannelTransactionMapper channelTransactionMapper;

    @Value("${reconciliation.batch-size:1000}")
    private int batchSize;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public List<ChannelTransaction> parse(InputStream inputStream, String channelCode) throws Exception {
        List<ChannelTransaction> resultList = new ArrayList<>();

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream, StandardCharsets.UTF_8))) {
            String line;
            int lineNum = 0;
            while ((line = reader.readLine()) != null) {
                lineNum++;
                if (lineNum == 1) {
                    continue;
                }
                if (StrUtil.isBlank(line)) {
                    continue;
                }
                try {
                    String[] parts = line.split(",");
                    ChannelTransaction transaction = parseLine(parts, channelCode, null);
                    if (transaction != null) {
                        resultList.add(transaction);
                    }
                } catch (Exception e) {
                    log.error("解析CSV行失败, 行号: {}, 数据: {}", lineNum, line, e);
                }
            }
        }

        log.info("CSV解析完成, 共解析 {} 条记录", resultList.size());
        return resultList;
    }

    public void parseStreaming(InputStream inputStream, String channelCode,
                               Long reconciliationId, StreamingExcelParser.ParseCallback callback) throws Exception {
        AtomicInteger totalCount = new AtomicInteger(0);
        AtomicInteger successCount = new AtomicInteger(0);
        List<ChannelTransaction> batchList = new ArrayList<>(batchSize);

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream, StandardCharsets.UTF_8))) {
            String line;
            int lineNum = 0;
            while ((line = reader.readLine()) != null) {
                lineNum++;
                if (lineNum == 1) {
                    continue;
                }
                if (StrUtil.isBlank(line)) {
                    continue;
                }
                try {
                    String[] parts = line.split(",");
                    ChannelTransaction transaction = parseLine(parts, channelCode, reconciliationId);
                    if (transaction != null) {
                        batchList.add(transaction);
                        totalCount.incrementAndGet();

                        if (batchList.size() >= batchSize) {
                            flushBatch(batchList, successCount, callback);
                        }
                    }
                } catch (Exception e) {
                    log.error("解析CSV行失败, 行号: {}, 数据: {}", lineNum, line, e);
                    if (callback != null) {
                        callback.onError(lineNum, line, e);
                    }
                }
            }

            if (!batchList.isEmpty()) {
                flushBatch(batchList, successCount, callback);
            }

            log.info("CSV流式解析完成, 总条数: {}, 成功: {}", totalCount.get(), successCount.get());
            if (callback != null) {
                callback.onComplete(totalCount.get(), successCount.get());
            }
        }
    }

    private void flushBatch(List<ChannelTransaction> batchList, AtomicInteger successCount,
                            StreamingExcelParser.ParseCallback callback) {
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

    private ChannelTransaction parseLine(String[] parts, String channelCode, Long reconciliationId) {
        if (parts.length < 7) {
            return null;
        }
        ChannelTransaction transaction = new ChannelTransaction();
        transaction.setReconciliationId(reconciliationId);
        transaction.setChannelCode(channelCode);
        transaction.setChannelTransNo(parts[0].trim());
        transaction.setMerchantNo(parts[1].trim());
        transaction.setOrderNo(parts[2].trim());
        transaction.setAmount(new BigDecimal(parts[3].trim()));
        transaction.setFee(new BigDecimal(parts[4].trim()));
        transaction.setStatus(Integer.parseInt(parts[5].trim()));
        transaction.setTransTime(LocalDateTime.now());
        transaction.setMatched(0);
        transaction.setCreateTime(LocalDateTime.now());
        return transaction;
    }

    @Override
    public boolean support(String fileType) {
        return "csv".equalsIgnoreCase(fileType);
    }
}
