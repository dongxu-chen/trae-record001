package com.property.repair.dto;

import lombok.Data;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

@Data
public class RepairSubmitDTO {

    @NotNull(message = "业主ID不能为空")
    private Long ownerId;

    @NotBlank(message = "业主姓名不能为空")
    private String ownerName;

    @NotBlank(message = "联系电话不能为空")
    private String ownerPhone;

    @NotNull(message = "报修类型不能为空")
    private Long repairTypeId;

    @NotBlank(message = "报修地址不能为空")
    private String address;

    private Double longitude;

    private Double latitude;

    @NotBlank(message = "报修描述不能为空")
    private String description;

    private String images;

    private String compressedImages;
}
