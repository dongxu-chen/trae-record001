package com.econtract.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@TableName("blockchain_batch")
public class BlockchainBatch implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    private String batchNo;

    private Integer evidenceCount;

    private Long totalGas;

    private Long avgGas;

    private String merkleRoot;

    private String txId;

    private Long blockHeight;

    private String blockHash;

    private LocalDateTime blockTime;

    private String status;

    private String errorMsg;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
