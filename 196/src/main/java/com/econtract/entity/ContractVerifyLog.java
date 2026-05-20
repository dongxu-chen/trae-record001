package com.econtract.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@TableName("contract_verify_log")
public class ContractVerifyLog implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    private String contractNo;

    private String verifyType;

    private String requesterIp;

    private String requesterInfo;

    private String verifyResult;

    private String verifyDetail;

    private LocalDateTime createTime;
}
