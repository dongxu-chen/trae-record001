package com.econtract.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotEmpty;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class ContractCreateDTO {

    @NotBlank(message = "合同名称不能为空")
    private String contractName;

    private Long templateId;

    private String formData;

    private LocalDateTime expireTime;

    @NotEmpty(message = "签署人不能为空")
    private List<SignerDTO> signers;
}
