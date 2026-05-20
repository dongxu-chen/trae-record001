package com.econtract.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import com.econtract.common.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("contract_template")
public class ContractTemplate extends BaseEntity {

    private static final long serialVersionUID = 1L;

    private String templateName;

    private String templateType;

    private String templateCode;

    private String filePath;

    private String fileName;

    private Long fileSize;

    @TableField(value = "fields")
    private String fields;

    private String signPositions;

    private Integer status;

    private Long creatorId;
}
