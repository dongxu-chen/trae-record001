package com.payment.reconciliation.ddd.domain.aggregate;

import com.payment.reconciliation.ddd.core.AggregateRoot;
import com.payment.reconciliation.ddd.core.DomainEvent;
import com.payment.reconciliation.ddd.domain.event.ChannelTransactionCreatedEvent;
import com.payment.reconciliation.ddd.domain.event.DiscrepancyDetectedEvent;
import com.payment.reconciliation.ddd.domain.event.ReconciliationCompletedEvent;
import com.payment.reconciliation.ddd.domain.event.ReconciliationStartedEvent;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

public class ReconciliationAggregate extends AggregateRoot<String> {
    private String reconciliationNo;
    private String channelCode;
    private LocalDate reconciliationDate;
    private String fileName;
    private String filePath;
    private Integer status;
    private List<ChannelTransaction> channelTransactions;
    private List<Discrepancy> discrepancies;
    private ReconciliationResult result;

    private ReconciliationAggregate() {
        this.channelTransactions = new ArrayList<>();
        this.discrepancies = new ArrayList<>();
    }

    public static ReconciliationAggregate create(String reconciliationNo, String channelCode,
                                                   LocalDate reconciliationDate, String fileName, String filePath) {
        ReconciliationAggregate reconciliation = new ReconciliationAggregate();
        reconciliation.setId(reconciliationNo);

        ReconciliationStartedEvent event = new ReconciliationStartedEvent(reconciliationNo, 1L);
        event.setReconciliationNo(reconciliationNo);
        event.setChannelCode(channelCode);
        event.setReconciliationDate(reconciliationDate);
        event.setFileName(fileName);
        event.setFilePath(filePath);

        reconciliation.apply(event);
        return reconciliation;
    }

    public void addChannelTransaction(String channelTransNo, String merchantNo, String orderNo,
                                       BigDecimal amount, BigDecimal fee, Integer status,
                                       java.time.LocalDateTime transTime) {
        Long nextVersion = getVersion() + 1;
        ChannelTransactionCreatedEvent event = new ChannelTransactionCreatedEvent(getId(), nextVersion);
        event.setChannelTransNo(channelTransNo);
        event.setChannelCode(channelCode);
        event.setMerchantNo(merchantNo);
        event.setOrderNo(orderNo);
        event.setAmount(amount);
        event.setFee(fee);
        event.setStatus(status);
        event.setTransTime(transTime);
        event.setReconciliationId(getId());

        apply(event);
    }

    public void detectDiscrepancy(String discrepancyNo, Integer discrepancyType, String orderNo,
                                   String transactionNo, String channelTransNo, BigDecimal sysAmount,
                                   BigDecimal channelAmount, BigDecimal differenceAmount) {
        Long nextVersion = getVersion() + 1;
        DiscrepancyDetectedEvent event = new DiscrepancyDetectedEvent(getId(), nextVersion);
        event.setDiscrepancyNo(discrepancyNo);
        event.setReconciliationNo(reconciliationNo);
        event.setChannelCode(channelCode);
        event.setReconciliationDate(reconciliationDate);
        event.setDiscrepancyType(discrepancyType);
        event.setOrderNo(orderNo);
        event.setTransactionNo(transactionNo);
        event.setChannelTransNo(channelTransNo);
        event.setSysAmount(sysAmount);
        event.setChannelAmount(channelAmount);
        event.setDifferenceAmount(differenceAmount);

        apply(event);
    }

    public void complete(ReconciliationResult result) {
        Long nextVersion = getVersion() + 1;
        ReconciliationCompletedEvent event = new ReconciliationCompletedEvent(getId(), nextVersion);
        event.setReconciliationNo(reconciliationNo);
        event.setChannelCode(channelCode);
        event.setSysTotalCount(result.sysTotalCount);
        event.setSysTotalAmount(result.sysTotalAmount);
        event.setChannelTotalCount(result.channelTotalCount);
        event.setChannelTotalAmount(result.channelTotalAmount);
        event.setMatchedCount(result.matchedCount);
        event.setMatchedAmount(result.matchedAmount);
        event.setLongCount(result.longCount);
        event.setLongAmount(result.longAmount);
        event.setShortCount(result.shortCount);
        event.setShortAmount(result.shortAmount);
        event.setStatus(1);

        apply(event);
    }

