package com.payment.reconciliation.ddd.domain.event;

import com.payment.reconciliation.ddd.core.DomainEvent;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class TransactionCreatedEvent extends DomainEvent {
    private String transactionNo;
    private String orderNo;
    private String channelCode;
    private String merchantNo;
    private BigDecimal amount;
    private BigDecimal fee;
    private String payMethod;
    private LocalDateTime transTime;
    private Integer status;

    public TransactionCreatedEvent() {
        super();
        setEventType("TransactionCreated");
    }

    public TransactionCreatedEvent(String aggregateId, Long version) {
        super(aggregateId, version, "TransactionCreated");
    }

    public String getTransactionNo() {
        return transactionNo;
    }

    public void setTransactionNo(String transactionNo) {
        this.transactionNo = transactionNo;
    }

    public String getOrderNo() {
        return orderNo;
    }

    public void setOrderNo(String orderNo) {
        this.orderNo = orderNo;
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

    public String getPayMethod() {
        return payMethod;
    }

    public void setPayMethod(String payMethod) {
        this.payMethod = payMethod;
    }

    public LocalDateTime getTransTime() {
        return transTime;
    }

    public void setTransTime(LocalDateTime transTime) {
        this.transTime = transTime;
    }

    public Integer getStatus() {
        return status;
    }

    public void setStatus(Integer status) {
        this.status = status;
    }
}
