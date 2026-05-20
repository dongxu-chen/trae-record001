package com.payment.reconciliation.ddd.domain.event;

import com.payment.reconciliation.ddd.core.DomainEvent;

import java.time.LocalDate;

public class ReconciliationStartedEvent extends DomainEvent {
    private String reconciliationNo;
    private String channelCode;
    private LocalDate reconciliationDate;
    private String fileName;
    private String filePath;

    public ReconciliationStartedEvent() {
        super();
        setEventType("ReconciliationStarted");
    }

    public ReconciliationStartedEvent(String aggregateId, Long version) {
        super(aggregateId, version, "ReconciliationStarted");
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

    public String getFileName() {
        return fileName;
    }

    public void setFileName(String fileName) {
        this.fileName = fileName;
    }

    public String getFilePath() {
        return filePath;
    }

    public void setFilePath(String filePath) {
        this.filePath = filePath;
    }
}
