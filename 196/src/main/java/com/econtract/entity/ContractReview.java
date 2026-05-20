package com.econtract.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@TableName("contract_review")
public class ContractReview implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long contractId;

    private String reviewResult;

    private String missingClauses;

    private String riskClauses;

    private String riskLevel;

    private Integer totalScore;

    private Long reviewerId;

    private LocalDateTime reviewTime;

    private String status;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
