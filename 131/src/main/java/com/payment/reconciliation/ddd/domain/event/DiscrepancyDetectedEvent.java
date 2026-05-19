package com.payment.reconciliation.ddd.domain.event;

import com.payment.reconciliation.ddd.core.DomainEvent;

import java.math.BigDecimal;
import java.time.LocalDate;

public class DiscrepancyDetectedEvent extends DomainEvent {
    private String discrepancyNo;
    private String reconciliationNo;
    private String channelCode;
    private LocalDate reconciliationDate;
    private Integer discrepancyType;
    private String orderNo;
    private String transactionNo;
    private String channelTransNo;
    private BigDecimal sysAmount;
    private BigDecimal channelAmount;
    private BigDecimal differenceAmount;

    public DiscrepancyDetectedEvent() {
        super();
        setEventType("DiscrepancyDetected");
    }

    public DiscrepancyDetectedEvent(String aggregateId, Long version) {
        super(aggregateId, version, "DiscrepancyDetected");
    }

    public String getDiscrepancyNo() {
        return discrepancyNo;
    }

    public void setDiscrepancyNo(String discrepancyNo) {
        this.discrepancyNo = discrepancyNo;
    }

    public String getReconciliationNo() {
        return reconciliationNo;
    }

    public void setReconciliationNo(String reconciliationNo) {
        this.reconciliationNo = reconciliationNo;
    }

    public String getChannelCode() {
        return channelCode;
    }

    public void setChannelCode(String channelCode) {
        this.channelCode = channelCode;
    }

    public LocalDate getReconciliationDate() {
        return reconciliationDate;
    }

    public void setReconciliationDate(LocalDate reconciliationDate) {
        this.reconciliationDate = reconciliationDate;
    }

    public Integer getDiscrepancyType() {
        return discrepancyType;
    }

    public void setDiscrepancyType(Integer discrepancyType) {
        this.discrepancyType = discrepancyType;
    }

    public String getOrderNo() {
        return orderNo;
    }

    public void setOrderNo(String orderNo) {
        this.orderNo = orderNo;
    }

    public String getTransactionNo() {
        return transactionNo;
    }

    public void setTransactionNo(String transactionNo) {
        this.transactionNo = transactionNo;
    }

    public String getChannelTransNo() {
        return channelTransNo;
    }

    public void setChannelTransNo(String channelTransNo) {
        this.channelTransNo = channelTransNo;
    }

    public BigDecimal getSysAmount() {
        return sysAmount;
    }

    public void setSysAmount(BigDecimal sysAmount) {
        this.sysAmount = sysAmount;
    }

    public BigDecimal getChannelAmount() {
        return channelAmount;
    }

    public void setChannelAmount(BigDecimal channelAmount) {
        this.channelAmount = channelAmount;
    }

    public BigDecimal getDifferenceAmount() {
        return differenceAmount;
    }

    public void setDifferenceAmount(BigDecimal differenceAmount) {
        this.differenceAmount = differenceAmount;
    }
}
