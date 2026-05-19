package com.payment.reconciliation.ddd.domain.event;

import com.payment.reconciliation.ddd.core.DomainEvent;

import java.math.BigDecimal;

public class ReconciliationCompletedEvent extends DomainEvent {
    private String reconciliationNo;
    private String channelCode;
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
    private Integer status;

    public ReconciliationCompletedEvent() {
        super();
        setEventType("ReconciliationCompleted");
    }

    public ReconciliationCompletedEvent(String aggregateId, Long version) {
        super(aggregateId, version, "ReconciliationCompleted");
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

    public Integer getSysTotalCount() {
        return sysTotalCount;
    }

    public void setSysTotalCount(Integer sysTotalCount) {
        this.sysTotalCount = sysTotalCount;
    }

    public BigDecimal getSysTotalAmount() {
        return sysTotalAmount;
    }

    public void setSysTotalAmount(BigDecimal sysTotalAmount) {
        this.sysTotalAmount = sysTotalAmount;
    }

    public Integer getChannelTotalCount() {
        return channelTotalCount;
    }

    public void setChannelTotalCount(Integer channelTotalCount) {
        this.channelTotalCount = channelTotalCount;
    }

    public BigDecimal getChannelTotalAmount() {
        return channelTotalAmount;
    }

    public void setChannelTotalAmount(BigDecimal channelTotalAmount) {
        this.channelTotalAmount = channelTotalAmount;
    }

    public Integer getMatchedCount() {
        return matchedCount;
    }

    public void setMatchedCount(Integer matchedCount) {
        this.matchedCount = matchedCount;
    }

    public BigDecimal getMatchedAmount() {
        return matchedAmount;
    }

    public void setMatchedAmount(BigDecimal matchedAmount) {
        this.matchedAmount = matchedAmount;
    }

    public Integer getLongCount() {
        return longCount;
    }

    public void setLongCount(Integer longCount) {
        this.longCount = longCount;
    }

    public BigDecimal getLongAmount() {
        return longAmount;
    }

    public void setLongAmount(BigDecimal longAmount) {
        this.longAmount = longAmount;
    }

    public Integer getShortCount() {
        return shortCount;
    }

    public void setShortCount(Integer shortCount) {
        this.shortCount = shortCount;
    }

    public BigDecimal getShortAmount() {
        return shortAmount;
    }

    public void setShortAmount(BigDecimal shortAmount) {
        this.shortAmount = shortAmount;
    }

    public Integer getStatus() {
        return status;
    }

    public void setStatus(Integer status) {
        this.status = status;
    }
}
