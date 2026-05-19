package com.payment.reconciliation.ddd.application.query;

import org.springframework.data.elasticsearch.annotations.Document;
import org.springframework.data.elasticsearch.annotations.Field;
import org.springframework.data.elasticsearch.annotations.FieldType;

import java.math.BigDecimal;

@Document(indexName = "reconciliation")
public class ReconciliationDoc {
    @Field(type = FieldType.Keyword)
    private String reconciliationNo;

    @Field(type = FieldType.Keyword)
    private String channelCode;

    @Field(type = FieldType.Date)
    private String reconciliationDate;

    @Field(type = FieldType.Integer)
    private Integer sysTotalCount;

    @Field(type = FieldType.Double)
    private BigDecimal sysTotalAmount;

    @Field(type = FieldType.Integer)
    private Integer channelTotalCount;

    @Field(type = FieldType.Double)
    private BigDecimal channelTotalAmount;

    @Field(type = FieldType.Integer)
    private Integer matchedCount;

    @Field(type = FieldType.Double)
    private BigDecimal matchedAmount;

    @Field(type = FieldType.Integer)
    private Integer longCount;

    @Field(type = FieldType.Double)
    private BigDecimal longAmount;

    @Field(type = FieldType.Integer)
    private Integer shortCount;

    @Field(type = FieldType.Double)
    private BigDecimal shortAmount;

    @Field(type = FieldType.Integer)
    private Integer status;

    @Field(type = FieldType.Date)
    private String createTime;

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

    public String getReconciliationDate() {
        return reconciliationDate;
    }

    public void setReconciliationDate(String reconciliationDate) {
        this.reconciliationDate = reconciliationDate;
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

    public String getCreateTime() {
        return createTime;
    }

    public void setCreateTime(String createTime) {
        this.createTime = createTime;
    }
}
