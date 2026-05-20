package com.econtract.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.econtract.common.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("contract")
public class Contract extends BaseEntity {

    private static final long serialVersionUID = 1L;

    private String contractNo;

    private String contractName;

    private Long templateId;

    private String filePath;

    private String fileName;

    private String fileHash;

    private String formData;

    private String status;

    private Long creatorId;

    private LocalDateTime expireTime;

    private String blockchainHash;

    private String blockchainTxId;

    private LocalDateTime blockchainTime;

    private String reviewStatus;

    private String riskLevel;

    private Integer reviewScore;

    private Integer allowPublicVerify;
}
