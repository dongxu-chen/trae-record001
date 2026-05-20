package com.econtract.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("witness_auth")
public class WitnessAuth implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long contractId;

    private Long signerId;

    private String authType;

    private String videoPath;

    private Integer videoDuration;

    private Long videoSize;

    private String videoHash;

    private Integer faceDetected;

    private BigDecimal faceSimilarity;

    private Integer livenessPassed;

    private String speechText;

    private String authResult;

    private LocalDateTime authTime;

    private String txId;

    private LocalDateTime blockchainTime;

    private LocalDateTime createTime;
}
