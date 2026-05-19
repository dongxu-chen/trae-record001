package com.payment.reconciliation.ddd.domain.event;

import com.payment.reconciliation.ddd.core.DomainEvent;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class ChannelTransactionCreatedEvent extends DomainEvent {
    private String channelTransNo;
    private String channelCode;
    private String merchantNo;
    private String orderNo;
    private BigDecimal amount;
    private BigDecimal fee;
    private Integer status;
    private LocalDateTime transTime;
    private String reconciliationId;

    public ChannelTransactionCreatedEvent() {
        super();
        setEventType("ChannelTransactionCreated");
    }

    public ChannelTransactionCreatedEvent(String aggregateId, Long version) {
        super(aggregateId, version, "ChannelTransactionCreated");
    }

    public String getChannelTransNo() {
        return channelTransNo;
    }

    public void setChannelTransNo(String channelTransNo) {
        this.channelTransNo = channelTransNo;
    }

    public String getChannelCode() {
        return channelCode;
    }

    public void setChannelCode(String channelCode) {
        this.channelCode = channelCode;
    }

    public String getMerchantNo() {
        return merchantNo;
    }

    public void setMerchantNo(String merchantNo) {
        this.merchantNo = merchantNo;
    }

    public String getOrderNo() {
        return orderNo;
    }

    public void setOrderNo(String orderNo) {
        this.orderNo = orderNo;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }

    public BigDecimal getFee() {
        return fee;
    }

    public void setFee(BigDecimal fee) {
        this.fee = fee;
    }

    public Integer getStatus() {
        return status;
    }

    public void setStatus(Integer status) {
        this.status = status;
    }

    public LocalDateTime getTransTime() {
        return transTime;
    }

    public void setTransTime(LocalDateTime transTime) {
        this.transTime = transTime;
    }

    public String getReconciliationId() {
        return reconciliationId;
    }

    public void setReconciliationId(String reconciliationId) {
        this.reconciliationId = reconciliationId;
    }
}
