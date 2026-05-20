package com.payment.reconciliation.service.impl;

import cn.hutool.core.io.FileUtil;
import cn.hutool.core.util.IdUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.payment.reconciliation.dto.ReconciliationExecuteDTO;
import com.payment.reconciliation.dto.ReconciliationParseDTO;
import com.payment.reconciliation.entity.*;
import com.payment.reconciliation.enums.BusinessTypeEnum;
import com.payment.reconciliation.enums.DiscrepancyTypeEnum;
import com.payment.reconciliation.enums.ReconciliationStatusEnum;
import com.payment.reconciliation.enums.TransactionStatusEnum;
import com.payment.reconciliation.mapper.*;
import com.payment.reconciliation.parser.StreamingCsvParser;
import com.payment.reconciliation.parser.StreamingExcelParser;
import com.payment.reconciliation.service.ReconciliationService;
import com.payment.reconciliation.service.ReversalService;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class ReconciliationServiceImpl implements ReconciliationService {

    @Autowired
    private ChannelReconciliationMapper channelReconciliationMapper;

    @Autowired
    private ChannelTransactionMapper channelTransactionMapper;

    @Autowired
    private TransactionMapper transactionMapper;

    @Autowired
    private ReconciliationResultMapper reconciliationResultMapper;

    @Autowired
    private DiscrepancyMapper discrepancyMapper;

    @Autowired
    private TransactionLogMapper transactionLogMapper;

    @Autowired
    private StreamingExcelParser streamingExcelParser;

    @Autowired
    private StreamingCsvParser streamingCsvParser;

    @Autowired
    private ReversalService reversalService;

    @Autowired
    private RocketMQTemplate rocketMQTemplate;

    @Value("${reconciliation.mq.topic.reconciliation:reconciliation-topic}")
    private String reconciliationTopic;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ChannelReconciliation parseReconciliationFile(ReconciliationParseDTO dto) {
        log.info("开始解析对账文件, 渠道: {}, 日期: {}", dto.getChannelCode(), dto.getReconciliationDate());

        ChannelReconciliation reconciliation = new ChannelReconciliation();
        reconciliation.setReconciliationNo(IdUtil.simpleUUID());
        reconciliation.setChannelCode(dto.getChannelCode());
        reconciliation.setReconciliationDate(dto.getReconciliationDate());
        reconciliation.setFileName(FileUtil.getName(dto.getFilePath()));
        reconciliation.setFilePath(dto.getFilePath());
        reconciliation.setFileType(dto.getFileType());
        reconciliation.setStatus(ReconciliationStatusEnum.PENDING.getCode());
        reconciliation.setCreateTime(LocalDateTime.now());
        reconciliation.setUpdateTime(LocalDateTime.now());
        channelReconciliationMapper.insert(reconciliation);

        String transactionId = IdUtil.simpleUUID();

        TransactionLog transactionLog = new TransactionLog();
        transactionLog.setTransactionId(transactionId);
        transactionLog.setBusinessType(BusinessTypeEnum.RECONCILIATION.getCode());
        transactionLog.setBusinessId(String.valueOf(reconciliation.getId()));
        transactionLog.setStatus(TransactionStatusEnum.PENDING.getCode());
        transactionLog.setRetryCount(0);
        transactionLog.setCreateTime(LocalDateTime.now());
        transactionLog.setUpdateTime(LocalDateTime.now());
        transactionLogMapper.insert(transactionLog);

        rocketMQTemplate.sendMessageInTransaction(
                reconciliationTopic,
                MessageBuilder.withPayload(reconciliation.getId())
                        .setHeader("TRANSACTION_ID", transactionId)
                        .setHeader("BUSINESS_TYPE", BusinessTypeEnum.RECONCILIATION.getCode())
                        .setHeader("BUSINESS_ID", String.valueOf(reconciliation.getId()))
                        .build(),
                null
        );

        log.info("对账文件解析任务已提交, reconciliationId: {}", reconciliation.getId());
        return reconciliation;
    }

    @Override
    public void executeReconciliation(ReconciliationExecuteDTO dto) {
        log.info("开始执行对账, 渠道: {}, 日期: {}", dto.getChannelCode(), dto.getReconciliationDate());

        LambdaQueryWrapper<ChannelReconciliation> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ChannelReconciliation::getChannelCode, dto.getChannelCode())
                .eq(ChannelReconciliation::getReconciliationDate, dto.getReconciliationDate())
                .eq(ChannelReconciliation::getStatus, ReconciliationStatusEnum.PARSED.getCode())
                .orderByDesc(ChannelReconciliation::getCreateTime)
                .last("LIMIT 1");

        ChannelReconciliation reconciliation = channelReconciliationMapper.selectOne(wrapper);
        if (reconciliation == null) {
            throw new RuntimeException("未找到已解析的对账文件");
        }

        processReconciliation(reconciliation.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void processReconciliation(Long reconciliationId) {
        log.info("开始处理对账任务, reconciliationId: {}", reconciliationId);

        ChannelReconciliation reconciliation = channelReconciliationMapper.selectById(reconciliationId);
        if (reconciliation == null) {
            throw new RuntimeException("对账记录不存在");
        }

        reconciliation.setStatus(ReconciliationStatusEnum.PARSING.getCode());
        reconciliation.setUpdateTime(LocalDateTime.now());
        channelReconciliationMapper.updateById(reconciliation);

        try {
            File file = new File(reconciliation.getFilePath());
            String fileType = FileUtil.extName(reconciliation.getFilePath());

            try (InputStream inputStream = new FileInputStream(file)) {
                if ("xlsx".equalsIgnoreCase(fileType) || "xls".equalsIgnoreCase(fileType)) {
                    streamingExcelParser.parseStreaming(inputStream, reconciliation.getChannelCode(),
                            reconciliationId, new StreamingExcelParser.ParseCallback() {
                                @Override
                                public void onBatchComplete(int batchSize, int totalSuccess) {
                                    log.debug("批次入库完成, batchSize: {}, total: {}", batchSize, totalSuccess);
                                }

                                @Override
                                public void onError(long rowIndex, Object rowData, Exception e) {
                                    log.error("解析行失败, rowIndex: {}", rowIndex, e);
                                }

                                @Override
                                public void onComplete(int totalCount, int successCount) {
                                    log.info("流式解析完成, 总条数: {}, 成功: {}", totalCount, successCount);
                                    reconciliation.setTotalCount(totalCount);
                                    reconciliation.setParsedCount(successCount);
                                }
                            });
                } else if ("csv".equalsIgnoreCase(fileType)) {
                    streamingCsvParser.parseStreaming(inputStream, reconciliation.getChannelCode(),
                            reconciliationId, new StreamingExcelParser.ParseCallback() {
                                @Override
                                public void onBatchComplete(int batchSize, int totalSuccess) {
                                    log.debug("批次入库完成, batchSize: {}, total: {}", batchSize, totalSuccess);
                                }

                                @Override
                                public void onError(long rowIndex, Object rowData, Exception e) {
                                    log.error("解析行失败, rowIndex: {}", rowIndex, e);
                                }

                                @Override
                                public void onComplete(int totalCount, int successCount) {
                                    log.info("流式解析完成, 总条数: {}, 成功: {}", totalCount, successCount);
                                    reconciliation.setTotalCount(totalCount);
                                    reconciliation.setParsedCount(successCount);
                                }
                            });
                } else {
                    throw new RuntimeException("不支持的文件类型: " + fileType);
                }
            }

            reconciliation.setStatus(ReconciliationStatusEnum.PARSED.getCode());
            reconciliation.setUpdateTime(LocalDateTime.now());
            channelReconciliationMapper.updateById(reconciliation);

            performReconciliation(reconciliation);

            reconciliation.setStatus(ReconciliationStatusEnum.SUCCESS.getCode());
            reconciliation.setUpdateTime(LocalDateTime.now());
            channelReconciliationMapper.updateById(reconciliation);

            log.info("对账任务处理完成, reconciliationId: {}", reconciliationId);
        } catch (Exception e) {
            log.error("对账任务处理失败, reconciliationId: {}", reconciliationId, e);
            reconciliation.setStatus(ReconciliationStatusEnum.FAILED.getCode());
            reconciliation.setErrorMsg(e.getMessage());
            reconciliation.setUpdateTime(LocalDateTime.now());
            channelReconciliationMapper.updateById(reconciliation);
            throw new RuntimeException("对账处理失败: " + e.getMessage());
        }
    }

    private void performReconciliation(ChannelReconciliation reconciliation) {
        log.info("开始执行对账匹配, reconciliationId: {}", reconciliation.getId());

        List<Transaction> sysTransactions = transactionMapper.selectByDateAndChannel(
                reconciliation.getReconciliationDate(),
                reconciliation.getChannelCode()
        );

        LambdaQueryWrapper<ChannelTransaction> ctWrapper = new LambdaQueryWrapper<>();
        ctWrapper.eq(ChannelTransaction::getReconciliationId, reconciliation.getId());
        List<ChannelTransaction> channelTransactions = channelTransactionMapper.selectList(ctWrapper);

        Map<String, Transaction> sysTransMap = sysTransactions.stream()
                .collect(Collectors.toMap(Transaction::getOrderNo, t -> t, (k1, k2) -> k1));

        Map<String, ChannelTransaction> channelTransMap = channelTransactions.stream()
                .collect(Collectors.toMap(ChannelTransaction::getOrderNo, t -> t, (k1, k2) -> k1));

        List<Discrepancy> discrepancies = new ArrayList<>();
        int matchedCount = 0;
        BigDecimal matchedAmount = BigDecimal.ZERO;

        Set<String> allOrderNos = new HashSet<>();
        allOrderNos.addAll(sysTransMap.keySet());
        allOrderNos.addAll(channelTransMap.keySet());

        for (String orderNo : allOrderNos) {
            Transaction sysTrans = sysTransMap.get(orderNo);
            ChannelTransaction channelTrans = channelTransMap.get(orderNo);

            if (sysTrans != null && channelTrans != null) {
                if (sysTrans.getAmount().compareTo(channelTrans.getAmount()) == 0) {
                    matchedCount++;
                    matchedAmount = matchedAmount.add(sysTrans.getAmount());
                    channelTrans.setMatched(1);
                } else {
                    Discrepancy discrepancy = createDiscrepancy(
                            reconciliation,
                            DiscrepancyTypeEnum.AMOUNT_MISMATCH,
                            orderNo,
                            sysTrans.getTransactionNo(),
                            channelTrans.getChannelTransNo(),
                            sysTrans.getAmount(),
                            channelTrans.getAmount()
                    );
                    discrepancies.add(discrepancy);
                }
            } else if (sysTrans != null) {
                Discrepancy discrepancy = createDiscrepancy(
                        reconciliation,
                        DiscrepancyTypeEnum.SHORT,
                        orderNo,
                        sysTrans.getTransactionNo(),
                        null,
                        sysTrans.getAmount(),
                        BigDecimal.ZERO
                );
                discrepancies.add(discrepancy);
            } else {
                Discrepancy discrepancy = createDiscrepancy(
                        reconciliation,
                        DiscrepancyTypeEnum.LONG,
                        orderNo,
                        null,
                        channelTrans.getChannelTransNo(),
                        BigDecimal.ZERO,
                        channelTrans.getAmount()
                );
                discrepancies.add(discrepancy);
            }
        }

        ReconciliationResult result = createReconciliationResult(
                reconciliation,
                sysTransactions,
                channelTransactions,
                matchedCount,
                matchedAmount,
                discrepancies
        );
        reconciliationResultMapper.insert(result);

        for (Discrepancy discrepancy : discrepancies) {
            discrepancy.setResultId(result.getId());
            discrepancyMapper.insert(discrepancy);
            reversalService.createReversalTask(discrepancy);
        }

        for (ChannelTransaction ct : channelTransactions) {
            channelTransactionMapper.updateById(ct);
        }

        log.info("对账匹配完成, 匹配成功: {}, 差错数: {}", matchedCount, discrepancies.size());
    }

    private Discrepancy createDiscrepancy(ChannelReconciliation reconciliation,
                                           DiscrepancyTypeEnum type,
                                           String orderNo,
                                           String transactionNo,
                                           String channelTransNo,
                                           BigDecimal sysAmount,
                                           BigDecimal channelAmount) {
        Discrepancy discrepancy = new Discrepancy();
        discrepancy.setDiscrepancyNo(IdUtil.simpleUUID());
        discrepancy.setChannelCode(reconciliation.getChannelCode());
        discrepancy.setReconciliationDate(reconciliation.getReconciliationDate());
        discrepancy.setType(type.getCode());
        discrepancy.setOrderNo(orderNo);
        discrepancy.setTransactionNo(transactionNo);
        discrepancy.setChannelTransNo(channelTransNo);
        discrepancy.setSysAmount(sysAmount);
        discrepancy.setChannelAmount(channelAmount);
        discrepancy.setDifferenceAmount(sysAmount.subtract(channelAmount).abs());
        discrepancy.setStatus(0);
        discrepancy.setCreateTime(LocalDateTime.now());
        discrepancy.setUpdateTime(LocalDateTime.now());
        return discrepancy;
    }

    private ReconciliationResult createReconciliationResult(ChannelReconciliation reconciliation,
                                                             List<Transaction> sysTransactions,
                                                             List<ChannelTransaction> channelTransactions,
                                                             int matchedCount,
                                                             BigDecimal matchedAmount,
                                                             List<Discrepancy> discrepancies) {
        ReconciliationResult result = new ReconciliationResult();
        result.setResultNo(IdUtil.simpleUUID());
        result.setChannelCode(reconciliation.getChannelCode());
        result.setReconciliationDate(reconciliation.getReconciliationDate());
        result.setSysTotalCount(sysTransactions.size());
        result.setSysTotalAmount(sysTransactions.stream()
                .map(Transaction::getAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add));
        result.setChannelTotalCount(channelTransactions.size());
        result.setChannelTotalAmount(channelTransactions.stream()
                .map(ChannelTransaction::getAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add));
        result.setMatchedCount(matchedCount);
        result.setMatchedAmount(matchedAmount);

        long longCount = discrepancies.stream().filter(d -> d.getType().equals(DiscrepancyTypeEnum.LONG.getCode())).count();
        BigDecimal longAmount = discrepancies.stream()
                .filter(d -> d.getType().equals(DiscrepancyTypeEnum.LONG.getCode()))
                .map(Discrepancy::getDifferenceAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        long shortCount = discrepancies.stream().filter(d -> d.getType().equals(DiscrepancyTypeEnum.SHORT.getCode())).count();
        BigDecimal shortAmount = discrepancies.stream()
                .filter(d -> d.getType().equals(DiscrepancyTypeEnum.SHORT.getCode()))
                .map(Discrepancy::getDifferenceAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        result.setLongCount((int) longCount);
        result.setLongAmount(longAmount);
        result.setShortCount((int) shortCount);
        result.setShortAmount(shortAmount);
        result.setStatus(1);
        result.setCreateTime(LocalDateTime.now());
        result.setUpdateTime(LocalDateTime.now());

        return result;
    }
}
