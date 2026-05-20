package com.econtract.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.econtract.common.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("contract_signer")
public class ContractSigner extends BaseEntity {

    private static final long serialVersionUID = 1L;

    private Long contractId;

    private Long signerId;

    private String signerName;

    private String signerPhone;

    private Integer signOrder;

    private String signStatus;

    private LocalDateTime signTime;

    private String signatureImage;

    private String signatureType;

    private String signPosition;

    private String signIp;

    private String signDevice;

    private String authType;

    private LocalDateTime authTime;

    private String timestampToken;

    private String signNote;

    private LocalDateTime signDeadline;

    private Integer remindCount;

    private LocalDateTime lastRemindTime;

    private String pressureData;

    private Integer isTimeout;

    private Long witnessAuthId;
}