    @Override
    protected void handle(DomainEvent event) {
        if (event instanceof ReconciliationStartedEvent) {
            handleReconciliationStarted((ReconciliationStartedEvent) event);
        } else if (event instanceof ChannelTransactionCreatedEvent) {
            handleChannelTransactionCreated((ChannelTransactionCreatedEvent) event);
        } else if (event instanceof DiscrepancyDetectedEvent) {
            handleDiscrepancyDetected((DiscrepancyDetectedEvent) event);
        } else if (event instanceof ReconciliationCompletedEvent) {
            handleReconciliationCompleted((ReconciliationCompletedEvent) event);
        }
    }

    private void handleReconciliationStarted(ReconciliationStartedEvent event) {
        this.reconciliationNo = event.getReconciliationNo();
        this.channelCode = event.getChannelCode();
        this.reconciliationDate = event.getReconciliationDate();
        this.fileName = event.getFileName();
        this.filePath = event.getFilePath();
        this.status = 0;
    }

    private void handleChannelTransactionCreated(ChannelTransactionCreatedEvent event) {
        ChannelTransaction ct = new ChannelTransaction();
        ct.channelTransNo = event.getChannelTransNo();
        ct.merchantNo = event.getMerchantNo();
        ct.orderNo = event.getOrderNo();
        ct.amount = event.getAmount();
        ct.fee = event.getFee();
        ct.status = event.getStatus();
        ct.transTime = event.getTransTime();
        this.channelTransactions.add(ct);
    }

    private void handleDiscrepancyDetected(DiscrepancyDetectedEvent event) {
        Discrepancy d = new Discrepancy();
        d.discrepancyNo = event.getDiscrepancyNo();
        d.discrepancyType = event.getDiscrepancyType();
        d.orderNo = event.getOrderNo();
        d.transactionNo = event.getTransactionNo();
        d.channelTransNo = event.getChannelTransNo();
        d.sysAmount = event.getSysAmount();
        d.channelAmount = event.getChannelAmount();
        d.differenceAmount = event.getDifferenceAmount();
        this.discrepancies.add(d);
    }

    private void handleReconciliationCompleted(ReconciliationCompletedEvent event) {
        this.result = new ReconciliationResult();
        this.result.sysTotalCount = event.getSysTotalCount();
        this.result.sysTotalAmount = event.getSysTotalAmount();
        this.result.channelTotalCount = event.getChannelTotalCount();
        this.result.channelTotalAmount = event.getChannelTotalAmount();
        this.result.matchedCount = event.getMatchedCount();
        this.result.matchedAmount = event.getMatchedAmount();
        this.result.longCount = event.getLongCount();
        this.result.longAmount = event.getLongAmount();
        this.result.shortCount = event.getShortCount();
        this.result.shortAmount = event.getShortAmount();
        this.status = event.getStatus();
    }

    public static class ChannelTransaction {
        private String channelTransNo;
        private String merchantNo;
        private String orderNo;
        private BigDecimal amount;
        private BigDecimal fee;
        private Integer status;
        private java.time.LocalDateTime transTime;
    }

    public static class Discrepancy {
        private String discrepancyNo;
        private Integer discrepancyType;
        private String orderNo;
        private String transactionNo;
        private String channelTransNo;
        private BigDecimal sysAmount;
        private BigDecimal channelAmount;
        private BigDecimal differenceAmount;
    }

    public static class ReconciliationResult {
        private Integer sysTotalCount;
        private BigDecimal sysTotalAmount;
        private Integer channelTotalCount;
        private BigDecimal channelTotalAmount;
        private Integer matchedCount;
        private BigDecimal matchedAmount;
        private Integer longCount;
        private BigDecimal longAmount;
        private Integer shortCount;
        private BigDecimal shortAmount;
    }

    public String getReconciliationNo() {
        return reconciliationNo;
    }

    public String getChannelCode() {
        return channelCode;
    }

    public LocalDate getReconciliationDate() {
        return reconciliationDate;
    }

    public String getFileName() {
        return fileName;
    }

    public String getFilePath() {
        return filePath;
    }

    public Integer getStatus() {
        return status;
    }

    public List<ChannelTransaction> getChannelTransactions() {
        return channelTransactions;
    }

    public List<Discrepancy> getDiscrepancies() {
        return discrepancies;
    }

    public ReconciliationResult getResult() {
        return result;
    }
}
