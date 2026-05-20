package com.payment.reconciliation.ddd.domain.aggregate;

import com.payment.reconciliation.ddd.core.AggregateRoot;
import com.payment.reconciliation.ddd.core.DomainEvent;
import com.payment.reconciliation.ddd.domain.event.TransactionCreatedEvent;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class AccountTransaction extends AggregateRoot<String> {
    private String transactionNo;
    private String orderNo;
    private String channelCode;
    private String merchantNo;
    private BigDecimal amount;
    private BigDecimal fee;
    private String payMethod;
    private LocalDateTime transTime;
    private Integer status;

    private AccountTransaction() {
    }

    public static AccountTransaction create(String transactionNo, String orderNo, String channelCode,
                                            String merchantNo, BigDecimal amount, BigDecimal fee,
                                            String payMethod, LocalDateTime transTime) {
        AccountTransaction transaction = new AccountTransaction();
        transaction.setId(transactionNo);

        TransactionCreatedEvent event = new TransactionCreatedEvent(transactionNo, 1L);
        event.setTransactionNo(transactionNo);
        event.setOrderNo(orderNo);
        event.setChannelCode(channelCode);
        event.setMerchantNo(merchantNo);
        event.setAmount(amount);
        event.setFee(fee);
        event.setPayMethod(payMethod);
        event.setTransTime(transTime);
        event.setStatus(1);

        transaction.apply(event);
        return transaction;
    }

    @Override
    protected void handle(DomainEvent event) {
        if (event instanceof TransactionCreatedEvent) {
            handleTransactionCreated((TransactionCreatedEvent) event);
        }
    }

    private void handleTransactionCreated(TransactionCreatedEvent event) {
        this.transactionNo = event.getTransactionNo();
        this.orderNo = event.getOrderNo();
        this.channelCode = event.getChannelCode();
        this.merchantNo = event.getMerchantNo();
        this.amount = event.getAmount();
        this.fee = event.getFee();
        this.payMethod = event.getPayMethod();
        this.transTime = event.getTransTime();
        this.status = event.getStatus();
    }

    public String getTransactionNo() {
        return transactionNo;
    }

    public String getOrderNo() {
        return orderNo;
    }

    public String getChannelCode() {
        return channelCode;
    }

    public String getMerchantNo() {
        return merchantNo;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public BigDecimal getFee() {
        return fee;
    }

    public String getPayMethod() {
        return payMethod;
    }

    public LocalDateTime getTransTime() {
        return transTime;
    }

    public Integer getStatus() {
        return status;
    }
}
